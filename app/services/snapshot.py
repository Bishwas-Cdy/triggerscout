from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TriggerType
from app.models import DetectedChange, MonitoredCompany, Snapshot
from app.schemas import ScanPageResult, ScanResponse
from app.services.classifier import TriggerClassifier, no_change_result
from app.services.diff import compact_diff
from app.services.normalizer import content_hash, normalize_html
from app.services.scraper import Scraper


async def capture_snapshot(
    db: Session, company: MonitoredCompany, page_url: str, scraper: Scraper
) -> Snapshot:
    html = await scraper.fetch(page_url)
    normalized = normalize_html(html)
    snapshot = Snapshot(
        company_id=company.id,
        page_url=page_url,
        content_hash=content_hash(normalized),
        normalized_text=normalized,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def latest_snapshot(db: Session, company_id: int, page_url: str) -> Snapshot | None:
    return db.scalar(
        select(Snapshot)
        .where(Snapshot.company_id == company_id, Snapshot.page_url == page_url)
        .order_by(Snapshot.captured_at.desc(), Snapshot.id.desc())
        .limit(1)
    )


async def scan_company(
    db: Session,
    company: MonitoredCompany,
    scraper: Scraper,
    classifier: TriggerClassifier,
) -> ScanResponse:
    results: list[ScanPageResult] = []
    meaningful_count = 0
    for page_url in company.pages_to_monitor:
        previous = latest_snapshot(db, company.id, page_url)
        current = await capture_snapshot(db, company, page_url, scraper)
        if previous is None:
            result = no_change_result(after_excerpt=current.normalized_text[:1_500])
        elif previous.content_hash == current.content_hash:
            result = no_change_result()
        else:
            candidate = compact_diff(previous.normalized_text, current.normalized_text)
            result = (
                no_change_result()
                if candidate is None
                else await classifier.classify(company.name, candidate)
            )
        if result.trigger is not TriggerType.NO_MEANINGFUL_CHANGE:
            meaningful_count += 1
            db.add(
                DetectedChange(
                    company_id=company.id,
                    page_url=page_url,
                    before_excerpt=result.before_excerpt,
                    after_excerpt=result.after_excerpt,
                    change_type=result.trigger.value,
                    confidence=result.confidence,
                    significance=result.significance.value,
                    why_it_matters=result.why_it_matters,
                    recommended_action=result.recommended_action.value,
                )
            )
        results.append(ScanPageResult(page_url=page_url, snapshot_id=current.id, result=result))
    db.commit()
    return ScanResponse(
        company_id=company.id,
        company_name=company.name,
        pages_scanned=len(results),
        meaningful_changes=meaningful_count,
        results=results,
    )

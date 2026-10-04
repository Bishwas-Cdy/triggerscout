from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_classifier, get_scraper
from app.enums import TriggerType
from app.models import DetectedChange, MonitoredCompany, Snapshot
from app.schemas import (
    CompanyCreate,
    CompanyRead,
    CompareRequest,
    CompareResponse,
    DetectedChangeRead,
    ScanResponse,
    SnapshotRead,
    SnapshotRequest,
    WebhookScanRequest,
)
from app.services.classifier import TriggerClassifier, no_change_result
from app.services.diff import compact_diff
from app.services.normalizer import content_hash, normalize_text
from app.services.scraper import ScrapeError, Scraper
from app.services.snapshot import capture_snapshot, scan_company
from app.services.url_safety import UnsafeURLError, normalize_page_url

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
ScraperDep = Annotated[Scraper, Depends(get_scraper)]
ClassifierDep = Annotated[TriggerClassifier, Depends(get_classifier)]


def _company_or_404(db: Session, company_id: int) -> MonitoredCompany:
    company = db.get(MonitoredCompany, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "TriggerScout"}


@router.post("/companies", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, db: DbSession) -> MonitoredCompany:
    try:
        website = normalize_page_url(str(payload.website), str(payload.website))
        raw_pages = payload.pages_to_monitor or [payload.website]
        pages = [normalize_page_url(website, str(page)) for page in raw_pages]
    except UnsafeURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    company = MonitoredCompany(
        name=payload.name,
        website=website,
        pages_to_monitor=list(dict.fromkeys(pages)),
        active=payload.active,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/companies", response_model=list[CompanyRead])
async def list_companies(db: DbSession) -> list[MonitoredCompany]:
    return list(db.scalars(select(MonitoredCompany).order_by(MonitoredCompany.id)).all())


@router.get("/companies/{company_id}", response_model=CompanyRead)
async def get_company(company_id: int, db: DbSession) -> MonitoredCompany:
    return _company_or_404(db, company_id)


@router.post("/companies/{company_id}/snapshot", response_model=list[SnapshotRead])
async def create_snapshot(
    company_id: int,
    db: DbSession,
    scraper: ScraperDep,
    payload: Annotated[SnapshotRequest | None, Body()] = None,
) -> list[Snapshot]:
    company = _company_or_404(db, company_id)
    if payload is not None and payload.page_url is not None:
        requested_url = normalize_page_url(company.website, str(payload.page_url))
        if requested_url not in company.pages_to_monitor:
            raise HTTPException(status_code=422, detail="URL is not configured for this company")
        pages = [requested_url]
    else:
        pages = company.pages_to_monitor
    try:
        snapshots = [await capture_snapshot(db, company, page, scraper) for page in pages]
    except (ScrapeError, UnsafeURLError) as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.commit()
    return snapshots


@router.get("/companies/{company_id}/snapshots", response_model=list[SnapshotRead])
async def list_snapshots(company_id: int, db: DbSession) -> list[Snapshot]:
    _company_or_404(db, company_id)
    statement = (
        select(Snapshot)
        .where(Snapshot.company_id == company_id)
        .order_by(Snapshot.captured_at.desc(), Snapshot.id.desc())
    )
    return list(db.scalars(statement).all())


@router.post("/companies/{company_id}/scan", response_model=ScanResponse)
async def scan(
    company_id: int,
    db: DbSession,
    scraper: ScraperDep,
    classifier: ClassifierDep,
) -> ScanResponse:
    company = _company_or_404(db, company_id)
    if not company.active:
        raise HTTPException(status_code=409, detail="Company monitoring is inactive")
    try:
        return await scan_company(db, company, scraper, classifier)
    except (ScrapeError, UnsafeURLError) as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/companies/{company_id}/changes", response_model=list[DetectedChangeRead])
async def list_changes(company_id: int, db: DbSession) -> list[DetectedChange]:
    _company_or_404(db, company_id)
    statement = (
        select(DetectedChange)
        .where(DetectedChange.company_id == company_id)
        .order_by(DetectedChange.detected_at.desc(), DetectedChange.id.desc())
    )
    return list(db.scalars(statement).all())


@router.post("/compare", response_model=CompareResponse, tags=["demo"])
async def compare(payload: CompareRequest, classifier: ClassifierDep) -> CompareResponse:
    before = normalize_text(payload.before)
    after = normalize_text(payload.after)
    if content_hash(before) == content_hash(after):
        result = no_change_result()
    else:
        candidate = compact_diff(before, after)
        result = (
            no_change_result()
            if candidate is None
            else await classifier.classify(payload.company_name, candidate)
        )
    return CompareResponse(
        company_name=payload.company_name,
        meaningful_change=result.trigger is not TriggerType.NO_MEANINGFUL_CHANGE,
        changes=[result],
    )


@router.post("/webhooks/scan", response_model=ScanResponse, tags=["automation"])
async def webhook_scan(
    payload: WebhookScanRequest,
    db: DbSession,
    scraper: ScraperDep,
    classifier: ClassifierDep,
) -> ScanResponse:
    return await scan(payload.company_id, db, scraper, classifier)

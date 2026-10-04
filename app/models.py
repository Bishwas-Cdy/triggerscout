from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class MonitoredCompany(Base):
    __tablename__ = "monitored_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    website: Mapped[str] = mapped_column(String(2048))
    pages_to_monitor: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("monitored_companies.id"), index=True)
    page_url: Mapped[str] = mapped_column(String(2048), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    normalized_text: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DetectedChange(Base):
    __tablename__ = "detected_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("monitored_companies.id"), index=True)
    page_url: Mapped[str] = mapped_column(String(2048), index=True)
    before_excerpt: Mapped[str] = mapped_column(Text)
    after_excerpt: Mapped[str] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String(50), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    significance: Mapped[str] = mapped_column(String(20))
    why_it_matters: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(String(50))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

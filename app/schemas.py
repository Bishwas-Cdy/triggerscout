from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.enums import RecommendedAction, Significance, TriggerType


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    website: HttpUrl
    pages_to_monitor: list[HttpUrl] = Field(default_factory=list, max_length=20)
    active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website: str
    pages_to_monitor: list[str]
    created_at: datetime
    active: bool


class SnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    page_url: str
    content_hash: str
    normalized_text: str
    captured_at: datetime


class SnapshotRequest(BaseModel):
    page_url: HttpUrl | None = None


class ChangeResult(BaseModel):
    trigger: TriggerType
    confidence: float = Field(ge=0, le=1)
    significance: Significance
    before_excerpt: str
    after_excerpt: str
    why_it_matters: str
    recommended_action: RecommendedAction


class DetectedChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    page_url: str
    before_excerpt: str
    after_excerpt: str
    change_type: TriggerType
    confidence: float
    significance: Significance
    why_it_matters: str
    recommended_action: RecommendedAction
    detected_at: datetime


class CompareRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    before: str = Field(max_length=200_000)
    after: str = Field(max_length=200_000)


class CompareResponse(BaseModel):
    company_name: str
    meaningful_change: bool
    changes: list[ChangeResult]


class ScanPageResult(BaseModel):
    page_url: str
    snapshot_id: int | None = None
    result: ChangeResult


class ScanResponse(BaseModel):
    company_id: int
    company_name: str
    pages_scanned: int
    meaningful_changes: int
    results: list[ScanPageResult]


class WebhookScanRequest(BaseModel):
    company_id: int = Field(gt=0)


class LLMClassification(BaseModel):
    trigger: TriggerType
    confidence: float = Field(ge=0, le=1)
    significance: Significance
    why_it_matters: str = Field(min_length=1, max_length=500)
    recommended_action: RecommendedAction

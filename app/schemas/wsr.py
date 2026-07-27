from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class WsrGenerateRequest(BaseModel):
    start_date: date = Field(description="WSR report period start (Monday, inclusive)")
    end_date: date = Field(description="WSR report period end (Friday, inclusive)")
    force: bool = Field(
        default=False,
        description="Start a new background job even if one is already running",
    )


class WsrJobStartResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    report_start_date: date
    report_end_date: date
    message: str


class WsrStatusResponse(BaseModel):
    status: Literal["not_found", "queued", "running", "completed", "failed"]
    job_id: str | None = None
    report_start_date: date | None = None
    report_end_date: date | None = None
    error: str | None = None
    result: "WsrGenerateResponse | None" = None


class WsrMeta(BaseModel):
    story_count: int
    slide_count: int
    titles_from_db: int = 0
    titles_fallback_summary: int = 0
    titles_generated: int = 0
    titles_reused: int = 0


class WsrWeekSummary(BaseModel):
    report_start_date: date
    report_end_date: date
    filename: str
    generated_at: datetime
    story_count: int = 0
    slide_count: int = 0
    thumbnail_url: str | None = None
    download_url: str


class WsrWeekListResponse(BaseModel):
    count: int
    weeks: list[WsrWeekSummary]


class WsrContentSection(BaseModel):
    sprint_name: str
    sprint_dates: str
    sprint_status: str
    released: list[str]
    inprogress: list[str]
    completed: list[str]


class WsrContentSlide(BaseModel):
    project_key: str
    project_name: str
    title: str
    sections: list[WsrContentSection]
    key_activities: list[str]


class WsrPreviewSlide(BaseModel):
    slide_index: int
    title: str
    image_url: str


class WsrGenerateResponse(BaseModel):
    report_start_date: date
    report_end_date: date
    meta: WsrMeta
    preview: str
    filename: str
    download_url: str
    slides: list[WsrContentSlide]
    preview_slides: list[WsrPreviewSlide] = Field(default_factory=list)


WsrStatusResponse.model_rebuild()

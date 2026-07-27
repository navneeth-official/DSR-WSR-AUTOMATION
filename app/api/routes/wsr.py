from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.wsr import (
    WsrContentSlide,
    WsrGenerateRequest,
    WsrGenerateResponse,
    WsrJobStartResponse,
    WsrMeta,
    WsrPreviewSlide,
    WsrStatusResponse,
    WsrWeekListResponse,
    WsrWeekSummary,
)
from app.paths import wsr_output_paths
from app.services.pptx_editor_service import (
    export_editor_document_to_pptx,
    load_wsr_editor_deck,
    save_wsr_editor_deck,
)
from app.services.wsr_job_service import get_job, start_wsr_job
from app.services.wsr_preview_service import (
    export_wsr_slide_previews,
    resolve_preview_image_path,
)
from app.services.wsr_service import (
    generate_wsr_deck,
    list_generated_wsr_weeks,
    load_wsr_week,
    resolve_wsr_ppt_path,
)

router = APIRouter(prefix="/api/wsr", tags=["wsr"])


class EditorDocumentPayload(BaseModel):
    document: dict



def _build_generate_response(result: dict) -> WsrGenerateResponse:
    return WsrGenerateResponse(
        report_start_date=date.fromisoformat(result["report_start_date"]),
        report_end_date=date.fromisoformat(result["report_end_date"]),
        meta=WsrMeta(**result["meta"]),
        preview=result["preview"],
        filename=result["filename"],
        download_url=result["download_url"],
        slides=[WsrContentSlide(**slide) for slide in result.get("slides", [])],
        preview_slides=[
            WsrPreviewSlide(**slide) for slide in result.get("preview_slides", [])
        ],
    )


@router.get("/weeks", response_model=WsrWeekListResponse)
def list_wsr_weeks() -> WsrWeekListResponse:
    """List all previously generated WSR decks (newest report week first)."""
    weeks = [
        WsrWeekSummary(**item) for item in list_generated_wsr_weeks()
    ]
    return WsrWeekListResponse(count=len(weeks), weeks=weeks)


@router.get("/week", response_model=WsrGenerateResponse)
def get_wsr_week(
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> WsrGenerateResponse:
    """Load an existing generated WSR deck for a week without regenerating."""
    try:
        result = load_wsr_week(start_date, end_date)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _build_generate_response(result)


@router.post("/generate", response_model=WsrJobStartResponse, status_code=202)
def generate_wsr(
    body: WsrGenerateRequest,
    db: Session = Depends(get_db),
) -> WsrJobStartResponse:
    """
    Queue WSR generation on a background thread.

    Poll GET /api/wsr/status until status is completed or failed.
    """
    del db  # generation uses its own DB session in the worker thread

    if body.start_date > body.end_date:
        raise HTTPException(
            status_code=400,
            detail=(
                f"start_date ({body.start_date}) must be on or before "
                f"end_date ({body.end_date})."
            ),
        )

    job = start_wsr_job(
        start_date=body.start_date,
        end_date=body.end_date,
        force=body.force,
    )
    return WsrJobStartResponse(
        job_id=job.job_id,
        status=job.status,
        report_start_date=body.start_date,
        report_end_date=body.end_date,
        message=(
            "WSR generation started in the background. "
            "Poll GET /api/wsr/status for progress."
        ),
    )


@router.get("/status", response_model=WsrStatusResponse)
def get_wsr_status(
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> WsrStatusResponse:
    """Poll background WSR generation for a week."""
    job = get_job(start_date, end_date)
    if job is None:
        return WsrStatusResponse(status="not_found")

    response = WsrStatusResponse(
        status=job.status,
        job_id=job.job_id,
        report_start_date=job.start_date,
        report_end_date=job.end_date,
        error=job.error,
    )
    if job.status == "completed" and job.result is not None:
        if "download_url" not in job.result:
            job.result["download_url"] = (
                f"/api/wsr/download?start_date={start_date.isoformat()}"
                f"&end_date={end_date.isoformat()}"
            )
        response.result = _build_generate_response(job.result)
    return response


@router.get("/preview/slides", response_model=list[WsrPreviewSlide])
def list_wsr_preview_slides(
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> list[WsrPreviewSlide]:
    """Return rendered slide previews for an existing WSR deck."""
    try:
        slides = export_wsr_slide_previews(
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"WSR preview export failed: {exc}",
        ) from exc
    return [WsrPreviewSlide(**slide) for slide in slides]


@router.get("/preview/image")
def get_wsr_preview_image(
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
    slide_index: int = Query(..., ge=1, description="1-based slide index"),
) -> FileResponse:
    """Serve a rendered PNG preview for one slide of the generated WSR deck."""
    try:
        image_path = resolve_preview_image_path(
            start_date=start_date,
            end_date=end_date,
            slide_index=slide_index,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path=Path(image_path), media_type="image/png")


@router.get("/download")
def download_wsr_deck(
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> FileResponse:
    """Download the generated PowerPoint for a WSR week."""
    ppt_path = resolve_wsr_ppt_path(start_date, end_date)
    if not ppt_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No deck found for {start_date} to {end_date}. "
                "Call POST /api/wsr/generate first."
            ),
        )
    return FileResponse(
        path=Path(ppt_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        filename=ppt_path.name,
    )


@router.get("/editor/deck")
def get_editor_deck(
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> dict:
    """Parse the generated WSR .pptx into an editable JSON document."""
    preview_slides: list[dict] = []
    try:
        preview_slides = export_wsr_slide_previews(
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
        )
    except Exception:
        preview_slides = []

    if not preview_slides:
        try:
            preview_slides = export_wsr_slide_previews(
                start_date=start_date,
                end_date=end_date,
                use_cache=False,
            )
        except Exception:
            preview_slides = []

    try:
        return load_wsr_editor_deck(
            start_date,
            end_date,
            preview_slides=preview_slides,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load editor deck: {exc}",
        ) from exc


@router.put("/editor/deck")
def save_editor_deck(
    body: EditorDocumentPayload,
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> dict:
    """Persist the in-browser editor document for a WSR week."""
    path = save_wsr_editor_deck(start_date, end_date, body.document)
    return {"saved": True, "path": str(path)}


@router.post("/editor/sync")
def sync_editor_deck(
    body: EditorDocumentPayload,
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> dict:
    """Apply editor changes directly to the .pptx and refresh slide preview images."""
    paths = wsr_output_paths(start_date, end_date)
    try:
        export_editor_document_to_pptx(body.document, paths.ppt_path)
        save_wsr_editor_deck(start_date, end_date, body.document)
        preview_slides = export_wsr_slide_previews(
            start_date=start_date,
            end_date=end_date,
            use_cache=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Sync to PowerPoint failed: {exc}",
        ) from exc
    return {"ok": True, "preview_slides": preview_slides}


@router.post("/editor/export")
def export_editor_deck(
    body: EditorDocumentPayload,
    start_date: date = Query(..., description="WSR week start (Monday)"),
    end_date: date = Query(..., description="WSR week end (Friday)"),
) -> FileResponse:
    """Export the edited document back to .pptx."""
    paths = wsr_output_paths(start_date, end_date)
    try:
        export_editor_document_to_pptx(body.document, paths.ppt_path)
        save_wsr_editor_deck(start_date, end_date, body.document)
        try:
            export_wsr_slide_previews(
                start_date=start_date,
                end_date=end_date,
                use_cache=False,
            )
        except Exception:
            pass
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {exc}",
        ) from exc
    return FileResponse(
        path=paths.ppt_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        filename=paths.ppt_path.name,
    )

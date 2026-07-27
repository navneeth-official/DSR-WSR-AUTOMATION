"""Generate WSR PowerPoint decks from PostgreSQL story data."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.paths import (
    G10X_TEMPLATE,
    OUTPUT_DIR,
    PPT_BUILDER,
    REPO_ROOT,
    ensure_output_dir,
    wsr_output_paths,
    wsr_preview_dir,
)
from app.services.ppt_content_builder import build_ppt_content
from app.services.ppt_content_preview import format_content_preview
from app.services.wsr_preview_service import export_wsr_slide_previews

_WSR_PPTX_RE = re.compile(r"^WSR_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.pptx$")


def build_ppt_deck(
    content_json: Path,
    ppt_output: Path,
    layout_hints: Path | None = None,
) -> None:
    """Run update_delivery_status.py with G10X layout rules."""
    if not PPT_BUILDER.is_file():
        raise FileNotFoundError(f"PPT builder not found: {PPT_BUILDER}")
    if not G10X_TEMPLATE.is_file():
        raise FileNotFoundError(f"G10X template not found: {G10X_TEMPLATE}")

    cmd = [
        sys.executable,
        str(PPT_BUILDER),
        "--content",
        str(content_json.resolve()),
        "--output",
        str(ppt_output.resolve()),
    ]
    if layout_hints and layout_hints.is_file():
        cmd.extend(["--layout-hints", str(layout_hints.resolve())])
    ensure_output_dir()
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)


def generate_wsr_deck(
    db: Session,
    *,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Build ppt_content.json and the PowerPoint deck for a WSR week.
    Returns metadata, preview text, and output file paths.
    """
    if start_date > end_date:
        raise ValueError(
            f"start_date ({start_date}) must be on or before end_date ({end_date})."
        )

    paths = wsr_output_paths(start_date, end_date)
    content = build_ppt_content(
        db,
        start_date=start_date,
        end_date=end_date,
    )

    ensure_output_dir()
    with paths.json_path.open("w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)

    preview_text = format_content_preview(content)
    paths.preview_path.write_text(preview_text, encoding="utf-8")

    build_ppt_deck(paths.json_path, paths.ppt_path)

    preview_slides: list[dict] = []
    try:
        preview_slides = export_wsr_slide_previews(
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        print(f"Warning: WSR slide preview export failed: {exc}")

    download_url = (
        f"/api/wsr/download?start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}"
    )
    return {
        "report_start_date": content["report_start_date"],
        "report_end_date": content["report_end_date"],
        "meta": content["meta"],
        "slides": content["slides"],
        "preview_slides": preview_slides,
        "preview": preview_text,
        "filename": paths.ppt_path.name,
        "json_filename": paths.json_path.name,
        "ppt_path": str(paths.ppt_path),
        "download_url": download_url,
    }


def resolve_wsr_ppt_path(start_date: date, end_date: date) -> Path:
    """Return the expected PPT path for a WSR week (may not exist yet)."""
    return wsr_output_paths(start_date, end_date).ppt_path


def list_generated_wsr_weeks() -> list[dict]:
    """Scan output/ for generated WSR .pptx files, newest week first."""
    if not OUTPUT_DIR.is_dir():
        return []

    weeks: list[dict] = []
    for ppt_path in OUTPUT_DIR.glob("WSR_*.pptx"):
        match = _WSR_PPTX_RE.match(ppt_path.name)
        if not match:
            continue

        start_s, end_s = match.group(1), match.group(2)
        start_date = date.fromisoformat(start_s)
        end_date = date.fromisoformat(end_s)

        story_count = 0
        slide_count = 0
        json_path = OUTPUT_DIR / f"WSR_{start_s}_{end_s}.json"
        if json_path.is_file():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
                meta = payload.get("meta") or {}
                story_count = int(meta.get("story_count") or 0)
                slide_count = int(meta.get("slide_count") or 0)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        thumbnail_url: str | None = None
        preview_dir = wsr_preview_dir(start_date, end_date)
        if preview_dir.is_dir() and any(preview_dir.glob("slide_*.png")):
            thumbnail_url = (
                f"/api/wsr/preview/image?start_date={start_s}"
                f"&end_date={end_s}&slide_index=1"
            )

        modified = datetime.fromtimestamp(ppt_path.stat().st_mtime)
        weeks.append(
            {
                "report_start_date": start_s,
                "report_end_date": end_s,
                "filename": ppt_path.name,
                "generated_at": modified.isoformat(),
                "story_count": story_count,
                "slide_count": slide_count,
                "thumbnail_url": thumbnail_url,
                "download_url": (
                    f"/api/wsr/download?start_date={start_s}&end_date={end_s}"
                ),
            }
        )

    weeks.sort(key=lambda item: item["report_start_date"], reverse=True)
    return weeks


def load_wsr_week(start_date: date, end_date: date) -> dict:
    """Load an already-generated WSR week from disk (no regeneration)."""
    paths = wsr_output_paths(start_date, end_date)
    if not paths.ppt_path.is_file():
        raise FileNotFoundError(
            f"No WSR deck found for {start_date} to {end_date}. "
            "Call POST /api/wsr/generate first."
        )

    content: dict = {
        "report_start_date": start_date.isoformat(),
        "report_end_date": end_date.isoformat(),
        "slides": [],
        "meta": {
            "story_count": 0,
            "slide_count": 0,
            "titles_from_db": 0,
            "titles_fallback_summary": 0,
            "titles_generated": 0,
            "titles_reused": 0,
        },
    }
    if paths.json_path.is_file():
        with paths.json_path.open(encoding="utf-8") as f:
            content = json.load(f)

    preview_text = ""
    if paths.preview_path.is_file():
        preview_text = paths.preview_path.read_text(encoding="utf-8")

    preview_slides: list[dict] = []
    try:
        preview_slides = export_wsr_slide_previews(
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
        )
    except Exception as exc:
        print(f"Warning: WSR slide preview load failed: {exc}")

    download_url = (
        f"/api/wsr/download?start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}"
    )
    return {
        "report_start_date": content["report_start_date"],
        "report_end_date": content["report_end_date"],
        "meta": content["meta"],
        "slides": content.get("slides", []),
        "preview_slides": preview_slides,
        "preview": preview_text,
        "filename": paths.ppt_path.name,
        "download_url": download_url,
    }

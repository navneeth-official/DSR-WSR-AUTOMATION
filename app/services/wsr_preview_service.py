"""Render generated WSR decks to PNG previews for the frontend viewer."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.paths import wsr_output_paths, wsr_preview_dir
from app.services.ppt_slide_images import (
    export_all_slides_to_png,
    list_all_slide_indices,
)


def build_preview_image_url(
    *,
    start_date: date,
    end_date: date,
    slide_index: int,
) -> str:
    return (
        f"/api/wsr/preview/image?start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}&slide_index={slide_index}"
    )


def _slide_index_from_png(path: Path) -> int | None:
    match = re.match(r"slide_(\d+)\.png$", path.name, re.I)
    if not match:
        return None
    return int(match.group(1))


def list_cached_wsr_slide_previews(
    *,
    start_date: date,
    end_date: date,
) -> list[dict] | None:
    """Return cached PNG previews when they are at least as new as the PPT file."""
    paths = wsr_output_paths(start_date, end_date)
    if not paths.ppt_path.is_file():
        return None

    preview_dir = wsr_preview_dir(start_date, end_date)
    if not preview_dir.is_dir():
        return None

    png_files = sorted(preview_dir.glob("slide_*.png"))
    if not png_files:
        return None

    ppt_mtime = paths.ppt_path.stat().st_mtime
    if any(path.stat().st_mtime < ppt_mtime for path in png_files):
        return None

    titles = {
        item["slide_index"]: item["title"]
        for item in list_all_slide_indices(paths.ppt_path)
    }

    slides: list[dict] = []
    for path in png_files:
        slide_index = _slide_index_from_png(path)
        if slide_index is None:
            continue
        slides.append(
            {
                "slide_index": slide_index,
                "title": titles.get(slide_index) or f"Slide {slide_index}",
                "image_url": build_preview_image_url(
                    start_date=start_date,
                    end_date=end_date,
                    slide_index=slide_index,
                ),
            }
        )

    return slides or None


def export_wsr_slide_previews(
    *,
    start_date: date,
    end_date: date,
    width_px: int = 1280,
    use_cache: bool = True,
) -> list[dict]:
    """
    Return slide preview metadata for a generated WSR deck.

    Reuses cached PNGs when present; otherwise exports via PowerPoint COM.
    """
    if use_cache:
        cached = list_cached_wsr_slide_previews(
            start_date=start_date,
            end_date=end_date,
        )
        if cached is not None:
            return cached

    paths = wsr_output_paths(start_date, end_date)
    if not paths.ppt_path.is_file():
        raise FileNotFoundError(
            f"No WSR deck found for {start_date} to {end_date}: {paths.ppt_path}"
        )

    preview_dir = wsr_preview_dir(start_date, end_date)
    preview_dir.mkdir(parents=True, exist_ok=True)

    exported = export_all_slides_to_png(
        paths.ppt_path,
        preview_dir,
        width_px=width_px,
    )
    if not exported:
        slides = list_all_slide_indices(paths.ppt_path)
        exported = [
            {
                "slide_index": s["slide_index"],
                "title": s["title"],
                "image_path": str(
                    preview_dir / f"slide_{s['slide_index']:02d}.png"
                ),
            }
            for s in slides
        ]

    return [
        {
            "slide_index": item["slide_index"],
            "title": item.get("title") or f"Slide {item['slide_index']}",
            "image_url": build_preview_image_url(
                start_date=start_date,
                end_date=end_date,
                slide_index=int(item["slide_index"]),
            ),
        }
        for item in sorted(exported, key=lambda row: int(row["slide_index"]))
    ]


def resolve_preview_image_path(
    *,
    start_date: date,
    end_date: date,
    slide_index: int,
) -> Path:
    image_path = wsr_preview_dir(start_date, end_date) / f"slide_{slide_index:02d}.png"
    if not image_path.is_file():
        raise FileNotFoundError(f"Preview image not found: {image_path}")
    return image_path

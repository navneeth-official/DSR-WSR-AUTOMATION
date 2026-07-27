"""Repository path constants for templates, scripts, and generated outputs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
OUTPUT_DIR = REPO_ROOT / "output"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"

G10X_TEMPLATE_NAME = "G10X H-E-B WSR Sustainment 05 June 2026 .pptx"
G10X_TEMPLATE = TEMPLATES_DIR / G10X_TEMPLATE_NAME
PPT_BUILDER = SCRIPTS_DIR / "update_delivery_status.py"

DEFAULT_CONTENT_JSON = OUTPUT_DIR / "ppt_content.json"
DEFAULT_CONTENT_PREVIEW = OUTPUT_DIR / "ppt_content_preview.txt"
DEFAULT_PPT_OUTPUT = OUTPUT_DIR / "HEB_Delivery_Status.pptx"
GEOMETRY_DEBUG_LOG = OUTPUT_DIR / "layout_geometry_debug.log"


class WsrOutputPaths:
    def __init__(self, json_path: Path, preview_path: Path, ppt_path: Path) -> None:
        self.json_path = json_path
        self.preview_path = preview_path
        self.ppt_path = ppt_path


def wsr_output_paths(start_date: date, end_date: date) -> WsrOutputPaths:
    """Per-week output files under output/."""
    stem = f"WSR_{start_date.isoformat()}_{end_date.isoformat()}"
    return WsrOutputPaths(
        json_path=OUTPUT_DIR / f"{stem}.json",
        preview_path=OUTPUT_DIR / f"{stem}_preview.txt",
        ppt_path=OUTPUT_DIR / f"{stem}.pptx",
    )


def wsr_preview_dir(start_date: date, end_date: date) -> Path:
    """Directory for rendered PNG previews of a WSR deck."""
    stem = f"WSR_{start_date.isoformat()}_{end_date.isoformat()}"
    return OUTPUT_DIR / f"{stem}_slides"


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def evaluation_report_paths(ppt_path: Path) -> tuple[Path, Path, Path]:
    """User JSON, user text, and internal debug JSON paths under output/."""
    ensure_output_dir()
    stem = Path(ppt_path).stem
    return (
        OUTPUT_DIR / f"{stem}.format_eval.json",
        OUTPUT_DIR / f"{stem}.format_eval.txt",
        OUTPUT_DIR / f"{stem}.format_eval.internal.json",
    )


def evaluation_ai_report_paths(ppt_path: Path) -> tuple[Path, Path]:
    """Visual AI review JSON + text paths under output/."""
    ensure_output_dir()
    stem = Path(ppt_path).stem
    return (
        OUTPUT_DIR / f"{stem}.format_eval.ai.json",
        OUTPUT_DIR / f"{stem}.format_eval.ai.txt",
    )

"""
Evaluate a delivery-status PowerPoint deck against the G10X template rulebook.

Per-slide and deck PASS/FAIL — no repairs, evaluation only.
Reports are saved under output/ by default (JSON + text document).

Usage:
    python scripts/evaluate_ppt_format.py --ppt output/HEB_Delivery_Status.pptx
    python scripts/evaluate_ppt_format.py --ppt output/HEB_Delivery_Status.pptx --mode deterministic
    python scripts/evaluate_ppt_format.py --ppt output/HEB_Delivery_Status.pptx --mode full --vision
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.paths import DEFAULT_CONTENT_JSON, evaluation_report_paths  # noqa: E402
from app.services.ppt_format_report import (  # noqa: E402
    evaluate_ppt_format,
    format_deck_pass_fail_report,
    save_evaluation_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate G10X delivery-status deck template compliance "
            "(spacing, overlap, typography, layout). Reports PASS/FAIL per slide."
        )
    )
    parser.add_argument(
        "--ppt",
        required=True,
        help="Path to .pptx deck (e.g. output/HEB_Delivery_Status.pptx)",
    )
    parser.add_argument(
        "--content",
        default="",
        help=f"Optional ppt_content.json (default when present: {DEFAULT_CONTENT_JSON.name})",
    )
    parser.add_argument(
        "--mode",
        choices=("full", "ai", "deterministic", "vision"),
        default="full",
        help=(
            "full = deterministic + AI; add --vision for visual review; "
            "ai = AI rulebook only; deterministic = rules only; vision = visual review only"
        ),
    )
    parser.add_argument(
        "--all-slides",
        action="store_true",
        help="Include untouched G10X template placeholder slides (default: content scope only)",
    )
    parser.add_argument(
        "--vision",
        action="store_true",
        help="Include qualitative vision review (full mode only; requires Windows + vision API)",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="JSON report path (default: output/<deck>.format_eval.json)",
    )
    parser.add_argument(
        "--report-out",
        default="",
        help="Human-readable report path (default: output/<deck>.format_eval.txt)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print to terminal only; do not write report files",
    )
    parser.add_argument(
        "--images-dir",
        default="",
        help="Directory for rendered slide PNGs (vision/full modes)",
    )
    args = parser.parse_args()

    ppt_path = Path(args.ppt).resolve()
    if not ppt_path.is_file():
        print(f"Error: file not found: {ppt_path}", file=sys.stderr)
        sys.exit(2)

    content_json: Path | None
    if args.content:
        content_json = Path(args.content).resolve()
    elif DEFAULT_CONTENT_JSON.is_file():
        content_json = DEFAULT_CONTENT_JSON.resolve()
    else:
        content_json = None

    images_dir = Path(args.images_dir).resolve() if args.images_dir else None

    report = evaluate_ppt_format(
        ppt_path,
        mode=args.mode,
        content_json=content_json,
        scope_all_slides=args.all_slides,
        images_dir=images_dir,
        include_vision=args.vision,
    )

    print(format_deck_pass_fail_report(report))

    if not args.no_save:
        default_json, default_report = evaluation_report_paths(ppt_path)
        json_path = Path(args.json_out).resolve() if args.json_out else default_json
        report_path = Path(args.report_out).resolve() if args.report_out else default_report
        save_evaluation_reports(
            report,
            json_path=json_path,
            report_path=report_path,
        )
        print(f"JSON report  -> {json_path}")
        print(f"Text report  -> {report_path}")

    sys.exit(0 if report.deck_pass else 1)


if __name__ == "__main__":
    main()

"""
Evaluate a delivery-status PowerPoint deck against the G10X template rulebook.

Hybrid evaluation (default): deterministic geometry + visual AI review.
Reports are saved under output/ by default (JSON + text document).

Usage:
    python scripts/evaluate_ppt_format.py --ppt output/HEB_Delivery_Status.pptx
    python scripts/evaluate_ppt_format.py --ppt output/HEB_Delivery_Status.pptx --mode deterministic
    python scripts/evaluate_ppt_format.py --ppt output/HEB_Delivery_Status.pptx --no-visual
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.paths import (  # noqa: E402
    DEFAULT_CONTENT_JSON,
    evaluation_ai_report_paths,
    evaluation_report_paths,
)
from app.services.ppt_format_report import (  # noqa: E402
    evaluate_ppt_format,
    save_evaluation_reports,
)
from app.services.ppt_format_user_report import format_evaluation_for_terminal  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Hybrid G10X delivery-status deck evaluation: "
            "deterministic geometry (source of truth) + visual AI quality review."
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
        choices=("full", "ai", "deterministic", "visual"),
        default="full",
        help=(
            "full = deterministic + visual (default); "
            "deterministic = measurable layout only; "
            "visual = subjective visual review only; "
            "ai = deprecated legacy rulebook auditor"
        ),
    )
    parser.add_argument(
        "--all-slides",
        action="store_true",
        help="Include untouched G10X template placeholder slides (default: content scope only)",
    )
    parser.add_argument(
        "--no-visual",
        action="store_true",
        help="Skip visual AI review in full mode (deterministic only)",
    )
    parser.add_argument(
        "--vision",
        action="store_true",
        help="Deprecated alias for visual review (enabled by default in full mode)",
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
        help="Directory for rendered slide PNGs (visual/full modes)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress raw vision API logs on the terminal (still written to vision_api_*.log)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print developer report with rule IDs and measurements (default: user-facing report)",
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

    include_visual = not args.no_visual
    if args.vision:
        include_visual = True

    report = evaluate_ppt_format(
        ppt_path,
        mode=args.mode,
        content_json=content_json,
        scope_all_slides=args.all_slides,
        images_dir=images_dir,
        include_visual=include_visual,
        quiet_vision_log=args.quiet,
    )

    print(format_evaluation_for_terminal(report, debug=args.debug))

    if not args.no_save:
        default_json, default_report, default_internal = evaluation_report_paths(ppt_path)
        default_ai_json, default_ai_report = evaluation_ai_report_paths(ppt_path)
        json_path = Path(args.json_out).resolve() if args.json_out else default_json
        report_path = Path(args.report_out).resolve() if args.report_out else default_report
        save_evaluation_reports(
            report,
            json_path=json_path,
            report_path=report_path,
            internal_json_path=default_internal,
            ai_json_path=default_ai_json,
            ai_report_path=default_ai_report,
        )
        print(f"Evaluation result -> {report_path}")
        print(f"JSON report       -> {json_path}")
        if not args.no_visual:
            print(f"AI visual review  -> {default_ai_report}")
            print(f"AI visual (JSON)  -> {default_ai_json}")
        print(f"Internal log      -> {default_internal}")

    sys.exit(0 if report.deck_pass else 1)


if __name__ == "__main__":
    main()

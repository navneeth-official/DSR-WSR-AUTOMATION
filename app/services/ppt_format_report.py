"""Unified PPT template-format evaluation — per-slide and deck PASS/FAIL."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.pipeline.qualitative_reviewer import QualitativeVisionReviewer
from app.pipeline.types import RenderBatch, RenderedSlide
from app.services.ppt_format_evaluator import (
    evaluate_deck_format,
    load_rulebook,
)
from app.services.ppt_format_extractor import extract_deck
from app.services.ppt_format_violations import detect_deck_violations
from app.services.ppt_slide_images import export_slides_to_png, list_delivery_slide_indices
from app.services.title_generator import create_llm_client

EvaluatorMode = Literal["full", "ai", "deterministic", "vision"]

_FAIL_SEVERITIES = frozenset({"critical", "major"})


@dataclass
class SlideFormatResult:
    slide_index: int
    title: str
    passed: bool
    deterministic_pass: bool | None = None
    ai_pass: bool | None = None
    vision_pass: bool | None = None
    score: float | None = None
    category_scores: dict[str, float] = field(default_factory=dict)
    violations: list[dict[str, Any]] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_index": self.slide_index,
            "title": self.title,
            "pass": self.passed,
            "deterministic_pass": self.deterministic_pass,
            "ai_pass": self.ai_pass,
            "vision_pass": self.vision_pass,
            "score": self.score,
            "category_scores": self.category_scores,
            "violations": self.violations,
            "strengths": self.strengths,
        }


@dataclass
class DeckFormatReport:
    source_file: str
    mode: str
    deck_pass: bool
    deck_score: float | None
    slides: list[SlideFormatResult]
    summary: str = ""
    critical_issues: list[str] = field(default_factory=list)
    rulebook_version: str = ""
    vision_model: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "mode": self.mode,
            "deck_pass": self.deck_pass,
            "deck_score": self.deck_score,
            "slides": [s.to_dict() for s in self.slides],
            "summary": self.summary,
            "critical_issues": self.critical_issues,
            "rulebook_version": self.rulebook_version,
            "vision_model": self.vision_model,
            "errors": self.errors,
        }


def _service_base_title(title: str) -> str:
    base = re.sub(r"^Delivery status\s*[–-]\s*", "", title, flags=re.I)
    return re.sub(r"\s*\(Contd.*\)\s*$", "", base, flags=re.I).strip()


def _load_content_titles(content_json: Path | None) -> set[str] | None:
    if content_json is None or not content_json.is_file():
        return None
    with open(content_json, encoding="utf-8") as f:
        data = json.load(f)
    slides = data.get("slides", data)
    return {s["title"].strip() for s in slides if s.get("title")}


def _deterministic_slide_pass(
    violations: list[dict[str, Any]],
    *,
    fail_severities: frozenset[str] = _FAIL_SEVERITIES,
) -> bool:
    return not any(v.get("severity") in fail_severities for v in violations)


def _group_violations_by_slide(
    violations: list[dict[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for v in violations:
        idx = v.get("slide_index")
        if idx is None:
            continue
        grouped.setdefault(int(idx), []).append(v)
    return grouped


def _merge_slide_results(
    deck_data: dict[str, Any],
    *,
    det_by_slide: dict[int, list[dict[str, Any]]],
    ai_by_slide: dict[int, dict[str, Any]],
    vision_by_slide: dict[int, dict[str, Any]],
    use_deterministic: bool,
    use_ai: bool,
    use_vision: bool,
) -> list[SlideFormatResult]:
    results: list[SlideFormatResult] = []
    for slide in deck_data.get("slides", []):
        idx = int(slide["slide_index"])
        title = slide.get("title", "")

        det_violations = list(det_by_slide.get(idx, []))
        ai_slide = ai_by_slide.get(idx, {})
        vis_slide = vision_by_slide.get(idx, {})

        violations: list[dict[str, Any]] = list(det_violations)
        for v in ai_slide.get("violations", []):
            violations.append({**v, "source": "ai"})
        for issue in vis_slide.get("issues", []):
            if issue.get("category") == "no_issue":
                continue
            violations.append({
                "rule_id": f"VISION-{issue.get('category', 'layout').upper()}",
                "severity": issue.get("severity", "medium"),
                "message": issue.get("description", ""),
                "source": "vision",
            })

        det_pass = (
            _deterministic_slide_pass(det_violations) if use_deterministic else None
        )
        ai_pass = ai_slide.get("pass") if use_ai else None
        vis_pass = vis_slide.get("pass") if use_vision else None

        checks = [c for c in (det_pass, ai_pass, vis_pass) if c is not None]
        passed = bool(checks) and all(checks)

        results.append(
            SlideFormatResult(
                slide_index=idx,
                title=title,
                passed=passed,
                deterministic_pass=det_pass,
                ai_pass=ai_pass,
                vision_pass=vis_pass,
                score=ai_slide.get("score"),
                category_scores=dict(ai_slide.get("category_scores") or {}),
                violations=violations,
                strengths=list(ai_slide.get("strengths") or []),
            )
        )
    return results


def _run_vision_review(
    ppt_path: Path,
    *,
    slide_indices: list[int] | None = None,
    images_dir: Path | None = None,
) -> tuple[dict[int, dict[str, Any]], str]:
    """Render delivery slides and run qualitative vision review."""
    indices = slide_indices
    if indices is None:
        indices = [s["slide_index"] for s in list_delivery_slide_indices(ppt_path)]

    out_dir = images_dir
    cleanup = False
    if out_dir is None:
        out_dir = Path(tempfile.mkdtemp(prefix="ppt_format_eval_", dir=ppt_path.parent))
        cleanup = False  # keep for debugging unless caller sets images_dir

    exported = export_slides_to_png(ppt_path, out_dir, slide_indices=indices)
    rendered = [
        RenderedSlide(
            slide_index=item["slide_index"],
            title=item.get("title", ""),
            image_path=Path(item["image_path"]),
        )
        for item in exported
    ]
    batch = RenderBatch(ppt_path=ppt_path, output_dir=out_dir, slides=rendered)
    report = QualitativeVisionReviewer().evaluate(batch)

    by_slide: dict[int, dict[str, Any]] = {}
    for slide in report.slides:
        by_slide[slide.slide_index] = {
            "pass": slide.passes,
            "status": slide.status.value,
            "overall_quality": slide.overall_quality,
            "issues": [i.to_dict() for i in slide.issues],
        }
    return by_slide, report.vision_model


def evaluate_ppt_format(
    ppt_path: str | Path,
    *,
    mode: EvaluatorMode = "full",
    content_json: Path | None = None,
    scope_all_slides: bool = False,
    images_dir: Path | None = None,
    rulebook_path: Path | None = None,
    include_vision: bool = False,
) -> DeckFormatReport:
    """
    Evaluate a delivery-status deck against the G10X template rulebook.

    Modes:
    - ``full`` (default): deterministic rules + AI rulebook auditor.
    - ``ai``: AI rulebook only (typography, spacing, structure from extracted metrics).
    - ``deterministic``: spacing/overlap/bullet rules only (no API).
    - ``vision``: rendered-slide qualitative review only (Windows COM + vision API).

    Pass ``include_vision=True`` (CLI ``--vision``) to add visual review to ``full`` mode.

    Per-slide ``pass`` is True only when every enabled layer passes.
    Deck ``pass`` is True only when every evaluated slide passes.
    """
    ppt_path = Path(ppt_path).resolve()
    rulebook = load_rulebook(rulebook_path)

    use_deterministic = mode in ("full", "deterministic")
    use_ai = mode in ("full", "ai")
    use_vision = mode == "vision" or (mode == "full" and include_vision)

    deck_data = extract_deck(ppt_path)
    content_titles = _load_content_titles(content_json)
    errors: list[str] = []

    det_by_slide: dict[int, list[dict[str, Any]]] = {}
    if use_deterministic:
        det = detect_deck_violations(
            deck_data,
            content_titles=content_titles,
            scope_all_slides=scope_all_slides,
        )
        det_by_slide = _group_violations_by_slide(det.get("violations", []))

    ai_by_slide: dict[int, dict[str, Any]] = {}
    ai_result: dict[str, Any] = {}
    if use_ai:
        client, _model = create_llm_client()
        if client is None:
            errors.append(
                "Azure/OpenAI not configured — skipped AI evaluation "
                "(set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)."
            )
            if mode == "ai":
                raise RuntimeError(errors[-1])
        else:
            try:
                ai_result = evaluate_deck_format(ppt_path, rulebook_path)
                for slide in ai_result.get("slides", []):
                    ai_by_slide[int(slide["slide_index"])] = slide
            except Exception as exc:  # noqa: BLE001
                errors.append(f"AI evaluation failed: {exc}")
                if mode == "ai":
                    raise

    vision_by_slide: dict[int, dict[str, Any]] = {}
    vision_model = ""
    if use_vision:
        try:
            scope_indices = None
            if content_titles and not scope_all_slides:
                allowed = {t.strip().lower() for t in content_titles}
                scope_indices = [
                    s["slide_index"]
                    for s in list_delivery_slide_indices(ppt_path)
                    if _service_base_title(s.get("title", "")).lower() in allowed
                ]
            vision_by_slide, vision_model = _run_vision_review(
                ppt_path, slide_indices=scope_indices, images_dir=images_dir
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Vision evaluation failed: {exc}")
            if mode == "vision":
                raise

    # When AI-only mode without extract slides in ai result, use deck extract
    if not deck_data.get("slides") and ai_by_slide:
        deck_data = {
            "file": str(ppt_path),
            "slides": [
                {"slide_index": idx, "title": s.get("title", "")}
                for idx, s in sorted(ai_by_slide.items())
            ],
        }

    slides = _merge_slide_results(
        deck_data,
        det_by_slide=det_by_slide,
        ai_by_slide=ai_by_slide,
        vision_by_slide=vision_by_slide,
        use_deterministic=use_deterministic,
        use_ai=use_ai and bool(ai_by_slide),
        use_vision=use_vision and bool(vision_by_slide),
    )

    if content_titles and not scope_all_slides:
        allowed_lower = {t.strip().lower() for t in content_titles}
        slides = [
            s
            for s in slides
            if _service_base_title(s.title).lower() in allowed_lower
        ]

    deck_pass = bool(slides) and all(s.passed for s in slides)

    scores = [s.score for s in slides if s.score is not None]
    deck_score: float | None = None
    if ai_result.get("deck_score") is not None:
        deck_score = float(ai_result["deck_score"])
    elif scores:
        deck_score = round(sum(scores) / len(scores), 1)

    if deck_score is not None and use_ai and not use_deterministic and not use_vision:
        deck_pass = bool(ai_result.get("deck_pass", deck_pass))

    summary_parts = []
    if use_deterministic:
        n_fail = sum(1 for s in slides if s.deterministic_pass is False)
        summary_parts.append(
            f"Deterministic: {len(slides) - n_fail}/{len(slides)} slide(s) pass"
        )
    if use_ai and ai_by_slide:
        n_fail = sum(1 for s in slides if s.ai_pass is False)
        summary_parts.append(f"AI rulebook: {len(slides) - n_fail}/{len(slides)} pass")
    if use_vision and vision_by_slide:
        n_fail = sum(1 for s in slides if s.vision_pass is False)
        summary_parts.append(f"Vision: {len(slides) - n_fail}/{len(slides)} pass")

    return DeckFormatReport(
        source_file=str(ppt_path),
        mode=mode,
        deck_pass=deck_pass,
        deck_score=deck_score,
        slides=slides,
        summary="; ".join(summary_parts) or "No slides evaluated.",
        critical_issues=list(ai_result.get("critical_issues") or []),
        rulebook_version=rulebook.get("meta", {}).get("version", ""),
        vision_model=vision_model,
        errors=errors,
    )


def format_deck_pass_fail_report(report: DeckFormatReport) -> str:
    """Human-readable PASS/FAIL report for terminal output."""
    lines = [
        f"Deck: {report.source_file}",
        f"Evaluator: {report.mode} (rulebook v{report.rulebook_version or '?'})",
    ]
    if report.deck_score is not None:
        lines.append(f"Score: {report.deck_score}/100")
    lines.append(
        f"Result: {'PASS' if report.deck_pass else 'FAIL'}",
    )
    if report.summary:
        lines.append(report.summary)
    if report.vision_model:
        lines.append(f"Vision model: {report.vision_model}")
    if report.errors:
        lines.append("")
        lines.append("Warnings:")
        for err in report.errors:
            lines.append(f"  - {err}")
    if report.critical_issues:
        lines.append("")
        lines.append("Critical issues:")
        for issue in report.critical_issues:
            lines.append(f"  - {issue}")
    lines.append("")
    lines.append("Per slide:")
    for slide in report.slides:
        status = "PASS" if slide.passed else "FAIL"
        parts = [status]
        if slide.deterministic_pass is not None:
            parts.append(f"det={'PASS' if slide.deterministic_pass else 'FAIL'}")
        if slide.ai_pass is not None:
            parts.append(f"ai={'PASS' if slide.ai_pass else 'FAIL'}")
            if slide.score is not None:
                parts.append(f"score={slide.score}")
        if slide.vision_pass is not None:
            parts.append(f"vision={'PASS' if slide.vision_pass else 'FAIL'}")
        lines.append(
            f"  Slide {slide.slide_index:2d}  {' | '.join(parts)}  {slide.title[:55]}"
        )
        for v in slide.violations[:6]:
            sev = v.get("severity", "?").upper()
            rid = v.get("rule_id", "?")
            msg = v.get("message", "")[:90]
            src = v.get("source", "rule")
            lines.append(f"           [{sev}] {rid} ({src}): {msg}")
        if len(slide.violations) > 6:
            lines.append(f"           … +{len(slide.violations) - 6} more")
    lines.append("")
    lines.append(f"Overall: {'PASS' if report.deck_pass else 'FAIL'}")
    return "\n".join(lines)


def save_evaluation_reports(
    report: DeckFormatReport,
    *,
    json_path: Path,
    report_path: Path,
) -> tuple[Path, Path]:
    """Write JSON + human-readable evaluation documents under output/."""
    json_path = Path(json_path)
    report_path = Path(report_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(format_deck_pass_fail_report(report), encoding="utf-8")
    return json_path, report_path

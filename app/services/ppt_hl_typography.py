"""Deterministic Highlights (HL) typography validation — font, size, line spacing."""

from __future__ import annotations

from typing import Any

# G10X template uses Manrope family; story lines often resolve to theme +mn-lt.
MANROPE_FONTS = frozenset({
    "Manrope",
    "Manrope Light",
    "Manrope Bold",
    "+mn-lt",
    "+mj-lt",
})
STORY_FONTS = frozenset({
    "Manrope Light",
    "+mn-lt",
    "Manrope",
})

HL_HEADER_SIZE_PT = 14.0
HL_BODY_SIZE_PT = 12.0
# Template body paragraphs use fixed 16pt line height (a:lnSpc/a:spcPts val=1600).
HL_LINE_SPACING_PT = 16.0
SIZE_TOLERANCE_PT = 0.05
LINE_SPACING_TOLERANCE_PT = 0.5
SPC_BEF_TOLERANCE_PT = 0.05

_CATEGORY_ROLES = frozenset({
    "category_completed",
    "category_released",
    "category_inprogress",
    "category_other",
})
_SPACING_ROLES = frozenset({
    "sprint_line",
    "current_week",
    "story_item",
    *_CATEGORY_ROLES,
})


def _size_matches(actual: float | None, expected: float) -> bool:
    if actual is None:
        return True
    return abs(actual - expected) <= SIZE_TOLERANCE_PT


def _font_matches(actual: str | None, allowed: frozenset[str]) -> bool:
    if not actual:
        return True
    return actual in allowed


def _primary_run_style(para: dict[str, Any]) -> dict[str, Any]:
    """Dominant font/size/bold from runs (prefer first non-empty text run)."""
    runs = para.get("runs") or []
    for run in runs:
        if (run.get("text") or "").strip():
            return {
                "font": run.get("font"),
                "size_pt": run.get("size_pt"),
                "bold": run.get("bold"),
            }
    if runs:
        run = runs[0]
        return {
            "font": run.get("font"),
            "size_pt": run.get("size_pt"),
            "bold": run.get("bold"),
        }
    return {}


def _all_runs_style(para: dict[str, Any]) -> list[dict[str, Any]]:
    runs = para.get("runs") or []
    if not runs:
        return []
    styles = []
    for run in runs:
        if (run.get("text") or "").strip() or len(runs) == 1:
            styles.append({
                "font": run.get("font"),
                "size_pt": run.get("size_pt"),
                "bold": run.get("bold"),
            })
    return styles or [{
        "font": runs[0].get("font"),
        "size_pt": runs[0].get("size_pt"),
        "bold": runs[0].get("bold"),
    }]


def _line_spacing_ok(para: dict[str, Any]) -> bool:
    pts = para.get("line_spacing_pt")
    if pts is None:
        return True
    return abs(float(pts) - HL_LINE_SPACING_PT) <= LINE_SPACING_TOLERANCE_PT


def _spc_bef_ok(para: dict[str, Any]) -> bool:
    spc = para.get("spc_bef_pt")
    if spc is None:
        return True
    return float(spc) <= SPC_BEF_TOLERANCE_PT


def _snippet(text: str, limit: int = 60) -> str:
    t = (text or "").strip()
    return t if len(t) <= limit else t[: limit - 1] + "…"


def detect_hl_typography_violations(
    hl: dict[str, Any],
    *,
    slide_index: int | None = None,
    title: str = "",
) -> list[dict[str, Any]]:
    """
    Validate HL header and content typography against the G10X rulebook.

    Only flags explicitly set values that contradict the template — inherited
    theme defaults without explicit run properties are not penalized.
    """
    violations: list[dict[str, Any]] = []
    details_by_rule: dict[str, list[dict[str, Any]]] = {}

    def _add(rule_id: str, severity: str, message: str, detail: dict[str, Any]) -> None:
        details_by_rule.setdefault(rule_id, []).append(detail)
        if rule_id not in {v["rule_id"] for v in violations}:
            violations.append({
                "rule_id": rule_id,
                "severity": severity,
                "slide_index": slide_index,
                "title": title,
                "message": message,
                "details": details_by_rule[rule_id],
            })
        else:
            for v in violations:
                if v["rule_id"] == rule_id:
                    v["details"] = details_by_rule[rule_id]
                    break

    header = hl.get("header_metrics") or {}
    for run in header.get("runs") or []:
        font = run.get("font")
        size = run.get("size_pt")
        bold = run.get("bold")
        if font and not _font_matches(font, MANROPE_FONTS):
            _add(
                "HL-HDR-02",
                "major",
                "Highlights header must use Manrope Bold 14pt",
                {"issue": "wrong_font", "font": font, "expected_font": "Manrope"},
            )
        if size is not None and not _size_matches(size, HL_HEADER_SIZE_PT):
            _add(
                "HL-HDR-02",
                "major",
                "Highlights header must use Manrope Bold 14pt",
                {"issue": "wrong_size", "size_pt": size, "expected_size_pt": HL_HEADER_SIZE_PT},
            )
        if bold is False:
            _add(
                "HL-HDR-02",
                "minor",
                "Highlights header must use Manrope Bold 14pt",
                {"issue": "not_bold", "expected_bold": True},
            )

    for para in hl.get("paragraphs") or []:
        role = para.get("role", "")
        text = para.get("text", "")
        if not text or role == "blank":
            continue

        style = _primary_run_style(para)

        if role == "project_name":
            if style.get("font") and not _font_matches(style["font"], MANROPE_FONTS):
                _add("HL-P-01", "major", "Project label must use Manrope 12pt bold", {
                    "role": role, "issue": "wrong_font", "font": style["font"],
                    "text": _snippet(text),
                })
            if style.get("size_pt") is not None and not _size_matches(style["size_pt"], HL_BODY_SIZE_PT):
                _add("HL-P-01", "major", "Project label must use Manrope 12pt bold", {
                    "role": role, "issue": "wrong_size", "size_pt": style["size_pt"],
                    "text": _snippet(text),
                })
            if style.get("bold") is False:
                _add("HL-P-01", "minor", "Project label must use Manrope 12pt bold", {
                    "role": role, "issue": "not_bold", "text": _snippet(text),
                })

        elif role == "sprint_line":
            for run_style in _all_runs_style(para):
                if run_style.get("font") and not _font_matches(run_style["font"], MANROPE_FONTS):
                    _add("HL-P-02", "major", "Sprint line must use Manrope / Manrope Light 12pt", {
                        "role": role, "issue": "wrong_font", "font": run_style["font"],
                        "text": _snippet(text),
                    })
                if run_style.get("size_pt") is not None and not _size_matches(
                    run_style["size_pt"], HL_BODY_SIZE_PT
                ):
                    _add("HL-P-02", "major", "Sprint line must use Manrope / Manrope Light 12pt", {
                        "role": role, "issue": "wrong_size", "size_pt": run_style["size_pt"],
                        "text": _snippet(text),
                    })

        elif role == "current_week":
            if style.get("font") and not _font_matches(style["font"], MANROPE_FONTS):
                _add("HL-P-03", "major", "Current week status must use Manrope Light 12pt", {
                    "role": role, "issue": "wrong_font", "font": style["font"],
                    "text": _snippet(text),
                })
            if style.get("size_pt") is not None and not _size_matches(style["size_pt"], HL_BODY_SIZE_PT):
                _add("HL-P-03", "major", "Current week status must use Manrope Light 12pt", {
                    "role": role, "issue": "wrong_size", "size_pt": style["size_pt"],
                    "text": _snippet(text),
                })

        elif role in _CATEGORY_ROLES:
            if style.get("font") and not _font_matches(style["font"], MANROPE_FONTS):
                _add("HL-P-04", "major", "Category header must use Manrope 12pt bold", {
                    "role": role, "issue": "wrong_font", "font": style["font"],
                    "text": _snippet(text),
                })
            if style.get("size_pt") is not None and not _size_matches(style["size_pt"], HL_BODY_SIZE_PT):
                _add("HL-P-04", "major", "Category header must use Manrope 12pt bold", {
                    "role": role, "issue": "wrong_size", "size_pt": style["size_pt"],
                    "text": _snippet(text),
                })
            if style.get("bold") is False:
                _add("HL-P-04", "minor", "Category header must use Manrope 12pt bold", {
                    "role": role, "issue": "not_bold", "text": _snippet(text),
                })

        elif role == "story_item":
            if style.get("font") and not _font_matches(style["font"], STORY_FONTS):
                _add("HL-P-05", "major", "Story line must use Manrope Light 12pt", {
                    "role": role, "issue": "wrong_font", "font": style["font"],
                    "text": _snippet(text),
                })
            if style.get("size_pt") is not None and not _size_matches(style["size_pt"], HL_BODY_SIZE_PT):
                _add("HL-P-05", "major", "Story line must use Manrope Light 12pt", {
                    "role": role, "issue": "wrong_size", "size_pt": style["size_pt"],
                    "text": _snippet(text),
                })
            if style.get("bold") is True:
                _add("HL-P-05", "minor", "Story line must use Manrope Light 12pt regular weight", {
                    "role": role, "issue": "unexpected_bold", "text": _snippet(text),
                })
            if not _spc_bef_ok(para):
                _add("HL-SPC-04", "minor", "Story bullets must not add space-before", {
                    "role": role, "issue": "spc_bef_nonzero",
                    "spc_bef_pt": para.get("spc_bef_pt"), "text": _snippet(text),
                })

        if role in _SPACING_ROLES:
            if not _line_spacing_ok(para):
                _add(
                    "HL-SPC-02",
                    "major",
                    f"HL line spacing must be {HL_LINE_SPACING_PT:g}pt (template single spacing)",
                    {
                        "role": role,
                        "issue": "wrong_line_spacing",
                        "line_spacing_pt": para.get("line_spacing_pt"),
                        "expected_line_spacing_pt": HL_LINE_SPACING_PT,
                        "text": _snippet(text),
                    },
                )

    return violations


def summarize_hl_typography(hl: dict[str, Any]) -> dict[str, Any]:
    """Compact typography summary for visual AI context."""
    header = hl.get("header_metrics") or {}
    header_run = (header.get("runs") or [{}])[0]
    paras = [p for p in (hl.get("paragraphs") or []) if p.get("text") and p.get("role") != "blank"]

    fonts: set[str] = set()
    sizes: set[float] = set()
    line_spacings: set[float] = set()
    for para in paras:
        for run in para.get("runs") or []:
            if run.get("font"):
                fonts.add(str(run["font"]))
            if run.get("size_pt") is not None:
                sizes.add(float(run["size_pt"]))
        if para.get("line_spacing_pt") is not None:
            line_spacings.add(float(para["line_spacing_pt"]))

    violations = detect_hl_typography_violations(hl)
    return {
        "header_font": header_run.get("font"),
        "header_size_pt": header_run.get("size_pt"),
        "header_bold": header_run.get("bold"),
        "body_fonts": sorted(fonts),
        "body_sizes_pt": sorted(sizes),
        "line_spacings_pt": sorted(line_spacings),
        "expected_header": {"font": "Manrope", "size_pt": HL_HEADER_SIZE_PT, "bold": True},
        "expected_body": {"fonts": sorted(MANROPE_FONTS), "size_pt": HL_BODY_SIZE_PT},
        "expected_line_spacing_pt": HL_LINE_SPACING_PT,
        "typography_violation_count": len(violations),
        "typography_rule_ids": sorted({v["rule_id"] for v in violations}),
    }

"""Deterministic spacing/layout violation detection for delivery-status slides."""

from __future__ import annotations

import re
from typing import Any

from app.services.ppt_layout_metrics import (
    FOOTER_MAX_BOTTOM_IN,
    FOOTER_MAX_HL_DENSE_BOTTOM_IN,
    DEFAULT_EMPTY_KA_HEIGHT_IN,
    HL_KA_MAX_BORDER_GAP_IN,
    HL_KA_MIN_BORDER_GAP_IN,
    MIN_KA_BLOCK_IN,
    MIN_TEXT_KA_CLEARANCE_IN,
    SPARSE_CONTD_MAX_FILLED,
    SPARSE_HL_MAX_WASTE_IN,
    SPARSE_KA_MAX_WASTE_IN,
    UTILIZATION_THRESHOLD,
    hl_is_dense,
)


def _service_base_title(title: str) -> str:
    base = re.sub(r"^Delivery status\s*[–-]\s*", "", title, flags=re.I)
    return re.sub(r"\s*\(Contd.*\)\s*$", "", base, flags=re.I).strip()


def _main_hl_is_dense(main: dict[str, Any]) -> bool:
    hl = main.get("highlights")
    if not hl:
        return False
    return hl_is_dense(hl)


def _ka_would_fit_on_main(main: dict[str, Any]) -> bool:
    """True when an empty KA table fits below HL text within the footer zone."""
    text_bottom = main.get("hl_text_bottom_for_fit_in") or main.get(
        "estimated_text_bottom_in"
    )
    if text_bottom is None:
        return False
    ka_top = text_bottom + MIN_TEXT_KA_CLEARANCE_IN
    return ka_top + DEFAULT_EMPTY_KA_HEIGHT_IN <= FOOTER_MAX_BOTTOM_IN


def _expected_sprint_gaps(paras: list[dict]) -> int:
    sprint_count = sum(1 for p in paras if p.get("role") == "sprint_line")
    return max(sprint_count - 1, 0)


def detect_slide_violations(slide: dict[str, Any]) -> list[dict[str, Any]]:
    """Return violation dicts for one extracted slide."""
    violations: list[dict[str, Any]] = []
    idx = slide.get("slide_index")
    title = slide.get("title", "")

    if re.search(r"Delivery status\s+-\s+", title) and not re.search(
        r"Delivery status\s+–\s+", title
    ):
        violations.append({
            "rule_id": "TITLE-01",
            "severity": "major",
            "slide_index": idx,
            "title": title,
            "message": "Slide title uses hyphen '-' instead of en dash '–' after Delivery status",
        })

    hl = slide.get("highlights")

    if hl:
        if hl.get("category_bullet_violations"):
            violations.append({
                "rule_id": "HL-P-04",
                "severity": "critical",
                "slide_index": idx,
                "title": title,
                "message": "Category headers use wrong bullet (must be Wingdings Ø at level 7)",
                "details": hl["category_bullet_violations"],
            })

        if hl.get("category_to_story_blank_gaps", 0) > 0:
            violations.append({
                "rule_id": "HL-SPC-01",
                "severity": "major",
                "slide_index": idx,
                "title": title,
                "message": "Blank line between category header and first story",
            })

        paras = hl.get("paragraphs", [])
        expected_gaps = _expected_sprint_gaps(paras)
        actual_gaps = hl.get("blank_between_sprints", 0)
        if actual_gaps != expected_gaps:
            violations.append({
                "rule_id": "HL-SPC-03",
                "severity": "major",
                "slide_index": idx,
                "title": title,
                "message": f"Expected {expected_gaps} sprint gap(s), found {actual_gaps}",
            })

        clearance = slide.get("text_ka_clearance_in")
        if clearance is not None and clearance < MIN_TEXT_KA_CLEARANCE_IN:
            violations.append({
                "rule_id": "KA-OVERLAP-01",
                "severity": "critical",
                "slide_index": idx,
                "title": title,
                "message": (
                    f"Highlights text may overlap Key Activities "
                    f"(clearance {clearance} in < {MIN_TEXT_KA_CLEARANCE_IN} in)"
                ),
            })

        hl_ka_gap = slide.get("hl_ka_gap_in")
        if hl_ka_gap is not None and hl_ka_gap < HL_KA_MIN_BORDER_GAP_IN:
            violations.append({
                "rule_id": "KA-PLC-01",
                "severity": "major",
                "slide_index": idx,
                "title": title,
                "message": (
                    f"Highlights table bottom overlaps Key Activities "
                    f"(gap {hl_ka_gap} in < {HL_KA_MIN_BORDER_GAP_IN} in)"
                ),
            })
        if hl_ka_gap is not None and hl_ka_gap > HL_KA_MAX_BORDER_GAP_IN:
            clearance_ok = (
                clearance is not None and clearance >= MIN_TEXT_KA_CLEARANCE_IN
            )
            hl_bottom = hl.get("position_in", {}).get("bottom")
            text_bottom = slide.get("estimated_text_bottom_in")
            text_inside_hl = (
                text_bottom is not None
                and hl_bottom is not None
                and text_bottom <= hl_bottom + 0.05
            )
            if clearance_ok and text_inside_hl:
                violations.append({
                    "rule_id": "KA-PLC-02",
                    "severity": "major",
                    "slide_index": idx,
                    "title": title,
                    "message": (
                        f"Key Activities too far below Highlights "
                        f"(gap {hl_ka_gap} in > {HL_KA_MAX_BORDER_GAP_IN} in)"
                    ),
                })

        ka = slide.get("key_activities")
        ka_has_items = ka is not None and ka.get("item_count", 0) > 0
        if (
            slide.get("is_contd")
            and hl.get("filled_paragraph_count", 0) <= SPARSE_CONTD_MAX_FILLED
            and ka_has_items
            and slide.get("layout_type") == "hl_and_ka"
        ):
            violations.append({
                "rule_id": "CONT-SPARSE-01",
                "severity": "major",
                "slide_index": idx,
                "title": title,
                "message": "Sparse Highlights on (Contd...) slide with few bullets",
            })

        util = hl.get("effective_utilization_ratio", hl.get("utilization_ratio"))
        waste = slide.get("hl_waste_below_text_in")
        if (
            util is not None
            and util < UTILIZATION_THRESHOLD
            and waste is not None
            and waste > SPARSE_HL_MAX_WASTE_IN
            and not slide.get("is_contd")
        ):
            violations.append({
                "rule_id": "HL-SIZE-01",
                "severity": "major",
                "slide_index": idx,
                "title": title,
                "message": (
                    f"Highlights table oversized for sparse content "
                    f"({waste} in empty below text)"
                ),
            })

    ka = slide.get("key_activities")
    if ka:
        ka_pos = ka.get("position_in", {})
        ka_bottom = ka_pos.get("bottom")
        if ka_bottom is not None and ka_bottom > FOOTER_MAX_BOTTOM_IN:
            violations.append({
                "rule_id": "GEO-02",
                "severity": "critical",
                "slide_index": idx,
                "title": title,
                "message": (
                    f"Key Activities extends below footer safe zone "
                    f"({ka_bottom} in > {FOOTER_MAX_BOTTOM_IN} in)"
                ),
            })
        item_count = ka.get("item_count", 0)
        ka_util = ka.get("utilization_ratio")
        ka_waste = slide.get("ka_waste_below_text_in")
        if (
            item_count > 0
            and ka_util is not None
            and ka_util < UTILIZATION_THRESHOLD
            and ka_waste is not None
            and ka_waste > SPARSE_KA_MAX_WASTE_IN
        ):
            violations.append({
                "rule_id": "KA-SIZE-01",
                "severity": "major",
                "slide_index": idx,
                "title": title,
                "message": (
                    f"Key Activities table oversized for sparse content "
                    f"({ka_waste} in empty below items)"
                ),
            })

    if hl:
        hl_pos = hl.get("position_in", {})
        hl_bottom = hl_pos.get("bottom")
        if hl_bottom is not None:
            ka_on_slide = slide.get("key_activities") is not None
            hl_limit = (
                FOOTER_MAX_HL_DENSE_BOTTOM_IN
                if not ka_on_slide and hl_is_dense(hl)
                else FOOTER_MAX_BOTTOM_IN
            )
            if hl_bottom > hl_limit:
                violations.append({
                    "rule_id": "GEO-02",
                    "severity": "critical",
                    "slide_index": idx,
                    "title": title,
                    "message": (
                        f"Highlights extends below footer safe zone "
                        f"({hl_bottom} in > {hl_limit} in)"
                    ),
                })

    return violations


def detect_deck_violations(
    deck_data: dict[str, Any],
    *,
    content_titles: set[str] | None = None,
    scope_all_slides: bool = False,
) -> dict[str, Any]:
    """
    Detect violations across deck, including cross-slide HL-UTIL-01
    (main under-filled while HL contd exists for same service).

    When content_titles is set, only slides whose service title appears in
    ppt_content.json are in scope (excludes untouched G10X template placeholders).
    """
    slides = deck_data.get("slides", [])
    if content_titles is not None and not scope_all_slides:
        allowed = {t.strip().lower() for t in content_titles}

        def in_scope(title: str) -> bool:
            return _service_base_title(title).lower() in allowed

        slides = [s for s in slides if in_scope(s.get("title", ""))]

    by_service: dict[str, dict[str, Any]] = {}

    for slide in deck_data.get("slides", []):
        base = _service_base_title(slide.get("title", ""))
        bucket = by_service.setdefault(
            base, {"main": None, "contd_hl": [], "contd_ka_only": None}
        )
        if slide.get("is_contd"):
            if slide.get("layout_type") == "ka_only_contd":
                bucket["contd_ka_only"] = slide
            elif slide.get("highlights"):
                bucket["contd_hl"].append(slide)
        else:
            bucket["main"] = slide

    all_violations: list[dict[str, Any]] = []

    for slide in slides:
        all_violations.extend(detect_slide_violations(slide))

    for service, pair in by_service.items():
        main = pair.get("main")
        contd_hl = pair.get("contd_hl") or []
        contd_ka = pair.get("contd_ka_only")
        if not main:
            continue

        hl = main.get("highlights")
        if hl and contd_hl and not hl_is_dense(hl):
            para_util = hl.get("utilization_ratio")
            visual_lines = hl.get("visual_line_count")
            effective = hl.get("effective_utilization_ratio", para_util)
            all_violations.append({
                "rule_id": "HL-UTIL-01",
                "severity": "critical",
                "slide_index": main.get("slide_index"),
                "title": main.get("title"),
                "service_title": service,
                "message": (
                    f"Main slide under-filled ({effective:.0%} effective"
                    + (
                        f", {para_util:.0%} paragraphs / {visual_lines} visual lines"
                        if para_util is not None and visual_lines is not None
                        else ""
                    )
                    + f") but HL (Contd...) exists for {service}"
                ),
            })

        # KA-PLC-04: KA-only contd only when KA cannot fit below HL on the main slide.
        # Dense HL-filled main (Supplier) + KA on contd is valid; sparse main with room is not.
        if contd_ka and hl and main.get("key_activities") is None:
            if not _main_hl_is_dense(main) and _ka_would_fit_on_main(main):
                hl_pos = hl.get("position_in", {})
                hl_bottom = hl_pos.get("bottom")
                text_bottom = main.get("hl_text_bottom_for_fit_in") or main.get(
                    "estimated_text_bottom_in"
                )
                room_in = (
                    round(hl_bottom - text_bottom, 4)
                    if hl_bottom is not None and text_bottom is not None
                    else None
                )
                all_violations.append({
                    "rule_id": "KA-PLC-04",
                    "severity": "critical",
                    "slide_index": main.get("slide_index"),
                    "title": main.get("title"),
                    "service_title": service,
                    "message": (
                        "Key Activities moved to (Contd...) but main slide has room "
                        f"to fit HL + KA together"
                        + (f" ({room_in} in below HL text)" if room_in is not None else "")
                    ),
                })
            elif contd_hl and _main_hl_is_dense(main):
                # supplier_contd: dense HL main + overflow on HL contd — expected pattern.
                pass

    critical = [v for v in all_violations if v.get("severity") == "critical"]
    return {
        "violation_count": len(all_violations),
        "critical_count": len(critical),
        "violations": all_violations,
        "has_critical": bool(critical),
    }

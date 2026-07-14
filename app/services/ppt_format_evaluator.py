"""AI-powered PPT format evaluation against G10X rulebook using Azure OpenAI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.ppt_format_extractor import extract_deck
from app.services.title_generator import create_llm_client

RULEBOOK_PATH = Path(__file__).resolve().parents[1] / "constants" / "ppt_format_rulebook.json"

SYSTEM_PROMPT = """You are a G10X H-E-B WSR delivery-status PowerPoint format auditor.

You receive:
1. The official format rulebook (JSON), including layout_principles.
2. Extracted structural metrics from each slide in the deck under review.

CONTENT-AGNOSTIC RULE (mandatory):
- NEVER pass or fail a slide by comparing inch heights to a named reference slide (Cost, Supplier, Wentworth, etc.).
- Judge layout using content-relative metrics from layout_principles.metrics_the_ai_must_use only.

Your job:
- Evaluate EVERY slide titled "Delivery status – …" (main, contd, template placeholders).
- Score EACH slide 0-100 across: typography, bullet_hierarchy, spacing, layout_geometry, content_structure, space_utilization.
- deck_score = average of all delivery-status slide scores; deck_pass when >= threshold.

Layout principle audit checklist (use extracted metrics):
1. Dynamic sizing: sparse HL/KA shrink to text (HL-SIZE-01, KA-SIZE-01, CONT-SPARSE-01). White space at slide bottom is valid.
2. HL–KA spacing when both on slide: hl_ka_gap_in between -0.12 and 0.25 in; text_ka_clearance_in >= 0.15 in (KA-OVERLAP-01, KA-PLC-01, KA-PLC-02).
3. Footer boundary: highlights/key_activities position_in.bottom <= 6.29 in (GEO-02).
4. Continuation: apply contd_decision_tree — penalize HL-UTIL-01 (premature HL contd), KA-PLC-04 (KA-only contd when main has room for both HL+KA). Do NOT penalize KA-PLC-04 when main HL is dense/full (utilization >= 0.85) and KA cannot fit below HL on main (Supplier pattern).
5. No overlap: text must not intrude into KA; sections left-aligned.
6. Bullets: HL-P-04 critical — category headers Wingdings Ø level 7 only; stories lvl 1 dash.

Penalize heavily: category_bullet_violations (critical), stretched sparse boxes, HL–KA overlap, excessive HL–KA gap, footer overflow, premature contd.
Reward: fit-to-content sizing, correct contd splits, acceptable bottom white space.

Return ONLY valid JSON matching output_schema in rulebook evaluation_instructions. No markdown fences."""


def load_rulebook(path: Path | None = None) -> dict[str, Any]:
    p = path or RULEBOOK_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _build_user_prompt(rulebook: dict, deck_data: dict) -> str:
    # Trim paragraph text in deck data to keep token count reasonable
    compact = json.loads(json.dumps(deck_data))
    for slide in compact.get("slides", []):
        hl = slide.get("highlights")
        if hl and "paragraphs" in hl:
            for p in hl["paragraphs"]:
                if "text" in p and len(p["text"]) > 120:
                    p["text"] = p["text"][:120] + "…"
    return json.dumps(
        {
            "rulebook": rulebook,
            "layout_principles": rulebook.get("layout_principles", {}),
            "deck_under_review": compact,
            "task": (
                "Evaluate format compliance using layout_principles and content-relative metrics. "
                "Return JSON per output_schema."
            ),
        },
        ensure_ascii=False,
    )


def evaluate_deck_format(
    ppt_path: str | Path,
    rulebook_path: Path | None = None,
) -> dict[str, Any]:
    """
    Extract deck metrics and call Azure OpenAI for format scoring.
    Returns evaluation JSON with deck_score, deck_pass, per-slide scores.
    """
    rulebook = load_rulebook(rulebook_path)
    deck_data = extract_deck(ppt_path)

    if not deck_data["slides"]:
        return {
            "deck_score": 0,
            "deck_pass": False,
            "slides": [],
            "summary": "No delivery-status slides found in deck.",
            "critical_issues": ["No slides matching 'Delivery status' title pattern."],
        }

    client, model = create_llm_client()
    if client is None:
        raise RuntimeError(
            "Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env"
        )

    user_prompt = _build_user_prompt(rulebook, deck_data)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    result = json.loads(raw)

    # Attach extraction snapshot for traceability
    result["source_file"] = deck_data["file"]
    result["extracted_slide_count"] = deck_data["slide_count"]
    result["rulebook_version"] = rulebook.get("meta", {}).get("version", "unknown")

    return result


def format_evaluation_report(result: dict[str, Any]) -> str:
    """Human-readable evaluation summary."""
    lines = [
        f"Deck: {result.get('source_file', '?')}",
        f"Rulebook: v{result.get('rulebook_version', '?')}",
        f"Score: {result.get('deck_score', 0)}/100 — {'PASS' if result.get('deck_pass') else 'FAIL'}",
        "",
        result.get("summary", ""),
        "",
    ]
    if result.get("critical_issues"):
        lines.append("Critical issues:")
        for issue in result["critical_issues"]:
            lines.append(f"  - {issue}")
        lines.append("")

    for slide in result.get("slides", []):
        lines.append(f"Slide {slide.get('slide_index')}: {slide.get('title', '')[:50]}")
        lines.append(f"  Score: {slide.get('score', 0)}/100 — {'PASS' if slide.get('pass') else 'FAIL'}")
        cats = slide.get("category_scores", {})
        if cats:
            lines.append(
                "  Categories: "
                + ", ".join(f"{k}={v}" for k, v in cats.items())
            )
        for v in slide.get("violations", [])[:5]:
            lines.append(f"  [{v.get('severity', '?').upper()}] {v.get('rule_id')}: {v.get('message')}")
        lines.append("")

    return "\n".join(lines)

"""Generate short WSR slide titles from Jira summary/description via GPT-4o mini."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from openai import AzureOpenAI, OpenAI
from sqlalchemy.orm import Session

from app.config import get_settings, llm_configured
from app.constants.ppt_mapping import MAX_TITLE_LENGTH

if TYPE_CHECKING:
    from app.models.jira_story import JiraStory

SYSTEM_PROMPT = """You write one-line WSR slide bullets for H-E-B delivery status decks.
Output a single short action phrase (Validate, Implement, Add, Fix, Update, …) that tells a non-technical reader what was done.
Rules:
- Max 80 characters
- No Jira keys (e.g. LOC-1234)
- No pipe-separated prefixes like "FAM | MFR |"
- Plain sentence case, no quotes
Examples:
- Implement Warehouse List Page UI
- Validate tax exempt TIN validation on supplier form
- Add validation for warehouse number minimum length
- Fix status column display for offsite warehouses
"""

DESCRIPTION_MAX_CHARS = 500


def _strip_prefix(summary: str) -> str:
    """Remove common Jira pipe-prefix segments for fallback titles."""
    text = summary.strip()
    if "|" in text:
        parts = [p.strip() for p in text.split("|") if p.strip()]
        if len(parts) > 1:
            text = parts[-1]
    return text


def fallback_title(summary: str, description: str | None = None) -> str:
    """Derive a title without calling the API."""
    base = _strip_prefix(summary)
    if description and (len(base) <= 3 or base.isdigit()):
        first = description.strip().split(".")[0].strip()
        if len(first) > len(base):
            base = first
    base = re.sub(r"\s+", " ", base).strip()
    if len(base) > MAX_TITLE_LENGTH:
        base = base[: MAX_TITLE_LENGTH - 3].rsplit(" ", 1)[0] + "..."
    return base or "Story update"


def _clean_model_output(text: str) -> str:
    cleaned = text.strip().strip("\"'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if len(cleaned) > MAX_TITLE_LENGTH:
        cleaned = cleaned[: MAX_TITLE_LENGTH - 3].rsplit(" ", 1)[0] + "..."
    return cleaned


def create_llm_client() -> tuple[OpenAI | AzureOpenAI, str] | tuple[None, None]:
    """
    Return (client, model_or_deployment_name).
    Prefers Azure OpenAI when AZURE_OPENAI_* vars are set.
    """
    settings = get_settings()

    if settings.azure_openai_endpoint and settings.azure_openai_api_key:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint.rstrip("/"),
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        deployment = settings.azure_openai_model or "gpt-4o-mini"
        return client, deployment

    if settings.openai_api_key:
        return OpenAI(api_key=settings.openai_api_key), "gpt-4o-mini"

    return None, None


def generate_title(
    client: OpenAI | AzureOpenAI,
    *,
    jira_key: str,
    summary: str,
    description: str | None,
    model: str,
) -> str:
    """Call GPT-4o mini for one story title; fallback on failure."""
    desc = (description or "")[:DESCRIPTION_MAX_CHARS]
    user_msg = f"jira_key: {jira_key}\nsummary: {summary}\ndescription: {desc}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=60,
            temperature=0.3,
        )
        content = response.choices[0].message.content
        if content:
            return _clean_model_output(content)
    except Exception as exc:
        print(f"  Warning: GPT title failed for {jira_key}: {exc}")

    return fallback_title(summary, description)


def ensure_story_titles(
    stories: list[JiraStory],
    *,
    save: bool = False,
    db: Session | None = None,
    rate_limit_s: float = 0.2,
    regenerate: bool = False,
) -> tuple[int, int]:
    """
    Fill missing title on each story (in memory and optionally DB).
    Returns (generated_count, reused_count).
    """
    if not llm_configured():
        print(
            "Warning: No LLM credentials — set AZURE_OPENAI_* or OPENAI_API_KEY "
            "in .env; using fallback titles only."
        )

    client, model = create_llm_client()
    generated = 0
    reused = 0

    for story in stories:
        if story.title and story.title.strip() and not regenerate:
            reused += 1
            continue

        if client and model:
            story.title = generate_title(
                client,
                jira_key=story.jira_key,
                summary=story.summary,
                description=story.description,
                model=model,
            )
            generated += 1
            time.sleep(rate_limit_s)
        else:
            story.title = fallback_title(story.summary, story.description)
            generated += 1

        if save and db is not None:
            row = db.get(type(story), story.jira_key)
            if row:
                row.title = story.title

    return generated, reused

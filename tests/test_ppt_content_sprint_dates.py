"""Sprint dates on PPT content must mirror sprints table — never WSR-clipped."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.ppt_content_builder import build_slide_chunks
from app.services.sprint_display import sprint_dates_from_section


def _story(
    *,
    jira_key: str,
    sprint_name: str,
    sprint_start: date,
    sprint_end: date,
    sprint_status: str = "Ended",
    project_key: str = "COST",
    project_name: str = "Cost Core Service",
):
    sprint = SimpleNamespace(
        sprint_name=sprint_name,
        sprint_start_date=sprint_start,
        sprint_end_date=sprint_end,
        sprint_status=sprint_status,
    )
    project = SimpleNamespace(project_key=project_key, project_name=project_name)
    return SimpleNamespace(
        project_id=1,
        sprint_id=5,
        jira_key=jira_key,
        project=project,
        sprint=sprint,
        title="Example story",
        summary="Example story",
        status="Done",
    )


def test_build_slide_chunks_uses_full_db_dates_not_wsr_end():
    """Sprint ending after WSR end must still show the DB end date."""
    story = _story(
        jira_key="COST-1",
        sprint_name="Q3.01 FY26 Atlas",
        sprint_start=date(2026, 6, 4),
        sprint_end=date(2026, 6, 17),
    )
    chunk = build_slide_chunks([story])[0]
    assert chunk["sprint_start_date"] == "2026-06-04"
    assert chunk["sprint_end_date"] == "2026-06-17"
    assert chunk["sprint_dates"] == "Jun 04 – Jun 17"


def test_build_slide_chunks_multiple_sprints_each_keep_db_dates():
    atlas = _story(
        jira_key="COST-1",
        sprint_name="Q3.01 FY26 Atlas",
        sprint_start=date(2026, 6, 4),
        sprint_end=date(2026, 6, 17),
    )
    orion = _story(
        jira_key="COST-2",
        sprint_name="Q3.02 FY26 Orion",
        sprint_start=date(2026, 6, 18),
        sprint_end=date(2026, 7, 1),
        sprint_status="In-progress",
    )
    orion.sprint_id = 4
    orion.project_id = 1

    chunks = build_slide_chunks([atlas, orion])
    by_name = {c["sprint_name"]: c for c in chunks}
    assert by_name["Q3.01 FY26 Atlas"]["sprint_dates"] == "Jun 04 – Jun 17"
    assert by_name["Q3.02 FY26 Orion"]["sprint_dates"] == "Jun 18 – Jul 01"


def test_sprint_dates_from_section_prefers_iso_over_stale_string():
    section = {
        "sprint_name": "Q3.01 FY26 Atlas",
        "sprint_start_date": "2026-06-04",
        "sprint_end_date": "2026-06-17",
        "sprint_dates": "Jun 04 – Jun 12",
    }
    assert sprint_dates_from_section(section) == "Jun 04 – Jun 17"

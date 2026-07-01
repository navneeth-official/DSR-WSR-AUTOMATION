from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.jira_story import JiraStory


class JiraStoryRepository:
    """Data access layer for jira_stories table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, jira_key: str) -> JiraStory | None:
        return self.db.get(JiraStory, jira_key)

    def get_all(self) -> list[JiraStory]:
        stmt = select(JiraStory).order_by(JiraStory.created_date.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_assignee(self, assignee: str) -> list[JiraStory]:
        stmt = (
            select(JiraStory)
            .where(JiraStory.assignee == assignee)
            .order_by(JiraStory.created_date.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_sprint(self, sprint_name: str) -> list[JiraStory]:
        stmt = (
            select(JiraStory)
            .where(JiraStory.sprint_name == sprint_name)
            .order_by(JiraStory.jira_key)
        )
        return list(self.db.scalars(stmt).all())

    def upsert(
        self,
        *,
        jira_key: str,
        project_name: str,
        summary: str,
        status: str,
        project_key: str | None = None,
        sprint_name: str | None = None,
        sprint_start_date: date | None = None,
        sprint_end_date: date | None = None,
        description: str | None = None,
        issue_type: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        reporter: str | None = None,
        story_points: Decimal | float | int | None = None,
        created_date: date | None = None,
        updated_date: date | None = None,
        resolved_date: date | None = None,
        snapshot_date: date | None = None,
        title: str | None = None,
        completion: Decimal | float | int | None = None,
    ) -> JiraStory:
        """Insert a new story or update an existing one by jira_key."""
        story = self.get_by_key(jira_key)

        if story is None:
            story = JiraStory(
                jira_key=jira_key,
                project_key=project_key,
                project_name=project_name,
                sprint_name=sprint_name,
                sprint_start_date=sprint_start_date,
                sprint_end_date=sprint_end_date,
                summary=summary,
                description=description,
                issue_type=issue_type,
                priority=priority,
                assignee=assignee,
                reporter=reporter,
                status=status,
                story_points=_to_decimal(story_points),
                created_date=created_date,
                updated_date=updated_date,
                resolved_date=resolved_date,
                snapshot_date=snapshot_date,
                title=title,
                completion=_to_decimal(completion),
            )
            self.db.add(story)
        else:
            story.project_key = project_key
            story.project_name = project_name
            story.sprint_name = sprint_name
            story.sprint_start_date = sprint_start_date
            story.sprint_end_date = sprint_end_date
            story.summary = summary
            story.description = description
            story.issue_type = issue_type
            story.priority = priority
            story.assignee = assignee
            story.reporter = reporter
            story.status = status
            story.story_points = _to_decimal(story_points)
            story.created_date = created_date
            story.updated_date = updated_date
            story.resolved_date = resolved_date
            story.snapshot_date = snapshot_date
            if title is not None:
                story.title = title
            story.completion = _to_decimal(completion)

        self.db.commit()
        self.db.refresh(story)
        return story

    def delete(self, jira_key: str) -> bool:
        story = self.get_by_key(jira_key)
        if story is None:
            return False
        self.db.delete(story)
        self.db.commit()
        return True


def _to_decimal(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))

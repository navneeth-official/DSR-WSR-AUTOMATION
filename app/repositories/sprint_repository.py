from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sprint import Sprint


class SprintRepository:
    """Data access layer for sprints table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, sprint_id: int) -> Sprint | None:
        return self.db.get(Sprint, sprint_id)

    def get_by_name(self, sprint_name: str) -> Sprint | None:
        stmt = select(Sprint).where(Sprint.sprint_name == sprint_name.strip())
        return self.db.scalars(stmt).first()

    def get_all(self) -> list[Sprint]:
        stmt = select(Sprint).order_by(Sprint.sprint_name)
        return list(self.db.scalars(stmt).all())

    def get_or_create(
        self,
        *,
        sprint_name: str | None,
        sprint_start_date: date | None = None,
        sprint_end_date: date | None = None,
    ) -> Sprint | None:
        """Find sprint by name or insert a new row with the next sprint_id."""
        if not sprint_name or not sprint_name.strip():
            return None

        name = sprint_name.strip()
        sprint = self.get_by_name(name)

        if sprint is None:
            sprint = Sprint(
                sprint_name=name,
                sprint_status="inprogress",
                sprint_start_date=sprint_start_date,
                sprint_end_date=sprint_end_date,
            )
            self.db.add(sprint)
            self.db.flush()
        else:
            if sprint_start_date and sprint.sprint_start_date is None:
                sprint.sprint_start_date = sprint_start_date
            if sprint_end_date and sprint.sprint_end_date is None:
                sprint.sprint_end_date = sprint_end_date
            self.db.flush()

        return sprint

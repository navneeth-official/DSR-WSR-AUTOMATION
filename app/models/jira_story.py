from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JiraStory(Base):
    """Stores Jira story details synced from Rovo AI for DSR/WSR report generation."""

    __tablename__ = "jira_stories"

    jira_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    project_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sprint_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sprint_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sprint_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reporter: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    story_points: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    created_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="AI-generated title from summary and description (filled later)",
    )
    completion: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Story completion percentage (0-100)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<JiraStory(jira_key={self.jira_key!r}, status={self.status!r})>"

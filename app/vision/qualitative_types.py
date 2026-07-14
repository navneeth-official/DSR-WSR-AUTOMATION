"""Typed results for qualitative vision layout review."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.constants.vision_qualitative_reviewer_prompt import (
    ALLOWED_QUALITATIVE_CATEGORIES,
    SLIDE_STATUS_NEEDS_REVIEW,
    SLIDE_STATUS_OK,
)


class QualitativeCategory(str, Enum):
    OVERLAP = "overlap"
    CLIPPED_TEXT = "clipped_text"
    EXCESSIVE_WHITESPACE = "excessive_whitespace"
    POOR_VISUAL_BALANCE = "poor_visual_balance"
    UNREADABLE_LAYOUT = "unreadable_layout"
    NO_ISSUE = "no_issue"

    @classmethod
    def from_raw(cls, value: str | None) -> QualitativeCategory:
        if value in ALLOWED_QUALITATIVE_CATEGORIES:
            return cls(value)  # type: ignore[arg-type]
        return cls.NO_ISSUE


class ReviewStatus(str, Enum):
    OK = SLIDE_STATUS_OK
    NEEDS_REVIEW = SLIDE_STATUS_NEEDS_REVIEW


@dataclass(frozen=True)
class QualitativeIssue:
    category: QualitativeCategory
    severity: str
    confidence: float | None
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity,
            "confidence": self.confidence,
            "description": self.description,
        }


@dataclass(frozen=True)
class QualitativeSlideReview:
    slide_number: int | None
    status: ReviewStatus
    overall_quality: str
    issues: tuple[QualitativeIssue, ...] = ()

    @property
    def passes(self) -> bool:
        if self.status == ReviewStatus.OK:
            return True
        return not any(
            i.category != QualitativeCategory.NO_ISSUE
            and i.severity in ("high", "medium")
            for i in self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_number": self.slide_number,
            "status": self.status.value,
            "pass": self.passes,
            "overall_quality": self.overall_quality,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class QualitativeReviewReport:
    deck_pass: bool
    slides: list[QualitativeSlideReview] = field(default_factory=list)
    summary: str = ""
    evaluator: str = "qualitative_vision_reviewer"
    vision_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "deck_pass": self.deck_pass,
            "slides": [s.to_dict() for s in self.slides],
            "summary": self.summary,
            "evaluator": self.evaluator,
            "vision_model": self.vision_model,
        }

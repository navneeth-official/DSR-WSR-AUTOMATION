"""Pipeline adapter for qualitative vision review."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline.types import RenderBatch, RenderedSlide
from app.vision.qualitative_client import QualitativeVisionClient
from app.vision.qualitative_types import QualitativeReviewReport, QualitativeSlideReview


class QualitativeVisionReviewer:
    """Reviews rendered slides for visual quality (no pixel measurements)."""

    def __init__(self, *, client: QualitativeVisionClient | None = None) -> None:
        self._client = client or QualitativeVisionClient()

    def evaluate(self, render_batch: RenderBatch) -> QualitativeReviewReport:
        if not render_batch.slides:
            return QualitativeReviewReport(
                deck_pass=True,
                summary="No slides to review.",
                vision_model=self._client.model_name,
            )

        reexport_dir: list[Path | None] = [None]
        slide_reviews: list[QualitativeSlideReview] = []

        for slide in render_batch.slides:
            image_path = self._resolve_slide_image(slide, render_batch, reexport_dir)
            review = self._client.review_slide(
                image_path,
                slide_number=slide.slide_index,
                title=slide.title,
            )
            slide_reviews.append(review)

        deck_pass = bool(slide_reviews) and all(s.passes for s in slide_reviews)
        needs_review = sum(1 for s in slide_reviews if not s.passes)

        return QualitativeReviewReport(
            deck_pass=deck_pass,
            slides=slide_reviews,
            summary=(
                f"Qualitative review: {len(slide_reviews)} slide(s); "
                f"{needs_review} need review."
            ),
            vision_model=self._client.model_name,
        )

    def passes(self, report: QualitativeReviewReport) -> bool:
        return report.deck_pass

    def _resolve_slide_image(
        self,
        slide: RenderedSlide,
        render_batch: RenderBatch,
        reexport_dir: list[Path | None],
    ) -> Path:
        if slide.image_path.is_file():
            return slide.image_path.resolve()

        from app.services.ppt_slide_images import export_slides_to_png

        if reexport_dir[0] is None:
            reexport_dir[0] = Path(
                tempfile.mkdtemp(
                    prefix="ppt_qualitative_review_",
                    dir=render_batch.ppt_path.parent,
                )
            )
        exported = export_slides_to_png(
            render_batch.ppt_path,
            reexport_dir[0],
            slide_indices=[slide.slide_index],
        )
        if not exported:
            raise FileNotFoundError(
                f"Could not export slide {slide.slide_index} from {render_batch.ppt_path}"
            )
        return Path(exported[0]["image_path"]).resolve()

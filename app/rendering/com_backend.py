"""PowerPoint COM backend for pixel-accurate slide export (Windows)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence


class ComSlideRendererBackend:
    """
    Renders slides through the installed PowerPoint application.

    Uses ``Slide.Export`` so fonts, spacing, and shapes match the live deck.
    """

    def render_slides(
        self,
        ppt_path: Path,
        output_dir: Path,
        *,
        slide_indices: Sequence[int] | None = None,
        width_px: int = 1920,
    ) -> list[Path]:
        ppt_path = ppt_path.resolve()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            import win32com.client  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "win32com is required for PowerPoint rendering. "
                "Install with: pip install pywin32"
            ) from exc

        app = win32com.client.Dispatch("PowerPoint.Application")
        _set_powerpoint_visible(app, visible=False)
        presentation = app.Presentations.Open(str(ppt_path), WithWindow=False)
        exported: list[Path] = []

        try:
            slide_count = int(presentation.Slides.Count)
            indices = (
                list(slide_indices)
                if slide_indices is not None
                else list(range(1, slide_count + 1))
            )

            slide_width = float(presentation.PageSetup.SlideWidth)
            slide_height = float(presentation.PageSetup.SlideHeight)
            if slide_width <= 0:
                slide_width = 720.0
            height_px = max(1, int(width_px * slide_height / slide_width))

            for idx in indices:
                if idx < 1 or idx > slide_count:
                    continue
                slide = presentation.Slides(idx)
                out_path = (output_dir / f"slide_{idx:02d}.png").resolve()
                slide.Export(str(out_path), "PNG", width_px, height_px)
                exported.append(out_path)
        finally:
            presentation.Close()
            app.Quit()

        return exported


def _set_powerpoint_visible(app, *, visible: bool) -> None:
    """
    Set PowerPoint visibility; some installs forbid hiding the app window.

    Falls back to visible=True when ``Visible = False`` is rejected by COM.
    """
    try:
        app.Visible = -1 if visible else 0  # msoTrue / msoFalse
    except Exception:
        try:
            app.Visible = 1 if visible else 0
        except Exception:
            app.Visible = 1

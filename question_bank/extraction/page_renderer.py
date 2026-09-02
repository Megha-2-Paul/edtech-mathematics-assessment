"""Render PDF page regions to high-resolution images."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import fitz


def render_region(
    page: fitz.Page,
    bbox: tuple[float, float, float, float],
    output_path: str | Path,
    dpi: int = 180,
) -> Path:
    """Render ``bbox`` from a page to PNG at the requested DPI."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    rect = fitz.Rect(bbox) & page.rect
    if rect.is_empty or rect.width <= 0 or rect.height <= 0:
        raise ValueError("Cannot render an empty or invalid PDF region")

    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    pixmap.save(str(output))
    return output


def render_page(
    page: fitz.Page,
    output_path: str | Path,
    dpi: int = 180,
) -> Path:
    """Render an entire PDF page to PNG."""
    return render_region(page, page.rect, output_path, dpi=dpi)

"""Detect visual assets inside a question region.

V1 records source image/drawing bounding boxes. It does not interpret the
assets; the original PDF crop remains the ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import fitz


@dataclass(frozen=True)
class VisualAsset:
    asset_type: str
    bbox: tuple[float, float, float, float]
    page: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _intersection(a: fitz.Rect, b: fitz.Rect) -> fitz.Rect:
    return a & b


def detect_visual_assets(
    page: fitz.Page,
    page_number: int,
    region: tuple[float, float, float, float],
) -> list[VisualAsset]:
    """Return image/drawing regions that overlap the question region."""
    region_rect = fitz.Rect(region) & page.rect
    assets: list[VisualAsset] = []

    for image in page.get_images(full=True):
        xref = image[0]
        for rect in page.get_image_rects(xref):
            overlap = _intersection(rect, region_rect)
            if overlap.get_area() > 0:
                assets.append(
                    VisualAsset("image", tuple(overlap), page_number, f"xref:{xref}")
                )

    # Drawings are useful signals for vector diagrams, graphs and table lines.
    # Keep their individual bounding boxes; interpretation happens later.
    try:
        drawings = page.get_drawings()
    except (AttributeError, RuntimeError):
        drawings = []

    for drawing in drawings:
        rect = fitz.Rect(drawing.get("rect", (0, 0, 0, 0)))
        overlap = _intersection(rect, region_rect)
        if overlap.get_area() > 0:
            assets.append(
                VisualAsset("drawing", tuple(overlap), page_number, "vector")
            )

    return assets

"""Extraction review package adapter.

The original MVP implementation remains in the sibling ``review_app.py`` module.
This package adapter keeps that implementation intact while allowing additive
review features, such as explicit OR-question splitting, to register cleanly.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_LEGACY_PATH = Path(__file__).resolve().parents[1] / "review_app.py"
_SPEC = importlib.util.spec_from_file_location("question_bank.extraction._legacy_review_app", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load legacy extraction review module: {_LEGACY_PATH}")

_legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_legacy)

# Re-export the legacy module's implementation so existing imports keep working.
for _name in dir(_legacy):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_legacy, _name)

from question_bank.extraction.or_question_routes import register_or_question_review  # noqa: E402

_legacy_register = register_extraction_review


def register_extraction_review(app):
    """Register the original review UI plus the OR-question review route."""
    _legacy_register(app)
    register_or_question_review(app)

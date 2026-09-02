"""Contracts shared by reusable question-bank document agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PageDecision:
    page: int
    role: str
    routing: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    document_type: str
    confidence: float
    pages: list[PageDecision]
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentAgent(Protocol):
    """Interface implemented by specialized PDF document agents."""

    name: str
    document_type: str

    def analyze(self, file_path: str) -> AgentResult:
        ...

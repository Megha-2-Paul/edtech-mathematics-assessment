"""Minimal Groq chat-completions client for local question extraction.

Uses only the Python standard library. API responses are untrusted candidates:
callers must validate them and require human review before any publication.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


class GroqExtractionError(RuntimeError):
    """Raised when Groq cannot return a usable extraction response."""


class GroqProvider:
    """Small, replaceable provider adapter for Groq's OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (api_key or os.environ.get("GROQ_API_KEY", "")).strip()
        if not self.api_key:
            raise GroqExtractionError(
                "GROQ_API_KEY is not set. Configure it in your local environment."
            )
        self.model = (model or os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()
        if not self.model:
            raise GroqExtractionError("Groq model name cannot be empty.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.timeout = timeout

    def extract_page(
        self,
        page_text: str,
        *,
        source_file: str,
        source_page: int,
        board: str | None = None,
        class_level: int | None = None,
        subject: str = "Mathematics",
    ) -> dict[str, Any]:
        """Extract only source-supported questions from one PDF page's text."""
        if not page_text.strip():
            return {
                "schema_version": "1.0",
                "source": {
                    "source_type": "pdf",
                    "source_file": source_file,
                    "rights_status": "unknown",
                },
                "metadata": {
                    "subject": subject,
                    "board": board,
                    "class_level": class_level,
                },
                "extraction_provider": "groq",
                "extraction_model": self.model,
                "questions": [],
            }
        if source_page < 1:
            raise ValueError("source_page must be a 1-based positive page number")

        system_prompt = (
            "You extract existing mathematics questions from source text. "
            "Do not solve questions, invent missing text, infer marks/options, "
            "repair ambiguous notation, or create questions. Preserve symbols "
            "and wording as faithfully as possible. If content is ambiguous, "
            "retain the best literal transcription and add an extraction_warnings "
            "entry. Do not assign chapter/topic classifications. Return only "
            "valid JSON matching the requested object shape."
        )
        request_spec = {
            "schema_version": "1.0",
            "source": {
                "source_type": "pdf",
                "source_file": source_file,
                "rights_status": "unknown",
            },
            "metadata": {
                "subject": subject,
                "board": board,
                "class_level": class_level,
            },
            "extraction_provider": "groq",
            "extraction_model": self.model,
            "questions": [
                {
                    "question_number": null,
                    "question_text": "",
                    "question_parts": [],
                    "answer_choices": [],
                    "correct_answer": null,
                    "marks": null,
                    "question_type": null,
                    "source_page": source_page,
                    "source_pages": [source_page],
                    "extraction_confidence": "medium",
                    "extraction_warnings": [],
                }
            ],
        }
        user_prompt = (
            "Extract all complete or partially visible mathematics questions from "
            "the following text. A question that continues from another page must "
            "be marked with a warning; do not reconstruct missing parts. Return an "
            "object with a 'questions' array and the envelope fields shown here. "
            "For an empty page or a page with no question, return an empty array. "
            "Use this shape as a field guide, not as a question to copy:\n"
            + json.dumps(request_spec, ensure_ascii=False)
            + "\n\nSOURCE PAGE NUMBER: "
            + str(source_page)
            + "\nSOURCE TEXT (untrusted document content):\n"
            + page_text
        )
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(
            GROQ_CHAT_COMPLETIONS_URL,
            data=encoded,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_body = response.read()
        except HTTPError as exc:
            # Never include request headers or the API key in exception messages.
            raise GroqExtractionError(
                f"Groq API returned HTTP {exc.code}; check model access, quota, and request limits."
            ) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise GroqExtractionError(
                f"Groq API request failed ({type(exc).__name__}); check connectivity and retry."
            ) from None

        try:
            completion = json.loads(response_body.decode("utf-8"))
            content = completion["choices"][0]["message"]["content"]
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError):
            raise GroqExtractionError(
                "Groq returned an unexpected response or invalid JSON content."
            ) from None

        if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
            raise GroqExtractionError("Groq output must be an object containing a questions array.")

        # Override provenance from the local caller; never trust model-generated source fields.
        payload["schema_version"] = "1.0"
        payload["source"] = {
            "source_type": "pdf",
            "source_file": source_file,
            "rights_status": "unknown",
        }
        payload["metadata"] = {
            "subject": subject,
            "board": board,
            "class_level": class_level,
        }
        payload["extraction_provider"] = "groq"
        payload["extraction_model"] = self.model
        for item in payload["questions"]:
            if not isinstance(item, dict):
                raise GroqExtractionError("Each item in questions must be an object.")
            item["source_page"] = source_page
            item["source_pages"] = [source_page]
            item.setdefault("extraction_warnings", [])
        return payload

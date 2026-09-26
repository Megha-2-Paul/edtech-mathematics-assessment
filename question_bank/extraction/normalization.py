"""Deterministic normalization for external AI question-bank JSON.

Only transformations that can be justified from the supplied record are applied.
Ambiguous curriculum labels remain unchanged so the resolver can require review.
"""

import re
from typing import Any


QUESTION_TYPE_ALIASES = {
    "mcq": "mcq",
    "multiple_choice": "mcq",
    "multiple-choice": "mcq",
    "assertion_reason": "mcq",
    "assertion-reason": "mcq",
    "assertionreason": "mcq",
    "vsaq": "vsaq",
    "very_short": "vsaq",
    "very-short": "vsaq",
    "short": "saq",
    "short_answer": "saq",
    "short-answer": "saq",
    "saq": "saq",
    "long": "laq",
    "long_answer": "laq",
    "long-answer": "laq",
    "laq": "laq",
}

# These aliases are intentionally narrow. They resolve the chapter from the
# topic supplied by the same question; they do not infer a chapter from a
# broad unit name alone.
TOPIC_TO_CANONICAL_CHAPTER = {
    "goods and services tax (gst)": "GST",
    "gst": "GST",
    "gst - discount": "GST",
    "banking - recurring deposit accounts": "Banking",
    "banking - recurring deposits": "Banking",
    "shares and dividends": "Shares and Dividends",
    "quadratic equations - nature of roots": "Quadratic Equations",
    "quadratic equations - solving using formula": "Quadratic Equations",
    "quadratic equations - word problems (mensuration application)": "Quadratic Equations",
    "ratio and proportion": "Ratio and Proportion",
    "ratio and proportion - properties of proportion": "Ratio and Proportion",
    "factorisation of polynomials (remainder & factor theorem)": "Factorisation of Polynomials",
    "matrices": "Matrices",
    "geometric progression": "Geometric Progressions",
    "arithmetic progression": "Arithmetic Progressions",
    "linear inequations": "Linear Inequations",
    "equation of a line": "Equation of a Straight Line",
    "reflection (transformation geometry)": "Reflection",
    "circles - tangent properties": "Circles",
    "circles - tangent properties / proofs": "Circles",
    "circles - angle properties": "Circles",
    "similarity of triangles / basic proportionality theorem": "Similarity",
    "trigonometric identities": "Trigonometric Identities",
    "heights and distances": "Heights and Distances",
    "measures of central tendency - median": "Statistics",
    "mean of grouped data": "Statistics",
    "ogive - median, quartiles/percentile-type reading": "Statistics",
    "histogram - mode": "Statistics",
    "mean, median, mode": "Statistics",
    "simple probability": "Probability",
    "volume of cone": "Surface Areas and Volumes",
    "volume of solids (cone, sphere, cylinder)": "Surface Areas and Volumes",
    "volume of combined solids": "Surface Areas and Volumes",
}

def normalize_question_type(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    original = str(value).strip()
    key = re.sub(r"\s+", "_", original.casefold())
    return QUESTION_TYPE_ALIASES.get(key), original


def normalize_chapter(chapter: Any, topic: Any) -> tuple[Any, dict[str, Any]]:
    original = chapter
    if not isinstance(chapter, str) or not chapter.strip():
        return chapter, {"status": "UNRESOLVED", "reason": "missing_chapter"}

    chapter_clean = re.sub(r"\s+", " ", chapter.strip())
    topic_clean = re.sub(r"\s+", " ", str(topic or "").strip()).casefold()

    # Already canonical or a direct canonical-equivalent topic.
    direct = TOPIC_TO_CANONICAL_CHAPTER.get(topic_clean)
    broad = chapter_clean.casefold() in {
        "commercial mathematics", "algebra", "coordinate geometry",
        "geometry", "mensuration", "trigonometry", "statistics", "probability",
    }
    if broad and direct:
        return direct, {
            "status": "NORMALIZED",
            "reason": "topic_based_broad_chapter_normalization",
            "original_chapter": original,
        }

    # A topic-specific chapter label can be normalized even when the chapter
    # field is already more specific.
    if direct and (
        chapter_clean.casefold() == topic_clean
        or chapter_clean.casefold() in {"commercial mathematics", "algebra", "geometry", "mensuration", "trigonometry", "statistics", "probability", "coordinate geometry"}
    ):
        return direct, {
            "status": "NORMALIZED",
            "reason": "topic_based_chapter_normalization",
            "original_chapter": original,
        }

    return chapter, {
        "status": "UNCHANGED",
        "reason": "no_safe_deterministic_normalization",
        "original_chapter": original,
    }


def _answer_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.match(r"^(?:option\s*)?\(?([A-Za-z])\)?(?:\.|\)|:|-)?\s*$", text, re.I)
    return match.group(1).upper() if match else None


def _comparison_text(value: Any) -> str:
    text = str(value).strip().casefold()
    text = re.sub(r"^(?:option\s*)?\(?[a-z]\)?(?:\.|\)|:|-)?\s*", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace(",", "")
    return text


def normalize_mcq_answer(answer: Any, choices: list[dict[str, str]]) -> tuple[str | None, str]:
    if answer is None:
        return None, "missing_answer"

    original = str(answer).strip()
    label = _answer_key(original)
    if label and any(c.get("label", "").upper() == label for c in choices):
        return label, "explicit_option_label"

    target = _comparison_text(original)
    matches = [
        c["label"] for c in choices
        if _comparison_text(c.get("text", "")) == target
    ]
    if len(matches) == 1:
        return matches[0], "answer_text_matched_to_option"

    return original, "unresolved_mcq_answer"

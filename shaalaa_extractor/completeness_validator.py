import re
from typing import Any, Dict, List


INTENTIONAL_ENDINGS = re.compile(
    r"(?:______\.?|[:.]|is:|are:|following\W*$)", re.I
)
TRUNCATED_ENDINGS = re.compile(
    r"(?:find the value of|find the|value of|given,?|consisting of|"
    r"equal to|is|are|and|or|by)\s*$",
    re.I,
)
OPTION_TEXT = re.compile(
    r"^(?:\(?[a-d]\)[.)]?\s+|[a-d][.)]\s+|both\s+(?:a|the)\s+.+\s+(?:true|false))",
    re.I,
)


def _question_text(question: Dict[str, Any]) -> str:
    return " ".join(
        str(block.get("value", ""))
        for block in question.get("content", [])
        if block.get("type") == "text"
    ).strip()


def validate_completeness(record: Dict[str, Any]) -> Dict[str, Any]:
    warnings: List[Dict[str, str]] = []

    def inspect(question: Dict[str, Any]) -> None:
        text = _question_text(question)
        number = str(question.get("question_number", ""))
        if not text and not question.get("subquestions"):
            warnings.append({"question": number, "code": "QUESTION_CONTENT_MISSING",
                             "message": "No question stem remains"})
        elif TRUNCATED_ENDINGS.search(text) and not INTENTIONAL_ENDINGS.search(text):
            warnings.append({"question": number, "code": "QUESTION_STEM_POSSIBLY_TRUNCATED",
                             "message": "Stem ends at a likely incomplete fragment"})
        elif OPTION_TEXT.search(text):
            warnings.append({"question": number, "code": "MCQ_OPTION_REMOVAL_MAY_HAVE_TRUNCATED_STEM",
                             "message": "Question text resembles an answer option"})
        else:
            warnings.append({"question": number, "code": "QUESTION_STEM_VALID",
                             "message": "A non-empty question stem remains"})

        for block in question.get("content", []):
            if block.get("type") in {"image", "table"}:
                continue
            if block.get("type") == "math" and not block.get("value"):
                warnings.append({"question": number, "code": "REQUIRED_MATH_MISSING",
                                 "message": "Empty mathematical block"})
        for subquestion in question.get("subquestions", []):
            inspect(subquestion)

    for question in record.get("questions", []):
        inspect(question)
    return {"valid": True, "warnings": warnings}

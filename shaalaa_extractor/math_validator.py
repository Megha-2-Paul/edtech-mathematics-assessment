import re
from typing import Any, Dict, List


SUSPICIOUS_SPACES = re.compile(r"\d\s+\d|[A-Za-z]\s+\d")
HTML_ARTIFACT = re.compile(r"<(?:mjx|html|script|style)\b", re.I)
SOLUTION_TEXT = re.compile(r"\b(?:view solution|concept:|chapter:)\b", re.I)


def validate_mathematics(record: Dict[str, Any]) -> Dict[str, Any]:
    warnings: List[Dict[str, str]] = []

    def inspect(question: Dict[str, Any]) -> None:
        for block in question.get("content", []):
            value = str(block.get("value", ""))
            metadata = block.get("metadata", {})
            if block.get("type") == "math":
                if not metadata.get("source_html"):
                    warnings.append({"question": question["question_number"],
                                     "issue": "Structured mathematical block has no source HTML"})
                if metadata.get("accessibility") and metadata["accessibility"] in value:
                    warnings.append({"question": question["question_number"],
                                     "issue": "Accessibility text may be leaking into visible mathematics"})
                if metadata.get("format") == "MathJax/semantic-DOM" and not (
                    metadata.get("semantic_structure") or metadata.get("accessibility")
                ):
                    warnings.append({"question": question["question_number"],
                                     "issue": "MathJax block lacks semantic structure and accessibility metadata"})
            if block.get("type") == "text":
                if SUSPICIOUS_SPACES.search(value):
                    warnings.append({"question": question["question_number"],
                                     "issue": "Suspicious spacing may flatten a fraction or exponent"})
                if HTML_ARTIFACT.search(value):
                    warnings.append({"question": question["question_number"],
                                     "issue": "HTML or MathJax artifact leaked into text"})
                if SOLUTION_TEXT.search(value):
                    warnings.append({"question": question["question_number"],
                                     "issue": "Solution or metadata text leaked into question"})
                if value.count("(") != value.count(")") or value.count("[") != value.count("]"):
                    warnings.append({"question": question["question_number"],
                                     "issue": "Unbalanced mathematical delimiters"})
            if block.get("type") == "math" and not value.strip():
                warnings.append({"question": question["question_number"],
                                 "issue": "Empty mathematical block"})
        for subquestion in question.get("subquestions", []):
            inspect(subquestion)

    for question in record.get("questions", []):
        inspect(question)
    return {"valid": not warnings, "warnings": warnings}

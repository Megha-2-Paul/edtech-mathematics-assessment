import re
from typing import Any, Dict, List

from .math_validator import validate_mathematics
from .completeness_validator import validate_completeness


AD_TEXT = re.compile(r"advertisement|login/register|remove all ads|view solution", re.I)


def validate(record: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    paper = record.get("paper", {})
    for field in ("source_url", "board", "class_level", "subject", "academic_year"):
        if not paper.get(field):
            errors.append({"field": f"paper.{field}", "message": "Required metadata is missing"})
    questions = record.get("questions", [])
    if not questions:
        errors.append({"field": "questions", "message": "No questions extracted"})
    numbers = [q.get("question_number") for q in questions]
    if len(numbers) != len(set(numbers)):
        errors.append({"field": "questions", "message": "Duplicate question numbers detected"})
    subquestion_count = 0
    image_count = 0
    table_count = 0
    math_count = 0

    question_texts = []

    def inspect(question: Dict[str, Any]) -> None:
        nonlocal subquestion_count, image_count, table_count, math_count
        subquestion_count += len(question.get("subquestions", []))
        if not question.get("question_number"):
            errors.append({"field": "questions", "message": "Question number is empty"})
        content = question.get("content", [])
        text_values = [str(block.get("value", "")) for block in content
                       if block.get("type") == "text"]
        question_texts.extend(text_values)
        if not content and not question.get("subquestions"):
            errors.append({"field": f"question.{question.get('question_number')}", "message": "Empty question"})
        for block in content:
            if block.get("type") == "text" and AD_TEXT.search(str(block.get("value", ""))):
                warnings.append({"field": "content", "message": "Navigation, advertisement, or solution text detected"})
            if block.get("type") == "image" and not block.get("asset_id"):
                image_count += 1
                warnings.append({"field": "image", "message": "Image has not been assigned a local asset"})
            elif block.get("type") == "image":
                image_count += 1
            if block.get("type") == "table":
                table_count += 1
            if block.get("type") == "math":
                math_count += 1
        for subquestion in question.get("subquestions", []):
            inspect(subquestion)

    for question in questions:
        inspect(question)
    if len(question_texts) != len(set(question_texts)):
        warnings.append({"field": "questions", "message": "Duplicate question text detected"})
    structural = {
        "errors": errors.copy(),
        "valid": not errors,
        "statistics": {"question_count": len(questions)},
    }
    mathematical_warnings = [
        warning for warning in warnings
        if warning["field"] in {"math", "content"}
    ]
    question_warnings = [
        warning for warning in warnings
        if warning["field"] in {"image", "questions", "content"}
    ]
    mathematics = validate_mathematics(record)
    completeness = validate_completeness(record)
    warnings.extend({"field": "question_completeness", **warning}
                    for warning in completeness["warnings"])
    warnings.extend({"field": "math", **warning}
                    for warning in mathematics["warnings"])
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "STRUCTURAL_VALIDATION": structural,
        "MATHEMATICAL_CONTENT_VALIDATION": {
            "valid": mathematics["valid"],
            "warnings": mathematics["warnings"],
        },
        "QUESTION_CONTENT_VALIDATION": {
            "valid": not question_warnings,
            "warnings": question_warnings,
        },
        "QUESTION_COMPLETENESS_VALIDATION": completeness,
        "statistics": {
            "question_count": len(questions),
            "subquestion_count": subquestion_count,
            "image_count": image_count,
            "table_count": table_count,
            "mathematical_block_count": math_count,
        },
    }

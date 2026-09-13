"""Student-facing report preparation and deterministic recommendations."""


def build_recommendations(diagnosis):
    errors = {item["code"]: item["count"] for item in diagnosis["error_counts"]}
    recommendations = []

    if errors.get("C01", 0) + errors.get("C04", 0) >= 2:
        recommendations.append(
            {
                "priority": 1,
                "title": "Improve calculation and sign accuracy",
                "action": (
                    "Practise calculation-heavy sets and check signs and arithmetic "
                    "before finalising."
                ),
            }
        )
    if errors.get("C02", 0) >= 2:
        recommendations.append(
            {
                "priority": 1,
                "title": "Strengthen concepts",
                "action": (
                    "Revise the underlying concept, then test it with application "
                    "questions."
                ),
            }
        )
    if errors.get("C03", 0) >= 2:
        recommendations.append(
            {
                "priority": 2,
                "title": "Revise formula use",
                "action": (
                    "Practise recalling formulas and identifying which formula "
                    "applies before calculating."
                ),
            }
        )
    if errors.get("C05", 0) + errors.get("C07", 0) >= 2:
        recommendations.append(
            {
                "priority": 2,
                "title": "Improve solution presentation",
                "action": "Write complete steps and include required justifications.",
            }
        )
    if errors.get("C06", 0) >= 2:
        recommendations.append(
            {
                "priority": 1,
                "title": "Choose the correct method",
                "action": (
                    "Practise identifying the method before solving and compare "
                    "with worked solutions afterward."
                ),
            }
        )
    if errors.get("C08", 0) >= 1:
        recommendations.append(
            {
                "priority": 2,
                "title": "Read the question carefully",
                "action": (
                    "Identify what is given and what is required before selecting "
                    "the method."
                ),
            }
        )
    if errors.get("C09", 0) >= 1 or diagnosis["attempt_rate"] < 80:
        recommendations.append(
            {
                "priority": 1,
                "title": "Improve completion and time use",
                "action": (
                    "Practise timed sections and use a first-pass strategy so easier "
                    "marks are not left unattempted."
                ),
            }
        )

    for weakness in diagnosis["weaknesses"][:2]:
        recommendations.append(
            {
                "priority": 1,
                "title": f"Revise {weakness['name']}",
                "action": (
                    f"Review core concepts in {weakness['name']} and complete "
                    "targeted practice before the next test."
                ),
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "priority": 1,
                "title": "Maintain current performance",
                "action": (
                    "Continue mixed practice and use the next assessment to check "
                    "whether the level is sustained."
                ),
            }
        )

    return sorted(recommendations, key=lambda x: x["priority"])[:5]


def build_report(diagnosis, student, test, attempt):
    return {
        "student_name": getattr(student, "name", "Student"),
        "student_id": getattr(student, "student_id", attempt.student_id),
        "test_title": test.title,
        "test_id": test.test_id,
        "attempt_id": attempt.attempt_id,
        "test_date": getattr(test, "test_date", None)
        or (
            attempt.submitted_at.strftime("%d %b %Y")
            if attempt.submitted_at
            else None
        ),
        "diagnosis": diagnosis,
        "recommendations": build_recommendations(diagnosis),
    }

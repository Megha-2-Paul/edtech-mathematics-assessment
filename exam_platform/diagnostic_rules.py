"""Deterministic interpretation rules for student performance diagnosis."""


def interpret_diagnosis(error_counts, attempt_rate, accuracy, weaknesses):
    errors = {item["code"]: item["count"] for item in error_counts}
    signals = []
    if errors.get("C01", 0) + errors.get("C04", 0) >= 2:
        signals.append({"type": "accuracy", "title": "Accuracy is costing marks", "message": "The student has repeated calculation/sign errors. This can indicate avoidable accuracy loss rather than a simple lack of chapter knowledge."})
    if errors.get("C02", 0) + errors.get("C03", 0) >= 2:
        signals.append({"type": "knowledge", "title": "Concept or formula understanding needs attention", "message": "Repeated conceptual/formula errors suggest revision should come before more difficult application practice."})
    if errors.get("C05", 0) + errors.get("C07", 0) >= 2:
        signals.append({"type": "presentation", "title": "Complete working is costing marks", "message": "The student is losing marks through incomplete steps or missing justification. Solution presentation needs targeted practice."})
    if errors.get("C06", 0) >= 2:
        signals.append({"type": "method", "title": "Method selection needs attention", "message": "Repeated wrong-method errors suggest the student should practise identifying the appropriate method before solving."})
    if errors.get("C08", 0) >= 1:
        signals.append({"type": "interpretation", "title": "Question interpretation needs attention", "message": "At least one error was linked to misunderstanding the question. Practise identifying what is given and what is required."})
    if errors.get("C09", 0) >= 1 or attempt_rate < 80:
        signals.append({"type": "completion", "title": "Completion/time management is costing marks", "message": "The student is leaving questions unattempted or has a time-related error. Timed practice and better question selection should be prioritised."})
    if not signals and accuracy >= 75:
        signals.append({"type": "maintenance", "title": "Performance is broadly consistent", "message": "No major recurring error pattern was detected in this assessment. Maintain mixed practice and monitor future tests."})
    elif not signals:
        signals.append({"type": "mixed", "title": "Mixed performance needs more evidence", "message": "No single dominant error pattern was detected. Use the next assessment to establish a clearer weakness profile."})
    if weaknesses:
        signals.append({"type": "chapter", "title": f"Priority chapter: {weaknesses[0]['name']}", "message": f"This chapter is currently below the diagnostic benchmark at {weaknesses[0]['percentage']}%. Targeted revision should be considered."})
    return signals

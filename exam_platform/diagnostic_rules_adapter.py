"""Small adapter keeping diagnostic interpretation separate from data collection."""
from .diagnostic_rules import interpret_diagnosis


def add_diagnostic_interpretation(diagnosis):
    diagnosis = dict(diagnosis)
    diagnosis["interpretations"] = interpret_diagnosis(
        diagnosis.get("error_counts", []),
        diagnosis.get("attempt_rate", 0),
        diagnosis.get("accuracy", 0),
        diagnosis.get("weaknesses", []),
    )
    return diagnosis

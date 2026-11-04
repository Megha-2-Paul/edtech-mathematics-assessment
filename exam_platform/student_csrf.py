"""CSRF protection for student assessment mutation routes."""

import hmac
import secrets

from flask import jsonify, request, session


_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_STUDENT_MUTATION_ENDPOINTS = frozenset(
    {
        "start_test",
        "save_response",
        "upload_answer_image",
        "delete_image",
        "submit_attempt",
    }
)


def _student_csrf_token():
    token = session.get("_student_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_student_csrf_token"] = token
    return token


def register_student_csrf(app):
    """Register CSRF token injection and validation for student mutations."""

    @app.context_processor
    def inject_student_csrf_token():
        return {"student_csrf_token": _student_csrf_token()}

    @app.before_request
    def enforce_student_csrf():
        if request.method not in _STATE_CHANGING_METHODS:
            return None

        if request.endpoint not in _STUDENT_MUTATION_ENDPOINTS:
            return None

        expected = str(session.get("_student_csrf_token") or "")
        supplied = str(
            request.headers.get("X-Student-CSRF-Token")
            or request.form.get("student_csrf_token")
            or ""
        )

        if not supplied or not expected or not hmac.compare_digest(
            supplied, expected
        ):
            return jsonify({"error": "Invalid or missing CSRF token"}), 400

        return None
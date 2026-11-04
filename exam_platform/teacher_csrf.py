"""CSRF protection for browser-based teacher/admin mutation routes."""

import hmac
import secrets

from flask import jsonify, request, session


_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _teacher_csrf_token():
    token = session.get("_teacher_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_teacher_csrf_token"] = token
    return token


def register_teacher_csrf(app):
    """Register CSRF token injection and validation for teacher/admin
    mutations and extraction-review requests.
    """

    @app.context_processor
    def inject_teacher_csrf_token():
        return {"teacher_csrf_token": _teacher_csrf_token()}

    @app.before_request
    def enforce_teacher_csrf():
        if request.method not in _STATE_CHANGING_METHODS:
            return None
        is_teacher_route = request.path.startswith("/teacher/")
        is_extraction_review_route = (request.endpoint or "").startswith("extraction_review.")
        if not (is_teacher_route or is_extraction_review_route):
            return None

        expected = str(session.get("_teacher_csrf_token") or "")
        supplied = str(
            request.headers.get("X-Teacher-CSRF-Token")
            or request.form.get("teacher_csrf_token")
            or ""
        )
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            return jsonify({"error": "Invalid or missing CSRF token"}), 400
        return None

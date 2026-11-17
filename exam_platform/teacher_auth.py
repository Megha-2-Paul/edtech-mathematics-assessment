"""Application-wide HTTP Basic Authentication for teacher routes."""

import hmac
import os

from flask import Response, request


def register_teacher_auth(app):
    """Require configured Basic Auth for all teacher routes."""

    @app.before_request
    def protect_teacher_routes():
        path = request.path
        if path != "/teacher" and not path.startswith("/teacher/"):
            return None

        password = os.getenv("TEACHER_ACCESS_PASSWORD")
        username = os.getenv("TEACHER_ACCESS_USERNAME", "teacher")

        if not password:
            if os.getenv("RENDER"):
                return Response("Teacher access is not configured.", status=503)
            return None

        auth = request.authorization
        if (
            not auth
            or not hmac.compare_digest(auth.username or "", username)
            or not hmac.compare_digest(auth.password or "", password)
        ):
            return Response(
                "Teacher access required.",
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Improvia Teacher"'},
            )

        return None
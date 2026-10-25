"""WSGI entry point for the Improvia deployment.

Keep deployment-only access controls here. Answer-image handling lives in
exam_platform.app so local and hosted deployments use the same private routes.
"""

import hmac
import os

from flask import Response, request

from exam_platform.app import app


# ---------------------------------------------------------------------------
# Deployment-only application settings
# ---------------------------------------------------------------------------

secret_key = os.getenv("SECRET_KEY")
if os.getenv("RENDER") and not secret_key:
    raise RuntimeError("SECRET_KEY must be configured on the hosted service.")
if secret_key:
    app.secret_key = secret_key


@app.before_request
def protect_teacher_routes():
    """Require configured HTTP Basic Auth for teacher-side routes."""
    if not request.path.startswith("/teacher"):
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


application = app

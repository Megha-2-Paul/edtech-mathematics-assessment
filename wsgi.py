"""WSGI entry point for the Improvia deployment.

Deployment configuration is applied here. Application-wide route controls
are registered in exam_platform.app for local and hosted deployments.
"""

import os

from exam_platform.app import app, initialize_app

# ---------------------------------------------------------------------------
# Deployment-only application settings
# ---------------------------------------------------------------------------

secret_key = os.getenv("SECRET_KEY")
if os.getenv("RENDER") and not secret_key:
    raise RuntimeError("SECRET_KEY must be configured on the hosted service.")
if secret_key:
    app.secret_key = secret_key


initialize_app()

application = app

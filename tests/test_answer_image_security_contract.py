from pathlib import Path


APP_SOURCE = Path(__file__).resolve().parents[1] / "exam_platform" / "app.py"


def test_answer_images_are_not_served_from_a_public_uploads_route():
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert '@app.route("/uploads/<path:filename>")' not in source
    assert '"/api/attempt/<attempt_id>/images/<image_id>/content"' in source


def test_answer_image_proxy_checks_attempt_access_and_uses_private_cache_headers():
    source = APP_SOURCE.read_text(encoding="utf-8")
    route_start = source.index("def get_answer_image(")
    route_end = source.index("\n\nif __name__ == \"__main__\":", route_start)
    route = source[route_start:route_end]

    assert "ensure_attempt_access(attempt_id)" in route
    assert "item.image_id == image_id and item.attempt_id == attempt_id" in route
    assert "media.read_stored_image(" in route
    assert 'upload_folder=app.config["UPLOAD_FOLDER"]' in route
    assert 'response.headers["Cache-Control"] = "private, no-store"' in route
    assert 'response.headers["X-Content-Type-Options"] = "nosniff"' in route


def test_submitted_attempts_reject_mutating_http_methods():
    source = APP_SOURCE.read_text(encoding="utf-8")
    helper_start = source.index("def ensure_attempt_access(")
    helper_end = source.index("\n\nload_mock_data()", helper_start)
    helper = source[helper_start:helper_end]

    assert "attempt.status == AttemptStatus.SUBMITTED.value" in helper
    assert '"POST", "PUT", "PATCH", "DELETE"' in helper
    assert "cannot be changed." in helper
    assert "409" in helper


def test_wsgi_does_not_replace_private_image_routes_with_legacy_handlers():
    wsgi_source = (
        Path(__file__).resolve().parents[1] / "wsgi.py"
    ).read_text(encoding="utf-8")

    assert 'app.view_functions["uploaded_file"]' not in wsgi_source
    assert 'app.view_functions["upload_answer_image"]' not in wsgi_source
    assert 'app.view_functions["get_question_images"]' not in wsgi_source
    assert "/uploads/" not in wsgi_source


def test_private_image_reads_are_constrained_to_configured_storage_root():
    media_source = (
        Path(__file__).resolve().parents[1] / "exam_platform" / "media.py"
    ).read_text(encoding="utf-8")
    assert "path.relative_to(root)" in media_source
    assert "outside the private upload directory" in media_source
    assert 'for delivery_type in ("authenticated", "upload")' not in media_source



def test_assessment_templates_attach_csrf_tokens_to_mutating_fetch_requests():
    root = Path(__file__).resolve().parents[1] / "exam_platform" / "templates"
    base = (root / "base.html").read_text(encoding="utf-8")
    app_source = APP_SOURCE.read_text(encoding="utf-8")

    assert 'meta name="csrf-token"' in base
    assert 'headers.set("X-CSRF-Token", token)' in base
    assert 'return nativeFetch(input, requestOptions);' in base
    assert "request.headers.get(\"X-CSRF-Token\")" in app_source

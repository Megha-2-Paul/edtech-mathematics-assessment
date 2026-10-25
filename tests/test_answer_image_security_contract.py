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
    assert "media.read_stored_image(image.file_path)" in route
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

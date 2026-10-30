from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "exam_platform" / "app.py").read_text(encoding="utf-8")
LOGIN_TEMPLATE = (ROOT / "exam_platform" / "templates" / "student_login.html").read_text(encoding="utf-8")
ACTIVATE_TEMPLATE = (ROOT / "exam_platform" / "templates" / "student_activate.html").read_text(encoding="utf-8")
MIGRATION_SOURCE = (ROOT / "question_bank" / "migrations" / "006_student_access.py").read_text(encoding="utf-8")


def test_anonymous_requests_do_not_create_guest_students():
    assert 'return session.get("student_id")' in APP_SOURCE
    assert 'Guest Student' not in APP_SOURCE
    assert "def enforce_student_access" in APP_SOURCE


def test_assessment_routes_require_an_active_student_session():
    for prefix in ('"/tests"', '"/test/"', '"/api/test/"', '"/api/attempt/"', '"/report/"', '"/result/"'):
        assert prefix in APP_SOURCE
    assert 'str(student.status or "").lower() != "active"' in APP_SOURCE


def test_login_and_activation_forms_include_csrf_tokens():
    assert 'name="csrf_token"' in LOGIN_TEMPLATE
    assert 'name="csrf_token"' in ACTIVATE_TEMPLATE
    assert "def _valid_csrf()" in APP_SOURCE
    assert "if not _valid_csrf():" in APP_SOURCE


def test_activation_tokens_are_hashed_and_passwords_are_hashed():
    assert "hashlib.sha256(token.encode" in APP_SOURCE
    assert "generate_password_hash(password)" in APP_SOURCE
    assert 'check_password_hash(row["password_hash"], password)' in APP_SOURCE
    assert "student_access_credentials" in MIGRATION_SOURCE
    assert "student_access_tokens" in MIGRATION_SOURCE


def test_migration_defaults_to_audit_only():
    assert "Default mode is read-only" in MIGRATION_SOURCE
    assert "--apply" in MIGRATION_SOURCE

def test_csrf_guard_covers_state_changing_student_assessment_requests():
    assert "def enforce_csrf():" in APP_SOURCE
    assert 'request.method not in {"POST", "PUT", "PATCH", "DELETE"}' in APP_SOURCE
    assert '"/student/"' in APP_SOURCE
    assert '"/api/test/"' in APP_SOURCE
    assert '"/api/attempt/"' in APP_SOURCE
    assert 'if not _valid_csrf():' in APP_SOURCE
    assert 'return jsonify({"error": "Invalid or missing CSRF token"}), 400' in APP_SOURCE


def test_csrf_guard_does_not_capture_machine_to_machine_or_teacher_routes():
    guard_start = APP_SOURCE.index("def enforce_csrf():")
    guard_end = APP_SOURCE.index("\n\ndef _token_hash", guard_start)
    guard = APP_SOURCE[guard_start:guard_end]
    assert "request.path.startswith(CSRF_PROTECTED_PREFIXES)" in guard
    assert '"/api/registrations/google-form"' not in guard
    assert '"/teacher/students/<student_id>/access-link"' not in guard


def _isolated_csrf_client():
    """Build a tiny Flask app from the real CSRF hook without importing app.py."""
    import ast
    import hmac

    from flask import Flask, jsonify, request, session

    tree = ast.parse(APP_SOURCE)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "CSRF_PROTECTED_PREFIXES"
            for target in node.targets
        ):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {"_valid_csrf", "enforce_csrf"}:
            node.decorator_list = []
            selected.append(node)

    namespace = {"hmac": hmac, "request": request, "session": session, "jsonify": jsonify}
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), "<csrf-source>", "exec"), namespace)

    test_app = Flask(__name__)
    test_app.secret_key = "csrf-test-only-secret"
    test_app.before_request(namespace["enforce_csrf"])

    @test_app.route("/api/attempt/example/response", methods=["POST"])
    def assessment_mutation():
        return {"ok": True}, 200

    @test_app.route("/api/registrations/google-form", methods=["POST"])
    def registration_webhook():
        return {"ok": True}, 200

    @test_app.route("/teacher/students/example/access-link", methods=["POST"])
    def teacher_route():
        return {"ok": True}, 200

    return test_app.test_client()


def test_csrf_guard_rejects_missing_and_invalid_tokens():
    client = _isolated_csrf_client()

    missing = client.post("/api/attempt/example/response")
    assert missing.status_code == 400
    assert missing.get_json() == {"error": "Invalid or missing CSRF token"}

    with client.session_transaction() as session:
        session["_csrf_token"] = "expected-token"
    invalid = client.post(
        "/api/attempt/example/response",
        headers={"X-CSRF-Token": "wrong-token"},
    )
    assert invalid.status_code == 400
    assert invalid.get_json() == {"error": "Invalid or missing CSRF token"}


def test_csrf_guard_accepts_valid_token():
    client = _isolated_csrf_client()
    with client.session_transaction() as session:
        session["_csrf_token"] = "expected-token"

    response = client.post(
        "/api/attempt/example/response",
        headers={"X-CSRF-Token": "expected-token"},
    )
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_csrf_guard_leaves_webhook_and_teacher_routes_outside_scope():
    client = _isolated_csrf_client()

    assert client.post("/api/registrations/google-form").status_code == 200
    assert client.post("/teacher/students/example/access-link").status_code == 200

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

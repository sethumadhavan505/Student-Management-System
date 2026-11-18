import re
from pathlib import Path

import pytest

from app import (
    EMAIL_PATTERN,
    MAX_DEPARTMENT_LENGTH,
    MAX_NAME_LENGTH,
    MAX_ROLL_NUMBER_LENGTH,
    MAX_ACADEMIC_YEAR,
    MIN_ACADEMIC_YEAR,
    create_app,
)
from werkzeug.security import generate_password_hash

TEST_PASSWORD_HASH = generate_password_hash("test-password")


def sign_in(client):
    login_page = client.get("/login")
    login_token = re.search(
        rb'name="csrf_token" value="([^"]+)"', login_page.data
    ).group(1).decode()
    login_response = client.post(
        "/login",
        data={
            "csrf_token": login_token,
            "username": "test-admin",
            "password": "test-password",
        },
    )
    assert login_response.status_code == 302
    dashboard = client.get("/")
    csrf_token = re.search(
        rb'name="csrf-token" content="([^"]+)"', dashboard.data
    ).group(1).decode()
    client.environ_base["HTTP_X_CSRF_TOKEN"] = csrf_token


@pytest.fixture()
def client(tmp_path):
    app=create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "SECRET_KEY": "test-secret-key-for-session-signing",
        "ADMIN_USERNAME": "test-admin",
        "ADMIN_PASSWORD_HASH": TEST_PASSWORD_HASH,
    })
    with app.test_client() as client:
        sign_in(client)
        yield client


def student(**overrides):
    data={"name":"Asha Kumar","roll_number":"IT001","department":"Information Technology","academic_year":"2026","email":"asha@example.com"}
    data.update(overrides); return data


def test_home_page(client):
    response=client.get("/")
    assert response.status_code==200
    assert b"Student Management System" in response.data
    assert b"Sign out" in response.data


def test_student_api_requires_authenticated_session(client):
    anonymous_client = client.application.test_client()
    response = anonymous_client.get("/api/students")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}
    assert anonymous_client.get("/").status_code == 302


def test_login_rejects_bad_credentials_and_missing_csrf(client):
    anonymous_client = client.application.test_client()
    login_page = anonymous_client.get("/login")
    token = re.search(
        rb'name="csrf_token" value="([^"]+)"', login_page.data
    ).group(1).decode()

    missing_csrf = anonymous_client.post(
        "/login",
        data={"username": "test-admin", "password": "test-password"},
    )
    assert missing_csrf.status_code == 400

    invalid_credentials = anonymous_client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "not-é-admin",
            "password": "wrong-password",
        },
    )
    assert invalid_credentials.status_code == 401
    assert b"Invalid username or password." in invalid_credentials.data


def test_api_mutations_require_csrf_token(client):
    anonymous_client = client.application.test_client()
    login_page = anonymous_client.get("/login")
    token = re.search(
        rb'name="csrf_token" value="([^"]+)"', login_page.data
    ).group(1).decode()
    anonymous_client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "test-admin",
            "password": "test-password",
        },
    )

    response = anonymous_client.post(
        "/api/students",
        json=student(),
        headers={"X-CSRF-Token": "invalid-é"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid or missing CSRF token."}


def test_logout_clears_authenticated_session(client):
    dashboard = client.get("/")
    csrf_token = re.search(
        rb'name="csrf-token" content="([^"]+)"', dashboard.data
    ).group(1).decode()

    response = client.post("/logout", data={"csrf_token": csrf_token})

    assert response.status_code == 302
    assert client.get("/api/students").status_code == 401


def test_login_fails_closed_when_authentication_is_unconfigured(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "unconfigured.sqlite"),
        "SECRET_KEY": None,
        "ADMIN_USERNAME": None,
        "ADMIN_PASSWORD_HASH": None,
    })
    client = app.test_client()

    assert client.get("/login").status_code == 503
    response = client.get("/api/students")
    assert response.status_code == 503
    assert response.get_json() == {"error": "Authentication is not configured."}


def test_export_button_is_available_in_both_frontends(client):
    flask_page = client.get("/")
    demo_page = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")

    assert b'id="exportButton"' in flask_page.data
    assert "Export CSV" in demo_page


def test_export_uses_student_fields_and_csv_escaping(client):
    script = client.get("/static/js/app.js").get_data(as_text=True)

    assert '["created_at", "Created At"]' in script
    assert '["academic_year", "Academic Year"]' in script
    assert 'function escapeCsvValue(value)' in script
    assert "safeText.replace(/\"/g, '\"\"')" in script
    assert r"/^[\u0000-\u0020\uFEFF]*[=+\-@]/.test(text)" in script
    assert "`'${text}`" in script
    assert ": text;" in script
    assert "students.map((student)" in script
    assert "exportButton.addEventListener(\"click\", exportStudentsToCsv)" in script


def test_search_fields_match_between_api_and_browser_storage(client):
    root = Path(__file__).resolve().parents[1]
    script = (root / "static" / "js" / "app.js").read_text(encoding="utf-8")
    backend = (root / "app.py").read_text(encoding="utf-8")

    expected_js = '["name", "roll_number", "department", "email"]'
    assert f"const searchableFields = {expected_js};" in script
    assert 'SEARCHABLE_FIELDS = ("name", "roll_number", "department", "email")' in backend


def test_validation_rules_match_between_flask_and_browser_storage(client):
    script = (
        Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"
    ).read_text(encoding="utf-8")
    backend = (Path(__file__).resolve().parents[1] / "app.py").read_text(
        encoding="utf-8"
    )
    matching_rules = [
        (f"MAX_NAME_LENGTH = {MAX_NAME_LENGTH}", f"maxNameLength = {MAX_NAME_LENGTH}"),
        (
            f"MAX_DEPARTMENT_LENGTH = {MAX_DEPARTMENT_LENGTH}",
            f"maxDepartmentLength = {MAX_DEPARTMENT_LENGTH}",
        ),
        (
            f"MAX_ROLL_NUMBER_LENGTH = {MAX_ROLL_NUMBER_LENGTH}",
            f"maxRollNumberLength = {MAX_ROLL_NUMBER_LENGTH}",
        ),
        (f"MIN_ACADEMIC_YEAR = {MIN_ACADEMIC_YEAR}", f"minAcademicYear = {MIN_ACADEMIC_YEAR}"),
        (f"MAX_ACADEMIC_YEAR = {MAX_ACADEMIC_YEAR}", f"maxAcademicYear = {MAX_ACADEMIC_YEAR}"),
    ]

    for python_rule, javascript_rule in matching_rules:
        assert python_rule in backend
        assert javascript_rule in script
    assert f"const emailPattern = /^{EMAIL_PATTERN}$/" in script


def test_dynamic_results_are_announced_and_actions_are_labeled(client):
    page = client.get("/").get_data(as_text=True)
    demo_page = (
        Path(__file__).resolve().parents[1] / "index.html"
    ).read_text(encoding="utf-8")
    script = client.get("/static/js/app.js").get_data(as_text=True)

    assert (
        'id="resultsStatus" class="sr-only" role="status" aria-live="polite"'
        in page
    )
    assert (
        'id="resultsStatus" class="sr-only" role="status" aria-live="polite"'
        in demo_page
    )
    assert 'aria-label="Edit ${escapeHtml(student.name)}"' in script
    assert 'aria-label="Delete ${escapeHtml(student.name)}"' in script


def test_create_and_list(client):
    response=client.post("/api/students",json=student())
    assert response.status_code==201
    assert len(client.get("/api/students").json)==1


def test_invalid_email(client):
    response=client.post("/api/students",json=student(email="bad"))
    assert response.status_code==400


def test_duplicate_rejected(client):
    client.post("/api/students",json=student())
    response=client.post("/api/students",json=student(email="other@example.com"))
    assert response.status_code==400


def test_update_delete(client):
    sid=client.post("/api/students",json=student()).json["id"]
    assert client.put(f"/api/students/{sid}",json=student(name="Asha Updated")).status_code==200
    assert client.delete(f"/api/students/{sid}").status_code==200


def test_student_summary_returns_counts_and_departments(client):
    client.post("/api/students", json=student())
    client.post(
        "/api/students",
        json=student(
            roll_number="CS101",
            department="Computer Science",
            email="other@example.com",
        ),
    )
    client.post(
        "/api/students",
        json=student(
            roll_number="IT002",
            department="information technology",
            email="third@example.com",
        ),
    )

    response = client.get("/api/students/summary")

    assert response.status_code == 200
    summary = response.get_json()
    assert summary["total_students"] == 3
    assert summary["department_count"] == 2
    assert set(summary["departments"]) == {
        "Computer Science",
        "Information Technology",
        "information technology",
    }

# ----------------------------------------------------------------------
# Additional tests for create flow
# ----------------------------------------------------------------------

def test_create_missing_required_fields(client):
    # Required fields should be rejected when omitted.
    for field in ["name", "roll_number", "department", "email"]:
        payload = student()
        payload.pop(field)
        response = client.post("/api/students", json=payload)
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_create_blank_required_fields(client):
    # Whitespace-only values should be treated as missing.
    payloads = [
        student(name="   "),
        student(roll_number="   "),
        student(department="   "),
        student(email="   "),
    ]
    for payload in payloads:
        response = client.post("/api/students", json=payload)
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_create_rejects_invalid_email_formats(client):
    # Invalid email values should be rejected by backend validation.
    invalid_emails = [
        "bad",
        "a@b",
        "user@@example.com",
        "user@example",
        "user example.com",
        " user@example.com ",
        "user@.com",
    ]
    for email in invalid_emails:
        response = client.post("/api/students", json=student(email=email))
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_create_rejects_duplicate_roll_number(client):
    # Duplicate roll numbers are not allowed.
    client.post("/api/students", json=student())
    response = client.post("/api/students", json=student(roll_number="IT001"))
    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


def test_create_rejects_duplicate_email_case_insensitive(client):
    # Email uniqueness should be case-insensitive.
    client.post("/api/students", json=student())
    response = client.post("/api/students", json=student(email="ASHA@example.com"))
    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


def test_create_rejects_name_length_101(client):
    # Name length limit is 100 characters.
    payload = student(name="A" * 101)
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "100 characters" in response.get_json()["error"]


def test_create_rejects_department_length_101(client):
    # Department length limit is 100 characters.
    payload = student(department="B" * 101)
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "100 characters" in response.get_json()["error"]


def test_create_rejects_roll_number_length_31(client):
    # Roll number limit is 30 characters.
    payload = student(roll_number="R" * 31)
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "30 characters" in response.get_json()["error"]


def test_create_rejects_non_object_json(client):
    # Request body must be a JSON object.
    response = client.post("/api/students", json=["not", "an", "object"])
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_rejects_empty_json_object(client):
    # Empty payload should fail validation.
    response = client.post("/api/students", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_rejects_malformed_json(client):
    # Malformed JSON should not be silently accepted.
    response = client.post(
        "/api/students",
        data="{bad json",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_ignores_unknown_fields_consistently(client):
    # Extra unrecognized fields should not break creation.
    payload = student()
    payload["unexpected_field"] = "extra"
    response = client.post("/api/students", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert "unexpected_field" not in data

# ----------------------------------------------------------------------
# Additional tests for list/search flow
# ----------------------------------------------------------------------

def test_list_returns_students_in_descending_id_order(client):
    # Newer students should appear first.
    first_response = client.post(
        "/api/students",
        json=student(roll_number="IT001", email="first@example.com"),
    )
    second_response = client.post(
        "/api/students",
        json=student(roll_number="IT002", email="second@example.com"),
    )
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first = first_response.get_json()
    second = second_response.get_json()
    assert "id" in first
    assert "id" in second
    response = client.get("/api/students")
    body = response.get_json()

    assert response.status_code == 200
    assert [student["id"] for student in body] == [second["id"], first["id"]]


def test_list_filters_by_name_roll_number_department_and_email(client):
    # Search should return matching results across all searchable fields.
    client.post(
        "/api/students",
        json=student(roll_number="IT001", name="Asha Kumar", department="IT", email="asha@example.com"),
    )
    client.post(
        "/api/students",
        json=student(roll_number="CS101", name="Ravi Nair", department="Computer Science", email="ravi@example.com"),
    )

    response = client.get("/api/students?q=asha")
    assert response.status_code == 200
    results = response.get_json()
    assert len(results) == 1
    assert results[0]["email"] == "asha@example.com"

    response = client.get("/api/students?q=CS101")
    assert response.status_code == 200
    results = response.get_json()
    assert len(results) == 1
    assert results[0]["roll_number"] == "CS101"

    response = client.get("/api/students?q=computer")
    assert response.status_code == 200
    results = response.get_json()
    assert len(results) == 1
    assert results[0]["department"] == "Computer Science"


def test_list_search_with_special_characters_returns_empty_list(client):
    # Search string should not crash or trigger unsafe behavior.
    response = client.get("/api/students?q=\" OR 1=1 --")
    assert response.status_code == 200
    assert response.get_json() == []

# ----------------------------------------------------------------------
# Additional tests for update flow
# ----------------------------------------------------------------------

def test_update_existing_student_successfully(client):
    # Updating an existing record should persist the new values.
    created = client.post("/api/students", json=student()).get_json()
    payload = student(
        name="Asha Updated",
        roll_number="IT999",
        department="Computer Science",
        email="asha.updated@example.com",
    )
    response = client.put(f"/api/students/{created['id']}", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Asha Updated"
    assert data["roll_number"] == "IT999"
    assert data["department"] == "Computer Science"
    assert data["email"] == "asha.updated@example.com"


def test_update_nonexistent_student_returns_404(client):
    # Updating a missing student should return a 404.
    response = client.put("/api/students/999999", json=student())
    assert response.status_code == 404
    assert "Student not found" in response.get_json()["error"]


def test_update_rejects_invalid_email(client):
    # Invalid updated email should be blocked.
    created = client.post("/api/students", json=student()).get_json()
    response = client.put(f"/api/students/{created['id']}", json=student(email="bad-email"))
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_rejects_duplicate_email(client):
    # Updating to an email already used by another student should fail.
    client.post("/api/students", json=student(roll_number="IT001", email="first@example.com"))
    created = client.post("/api/students", json=student(roll_number="IT002", email="second@example.com")).get_json()

    response = client.put(
        f"/api/students/{created['id']}",
        json=student(roll_number="IT002", email="first@example.com"),
    )
    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


def test_update_rejects_duplicate_roll_number(client):
    # Updating to an existing roll number should fail.
    client.post("/api/students", json=student(roll_number="IT001", email="first@example.com"))
    created = client.post("/api/students", json=student(roll_number="IT002", email="second@example.com")).get_json()

    response = client.put(
        f"/api/students/{created['id']}",
        json=student(roll_number="IT001", email="second@example.com"),
    )
    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


def test_update_rejects_empty_json(client):
    # Empty object payload should fail validation.
    created = client.post("/api/students", json=student()).get_json()
    response = client.put(f"/api/students/{created['id']}", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_rejects_malformed_json(client):
    # Invalid JSON body should not crash the app.
    created = client.post("/api/students", json=student()).get_json()
    response = client.put(
        f"/api/students/{created['id']}",
        data="{bad json",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_update_preserves_id_and_created_at(client):
    # Replacing a record should not change its identity metadata.
    created = client.post("/api/students", json=student()).get_json()
    before_created = created["created_at"]

    response = client.put(
        f"/api/students/{created['id']}",
        json=student(
            name="Asha Updated",
            roll_number="IT999",
            department="Computer Science",
            email="new@example.com",
        ),
    )

    updated = response.get_json()
    assert updated["id"] == created["id"]
    assert updated["created_at"] == before_created

# ----------------------------------------------------------------------
# Additional tests for delete flow
# ----------------------------------------------------------------------

def test_delete_existing_student_successfully(client):
    # Deleting an existing record should succeed.
    created = client.post("/api/students", json=student()).get_json()
    response = client.delete(f"/api/students/{created['id']}")
    assert response.status_code == 200
    assert response.get_json()["message"] == "Student deleted successfully."


def test_delete_nonexistent_student_returns_404(client):
    # Delete on a missing id should return a 404.
    response = client.delete("/api/students/999999")
    assert response.status_code == 404
    assert "Student not found" in response.get_json()["error"]


def test_delete_twice_returns_404_second_time(client):
    # Second delete should fail after the record is already removed.
    created = client.post("/api/students", json=student()).get_json()
    client.delete(f"/api/students/{created['id']}")
    response = client.delete(f"/api/students/{created['id']}")
    assert response.status_code == 404
    assert "Student not found" in response.get_json()["error"]


def test_delete_removes_row_from_db(client):
    # DB should reflect the deletion.
    created = client.post("/api/students", json=student()).get_json()
    response = client.delete(f"/api/students/{created['id']}")
    assert response.status_code == 200

    rows = client.get("/api/students").get_json()
    assert rows == []

# ----------------------------------------------------------------------
# Additional tests for invalid input and boundary values
# ----------------------------------------------------------------------

def test_create_rejects_whitespace_only_values(client):
    # Fields with only spaces should fail validation.
    payloads = [
        student(name="   "),
        student(roll_number=" \t "),
        student(department="   "),
        student(email="   "),
    ]
    for payload in payloads:
        response = client.post("/api/students", json=payload)
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_update_rejects_whitespace_only_values(client):
    # Updating with whitespace-only values should be rejected.
    created = client.post("/api/students", json=student()).get_json()
    payloads = [
        student(name="   "),
        student(roll_number=" \t "),
        student(department="   "),
        student(email="   "),
    ]
    for payload in payloads:
        response = client.put(f"/api/students/{created['id']}", json=payload)
        assert response.status_code == 400
        assert "error" in response.get_json()


def test_create_rejects_special_characters_in_name_if_unexpected(client):
    # This is a regression guard for unusual but common user input.
    payload = student(name="<script>alert(1)</script>")
    response = client.post("/api/students", json=payload)
    assert response.status_code == 201
    assert response.get_json()["name"] == "<script>alert(1)</script>"

# ----------------------------------------------------------------------
# Additional tests for database error cases
# ----------------------------------------------------------------------

def test_database_error_on_create_returns_safe_error(client, monkeypatch):
    # Simulate a database failure during insert and ensure the app fails safely.
    import sqlite3

    def raise_db_error(*args, **kwargs):
        raise sqlite3.DatabaseError("simulated db failure")

    monkeypatch.setattr("sqlite3.connect", raise_db_error)
    response = client.post("/api/students", json=student())
    assert response.status_code == 500
    assert response.get_json() == {"error": "Database operation failed."}


def test_database_error_on_list_returns_safe_error(client, monkeypatch):
    # Simulate a database failure while listing students.
    import sqlite3

    def raise_db_error(*args, **kwargs):
        raise sqlite3.DatabaseError("simulated db failure")

    monkeypatch.setattr("sqlite3.connect", raise_db_error)
    response = client.get("/api/students")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Database operation failed."}


def test_database_error_on_update_returns_safe_error(client, monkeypatch):
    import sqlite3

    def raise_db_error(*args, **kwargs):
        raise sqlite3.DatabaseError("simulated db failure")

    monkeypatch.setattr("sqlite3.connect", raise_db_error)
    response = client.put("/api/students/1", json=student())

    assert response.status_code == 500
    assert response.get_json() == {"error": "Database operation failed."}


def test_database_error_on_delete_returns_safe_error(client, monkeypatch):
    import sqlite3

    def raise_db_error(*args, **kwargs):
        raise sqlite3.DatabaseError("simulated db failure")

    monkeypatch.setattr("sqlite3.connect", raise_db_error)
    response = client.delete("/api/students/1")

    assert response.status_code == 500
    assert response.get_json() == {"error": "Database operation failed."}


# ----------------------------------------------------------------------
# Student search and filter flow
# ----------------------------------------------------------------------

def test_create_rejects_missing_academic_year(client):
    payload = student()
    payload.pop("academic_year")
    response = client.post("/api/students", json=payload)
    assert response.status_code == 400
    assert "academic year" in response.get_json()["error"]


def test_create_rejects_invalid_academic_year(client):
    response = client.post("/api/students", json=student(academic_year=""))
    assert response.status_code == 400
    assert "academic year" in response.get_json()["error"]

    for academic_year in ["26", "abcd", "1999", "2101"]:
        response = client.post("/api/students", json=student(academic_year=academic_year))
        assert response.status_code == 400
        assert "Academic year" in response.get_json()["error"]


def test_filter_by_department(client):
    client.post("/api/students", json=student(roll_number="IT001", department="Information Technology"))
    client.post("/api/students", json=student(roll_number="CS101", department="Computer Science", email="other@example.com"))

    response = client.get("/api/students?department=computer%20science")
    assert response.status_code == 200
    results = response.get_json()
    assert len(results) == 1
    assert results[0]["department"] == "Computer Science"


def test_filter_by_academic_year(client):
    client.post("/api/students", json=student(roll_number="IT001", academic_year="2025"))
    client.post("/api/students", json=student(roll_number="IT002", academic_year="2026", email="other@example.com"))

    response = client.get("/api/students?academic_year=2025")
    assert response.status_code == 200
    results = response.get_json()
    assert len(results) == 1
    assert results[0]["academic_year"] == "2025"


def test_combined_name_department_and_academic_year_filter(client):
    client.post(
        "/api/students",
        json=student(
            name="Asha Kumar",
            roll_number="IT001",
            department="Information Technology",
            academic_year="2026",
        ),
    )
    client.post(
        "/api/students",
        json=student(
            name="Asha Rao",
            roll_number="IT002",
            department="Computer Science",
            academic_year="2026",
            email="asha.rao@example.com",
        ),
    )

    response = client.get(
        "/api/students?q=asha&department=Information%20Technology&academic_year=2026"
    )
    assert response.status_code == 200
    results = response.get_json()
    assert len(results) == 1
    assert results[0]["name"] == "Asha Kumar"


def test_combined_filters_return_empty_list(client):
    client.post("/api/students", json=student())
    response = client.get(
        "/api/students?q=unknown&department=Unknown&academic_year=2026"
    )
    assert response.status_code == 200
    assert response.get_json() == []


def test_existing_database_is_migrated_without_losing_students(tmp_path):
    import sqlite3

    database = tmp_path / "existing.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("""CREATE TABLE students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        connection.execute(
            "INSERT INTO students(name, roll_number, department, email) VALUES(?, ?, ?, ?)",
            ("Asha Kumar", "IT001", "Information Technology", "asha@example.com"),
        )

    app = create_app({
        "TESTING": True,
        "DATABASE": str(database),
        "SECRET_KEY": "test-secret-key-for-session-signing",
        "ADMIN_USERNAME": "test-admin",
        "ADMIN_PASSWORD_HASH": TEST_PASSWORD_HASH,
    })
    with app.test_client() as client:
        sign_in(client)
        response = client.get("/api/students")

    assert response.status_code == 200
    records = response.get_json()
    assert len(records) == 1
    assert records[0]["name"] == "Asha Kumar"
    assert records[0]["academic_year"] == ""

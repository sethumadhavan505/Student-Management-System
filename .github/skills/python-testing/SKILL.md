---
name: python-testing
description: Guides inspection, writing, execution, and debugging of pytest tests for this Flask and SQLite application. Use when adding or changing Python tests, validating API behavior, or diagnosing pytest failures.
---

# Python Testing for Student Management System

Use this skill when creating or updating Python tests, checking Flask endpoints, testing validation or SQLite persistence, or investigating pytest failures.

## Inspect the existing test structure

1. Start with `tests/` and read the test module related to the behavior.
2. Check for `conftest.py`, pytest configuration, and test commands in `README.md` or `requirements.txt` before assuming they exist.
3. This repository currently keeps its `client` fixture and `student()` payload helper in `tests/test_app.py`; there is no shared `conftest.py` or frontend test runner in the project root.
4. Read the relevant route in `app.py` and the corresponding UI/API behavior before writing assertions.
5. Keep tests focused on observable behavior rather than duplicating implementation details.

## Write pytest tests

- Name tests `test_<behavior>_<condition>` and keep each test focused.
- Reuse the existing `client` fixture and `student()` helper when appropriate.
- The fixture builds an app with `TESTING=True` and a database under pytest's `tmp_path`. Use isolated temporary databases; do not use or alter the checked-in `students.db`.
- Use `client.get`, `client.post(..., json=...)`, `client.put(..., json=...)`, and `client.delete(...)` for API tests.
- Assert the HTTP status, response JSON shape/content, and database effects when persistence is part of the behavior.
- Keep test data synthetic. Provide distinct roll numbers and email addresses when creating multiple students because those fields are unique.

## Reuse fixtures correctly

- Prefer the existing fixture over manually starting a server or opening the production database.
- Let pytest manage `tmp_path`; avoid shared mutable test data or fixed database filenames.
- If adding a fixture, first confirm that existing setup cannot be reused. Keep fixture scope as narrow as practical so tests remain isolated.
- Use `monkeypatch` for controlled failures, following the existing database-error tests, and restore patched behavior through pytest's fixture lifecycle.

## Test API endpoints

For each changed route, cover the relevant success response and contract:

- `GET /api/students`: list, query filters, ordering, and no-match results.
- `POST /api/students`: creation, validation failures, duplicates, and response fields.
- `PUT /api/students/<id>`: successful update, invalid data, duplicate values, and missing IDs.
- `DELETE /api/students/<id>`: successful removal and missing IDs.

Check that query parameters are safely handled and that database changes persist only when expected. Preserve the established JSON error shape and status codes when extending an endpoint.

## Test invalid and edge-case inputs

Choose cases relevant to the changed behavior, such as:

- Missing fields, empty strings, whitespace-only values, and wrong JSON shapes.
- Invalid email/year formats and values just below or above length/range limits.
- Duplicate unique fields, including case variations for email.
- Unknown record IDs, empty search/filter results, and special characters in search text.
- Existing SQLite schemas that need migration, if schema behavior changes.
- Simulated database failures when adding or changing database error handling.

Assert that invalid operations return an appropriate error and do not leave partial or unintended database changes. Avoid tests that only restate constants or trivial implementation details.

## Run the tests

From the repository root, run the complete suite:

```powershell
python -m pytest -q
```

During iteration, run a focused test, for example:

```powershell
python -m pytest tests/test_app.py -q -k filter
```

Use the project dependencies from `requirements.txt`. Do not install packages or change dependency files unless required and authorized.

## Investigate failures

1. Read the first failing assertion and complete traceback.
2. Re-run the failing test alone to determine whether it is isolated or order-dependent.
3. Check fixture setup, test-data uniqueness, route status/JSON behavior, and the temporary database schema.
4. Compare the failure to the intended API contract and existing tests.
5. Fix the underlying cause; do not weaken a meaningful assertion or delete unrelated tests just to obtain a green run.
6. Re-run the focused test, then the full suite.

If failure is caused by a missing environment dependency or an external condition, report it explicitly rather than claiming success.

## Report test results

State the exact command, pass/fail/skip counts, and any relevant environment limitation. Distinguish tests that were actually executed from tests that were only added or inspected. Do not claim a suite passed if the command failed or did not run.

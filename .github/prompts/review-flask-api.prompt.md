---
name: review-flask-api
description: Perform a read-only review of the Student Management System Flask API for correctness, security, validation, and test coverage.
argument-hint: [route, function, or file to review]
agent: ask
---

Review the Flask API in this repository.

Target: ${input:target:optional route, function, or file path}

Follow the repository rules in `.github/copilot-instructions.md`.

1. Inspect the relevant implementation in `app.py` and the related tests in `tests/test_app.py`.
2. Trace each relevant request from input parsing through validation, database access, and response generation.
3. Check authentication and authorization, CSRF protection, SQL parameterization, input validation, uniqueness conflicts, transaction handling, error responses, and sensitive-data exposure. Verify each control in the source; do not assume it exists.
4. Identify missing or weak regression tests.
5. Return findings grouped by Critical, High, Medium, and Low priority. For each finding, include the exact file and function (and line numbers when available), evidence, impact, and a recommended fix.
6. Distinguish confirmed defects from risks or questions that need verification.
7. Do not edit files, run destructive commands, or claim tests were run unless they were actually executed.

---
name: flask-api-review
description: Review the Student Management System Flask API and its pytest coverage for security, correctness, validation, SQLite transaction handling, and error-response risks. Use when asked to audit, review, or assess Flask API routes or database mutations in this repository.
---

# Flask API Review Skill

## Purpose

Perform a careful, evidence-based, read-only review of the Flask API and its tests in this repository.

## Repository context

- Flask application and API routes are in `app.py`.
- SQLite persistence uses Python's `sqlite3`.
- API tests are in `tests/test_app.py`.
- The repository's architecture, API contracts, and coding rules are documented in `.github/copilot-instructions.md`.

Read the relevant project instructions before reviewing. Do not assume that the static GitHub Pages demo shares the Flask database.

## Workflow

1. **Scope the review**
   - Identify the requested route, function, or behavior.
   - If the request is broad, inspect all Flask API routes and their related helpers.
   - Read the corresponding tests before forming conclusions.

2. **Trace the implementation**
   - Follow request parsing, validation, database operations, transaction behavior, and response generation.
   - Check both success and failure paths.
   - Confirm that SQL uses placeholders for user-controlled values.

3. **Check security and correctness**
   - Authentication and authorization for sensitive or mutating operations.
   - CSRF protection where browser sessions and state-changing requests are involved.
   - Required fields, types, formats, length limits, and boundary values.
   - Case-insensitive uniqueness behavior for email and uniqueness for roll numbers.
   - Commit and rollback behavior after database failures.
   - Stable HTTP status codes and JSON response shapes.
   - Avoidance of SQL details, stack traces, secrets, and student personal data in client-facing errors.
   - Do not state that authentication, authorization, or CSRF exists unless the current code demonstrates it.

4. **Assess test coverage**
   - Map each finding to an existing test or a missing regression test.
   - Consider invalid input, boundary values, duplicate records, missing records, database exceptions, and post-failure database usability.
   - Do not rely on or modify the checked-in `students.db`.

5. **Report evidence**
   - Group findings by Critical, High, Medium, and Low priority.
   - For every finding, provide the file, function, line number when available, concrete code evidence, impact, and recommended fix.
   - Separate confirmed defects from potential risks and items that could not be verified.
   - Report test commands and outcomes only when they were actually run.

## Safety boundaries

- Default to read-only analysis. Do not edit files, commit, push, delete data, or run destructive commands as part of a review.
- If asked to implement a fix, first describe the proposed change and affected files. Wait for approval before editing.
- Never add real student information, credentials, API keys, or tokens to source, tests, or logs.
- Preserve current API contracts unless the requested task explicitly changes them.

## Expected output

1. Review scope.
2. Prioritized findings with evidence.
3. Missing or recommended regression tests.
4. Unverified questions or limitations.
5. A concise overall assessment.

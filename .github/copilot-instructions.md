# Student Management System: Copilot Instructions

## Project overview and architecture

This repository is a small student-record management application with two frontends:

- `app.py` is the Flask application factory, API, and SQLite persistence layer.
- `templates/index.html` is the server-rendered Flask dashboard. Its `data-storage="api"` setting makes `static/js/app.js` call Flask endpoints.
- Root `index.html` is the static GitHub Pages dashboard. Its `data-storage="local"` setting makes the same JavaScript use browser `localStorage`; it does not share data with the Flask database.
- `static/js/app.js` implements form handling, search and filters, CSV export, rendering, and the browser-storage adapter.
- `static/css/style.css` contains shared responsive styles.
- `tests/test_app.py` contains pytest tests using Flask's test client and temporary SQLite databases.
- `.github/workflows/pages.yml` deploys the static site from the repository root.

Preserve both frontend modes when changing shared HTML or JavaScript. Keep the two entry-point pages functionally consistent unless a change intentionally applies to only one mode.

## Technology stack

- Python 3.10 or newer (per `README.md`)
- Flask 3.x and Python's built-in `sqlite3`
- SQLite for the Flask application; browser `localStorage` for the static demo
- Server-rendered HTML, CSS, and vanilla JavaScript; there is no frontend framework, package manifest, or build step
- pytest 8.x
- GitHub Actions for GitHub Pages deployment

Use the versions and commands in `requirements.txt` and `README.md`. Do not add a dependency or build system when the existing stack can meet the requirement.

## Python conventions

- Follow PEP 8: four-space indentation, descriptive `snake_case` names, and readable, focused functions.
- Keep Flask setup in `create_app(test_config=None)` and make new behavior configurable/testable through the app configuration where appropriate.
- Use the existing request-scoped SQLite connection pattern (`g`, `sqlite3.Row`, and `teardown_appcontext`) rather than opening unmanaged connections.
- Keep route handlers and validation aligned with existing API response shapes and status codes.
- Add type hints for new public or non-trivial helpers when useful; avoid unnecessary abstractions for this small application.

## Frontend standards

- Use the existing vanilla JavaScript, DOM APIs, `fetch`, `URLSearchParams`, and shared helpers; do not introduce a framework.
- Respect `body[data-storage]` so API-backed Flask mode and browser-storage mode continue to work.
- Use semantic HTML, associated labels, keyboard-operable controls, visible focus states, and appropriate live regions.
- Escape untrusted values before inserting them into HTML. Prefer `textContent` when markup is unnecessary.
- Keep the root `index.html` and `templates/index.html` aligned for shared UI changes.
- Preserve responsive behavior in `static/css/style.css`.

## Database and API guidelines

- The `students` table stores `id`, `name`, `roll_number`, `department`, `academic_year`, `email`, and `created_at`; roll number and email are unique, with email uniqueness case-insensitive.
- Existing records may be upgraded at application startup. Make schema changes additive and non-destructive; preserve existing records and provide a safe migration path.
- Use SQL placeholders for all user-controlled values. Never interpolate request data into SQL.
- Preserve the existing routes and JSON contracts:
  - `GET /api/students` supports `q`, `department`, and `academic_year`.
  - `POST /api/students` creates a student.
  - `PUT /api/students/<id>` updates a student.
  - `DELETE /api/students/<id>` deletes a student.
- Validate inputs on the server even when the browser also validates them. Keep browser-storage validation behavior consistent with the Flask API.
- Do not assume GitHub Pages can access Flask or SQLite; its records remain local to each browser.

## Testing requirements

- Add or update pytest coverage for every behavior change, including invalid input, boundary values, empty results, and persistence or migration effects where relevant.
- Reuse the `client` fixture and `student()` helper in `tests/test_app.py` when appropriate. The fixture uses `tmp_path` for an isolated SQLite database. Inspect for an existing fixture before introducing another one; this repository currently defines its fixture in `tests/test_app.py`, not `conftest.py`.
- Test API status codes, JSON response bodies, and relevant database effects. Keep tests independent of the checked-in `students.db`.
- Run the smallest relevant test during iteration, then run the full suite with `python -m pytest -q` before reporting completion.
- Report the exact command and outcome. Do not claim a test passed unless it was run.

## Security practices

- Treat names, emails, search terms, and other student data as sensitive personal information. Never add real student data, credentials, or tokens to source, tests, logs, or the public demo.
- Keep secrets out of code and Git. The current secret-key value is a development placeholder; do not represent it as production-safe.
- Use parameterized SQL, server-side validation, and HTML escaping. Do not weaken these safeguards to make a test pass.
- The Flask development server uses `debug=True` when run directly. Do not use debug mode for production.
- Authentication, authorization, and CSRF protections are not established by this starter. Do not imply they exist; flag them when changes affect deployment or sensitive operations.

## Error handling

- Return explicit, stable API errors for expected invalid input, missing records, uniqueness conflicts, and database failures, following existing response conventions.
- Do not expose SQL, stack traces, secrets, or personal data in client-facing errors.
- Catch specific exceptions where recovery is appropriate. Do not use broad catches or silently convert failures into successful responses.
- Surface browser, network, JSON parsing, and storage errors to the existing UI message or result state.

## Documentation standards

- Update `README.md` when API behavior, setup, dependencies, storage behavior, or user-facing workflows change.
- Keep examples accurate, minimal, and free of real personal information or secrets.
- Use repository-relative paths in project documentation and clearly distinguish Flask/SQLite behavior from the static browser-storage demo.

## Git and pull request conventions

- Work on a feature branch; do not commit directly to `main`.
- Inspect `git status` and the diff before staging. Stage only task-related files and preserve unrelated user changes.
- Do not commit or push unless explicitly requested. Never force-push.
- Use a concise, descriptive commit subject. A pull request should summarize the change, list meaningful validation commands/results, and disclose known limitations.

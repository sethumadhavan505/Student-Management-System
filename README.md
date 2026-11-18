# Student Management System

A responsive student-record management starter built with **Python, Flask, SQLite, HTML, CSS, and JavaScript**.

## Features
- Add, view, search, update, and delete student records (CRUD)
- Required-field and email-format validation
- Unique roll numbers and email addresses
- SQLite database created automatically on first Flask run
- GitHub Pages demo with browser-local storage
- Responsive desktop/mobile dashboard
- Pytest API tests

## GitHub Pages

The static demo is deployed from the repository root by the GitHub Actions
workflow in `.github/workflows/pages.yml`. In the repository settings, open
**Pages** and set the build and deployment source to **GitHub Actions**. Each
push to `main` then publishes the site at:

https://sethumadhavan505.github.io/Student-Management-System/

GitHub Pages cannot run Flask or SQLite. The Pages version saves records in
the current browser only; records are not shared across visitors or with the
local Flask application. Do not enter real or sensitive student information.
The full Flask and SQLite version remains available for local use below.

## Project structure
```text
Student-Management-System/
├── app.py
├── index.html
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── index.html
│   └── login.html
├── static/css/style.css
├── static/js/app.js
├── .github/workflows/pages.yml
└── tests/test_app.py
```

## Run locally on Windows
1. Install Python 3.10 or newer.
2. Clone and enter the repository:
   ```powershell
   git clone https://github.com/sethumadhavan505/Student-Management-System.git
   cd Student-Management-System
   ```
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, use Command Prompt: `.venv\Scripts\activate.bat`.
4. Configure the single administrator account and run:
   ```powershell
   python -m pip install -r requirements.txt
   $env:STUDENT_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
   $env:STUDENT_ADMIN_USERNAME = "admin"
   $env:STUDENT_ADMIN_PASSWORD_HASH = python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass()))"
   python app.py
   ```
   The password prompt will not echo the password. Keep these environment
   variables private and set them in the hosting environment for WSGI
   deployments. Use a secret key at least 32 characters long. The Flask app
   refuses to start directly if the required credentials are missing or the
   secret key is too short. For HTTPS deployments, set
   `$env:STUDENT_COOKIE_SECURE = "1"` before starting the application.
5. Open http://127.0.0.1:5000 and sign in with the configured credentials.

The `students.db` SQLite file is generated on first run.

## Run tests
```powershell
python -m pytest -q
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/students?q=...` | List/search students |
| GET | `/api/students/summary` | Return student and department counts |
| POST | `/api/students` | Create a student |
| PUT | `/api/students/<id>` | Update a student |
| DELETE | `/api/students/<id>` | Delete a student |

Example JSON:
```json
{"name":"Asha Kumar","roll_number":"IT001","department":"Information Technology","academic_year":"2026","email":"asha@example.com"}
```

The Flask dashboard and API require the configured administrator session.
State-changing requests also require a CSRF token; the browser dashboard
supplies it automatically. GitHub Pages remains a separate browser-local demo
and does not use this login or share records with Flask.

## Production considerations
This is a learning/demo starter, not production-ready student information software. The Flask version provides a single administrator login, but does not provide multiple users, roles, account recovery, or login rate limiting. Use HTTPS, secure secret management, restricted network access, migrations, backups, monitoring, and a production WSGI server before deployment. Do not use real student personal data in a public demo.

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
├── templates/index.html
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
4. Install and run:
   ```powershell
   python -m pip install -r requirements.txt
   python app.py
   ```
5. Open http://127.0.0.1:5000.

The `students.db` SQLite file is generated on first run.

## Run tests
```powershell
python -m pytest -q
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/students?q=...` | List/search students |
| POST | `/api/students` | Create a student |
| PUT | `/api/students/<id>` | Update a student |
| DELETE | `/api/students/<id>` | Delete a student |

Example JSON:
```json
{"name":"Asha Kumar","roll_number":"IT001","department":"Information Technology","email":"asha@example.com"}
```

## Production considerations
This is a learning/demo starter, not production-ready student information software. Before production, add authentication and role-based authorization, CSRF protection, secure secret management, migrations, backups, logging, and deployment configuration. Do not use real student personal data in a public demo.

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template, request, g

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "students.db"

def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(DATABASE=str(DATABASE), TESTING=False, SECRET_KEY="change-this-before-production")
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        get_db().execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT NOT NULL UNIQUE,
                department TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        get_db().commit()

    with app.app_context():
        init_db()

    def validate_student(data: dict, student_id=None):
        keys = ("name", "roll_number", "department", "email")
        cleaned = {key: str(data.get(key, "")).strip() for key in keys}
        missing = [key for key, value in cleaned.items() if not value]
        if missing:
            return None, f"Please provide: {', '.join(missing)}."
        if len(cleaned["name"]) > 100 or len(cleaned["department"]) > 100:
            return None, "Name and department must be 100 characters or fewer."
        if len(cleaned["roll_number"]) > 30:
            return None, "Roll number must be 30 characters or fewer."
        if not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", cleaned["email"]):
            return None, "Enter a valid email address."
        duplicate = get_db().execute(
            "SELECT id FROM students WHERE (roll_number = ? OR email = ?) AND id != ?",
            (cleaned["roll_number"], cleaned["email"], student_id or -1),
        ).fetchone()
        if duplicate:
            return None, "A student with this roll number or email already exists."
        return cleaned, None

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/students")
    def list_students():
        query = request.args.get("q", "").strip()
        rows = get_db().execute("""
            SELECT id, name, roll_number, department, email, created_at
            FROM students
            WHERE name LIKE ? OR roll_number LIKE ? OR department LIKE ? OR email LIKE ?
            ORDER BY id DESC
        """, tuple([f"%{query}%"] * 4)).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post("/api/students")
    def create_student():
        cleaned, error = validate_student(request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400
        try:
            cursor = get_db().execute(
                "INSERT INTO students (name, roll_number, department, email) VALUES (?, ?, ?, ?)",
                (cleaned["name"], cleaned["roll_number"], cleaned["department"], cleaned["email"]),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Roll number and email must be unique."}), 409
        row = get_db().execute("SELECT * FROM students WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201

    @app.put("/api/students/<int:student_id>")
    def update_student(student_id):
        if not get_db().execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone():
            return jsonify({"error": "Student not found."}), 404
        cleaned, error = validate_student(request.get_json(silent=True) or {}, student_id)
        if error:
            return jsonify({"error": error}), 400
        try:
            get_db().execute(
                "UPDATE students SET name=?, roll_number=?, department=?, email=? WHERE id=?",
                (cleaned["name"], cleaned["roll_number"], cleaned["department"], cleaned["email"], student_id),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Roll number and email must be unique."}), 409
        row = get_db().execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return jsonify(dict(row))

    @app.delete("/api/students/<int:student_id>")
    def delete_student(student_id):
        cursor = get_db().execute("DELETE FROM students WHERE id = ?", (student_id,))
        get_db().commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Student not found."}), 404
        return jsonify({"message": "Student deleted successfully."})

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

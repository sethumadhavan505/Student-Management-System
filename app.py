from __future__ import annotations
import hmac
import os
import re
import secrets
import sqlite3
from pathlib import Path
from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "students.db"
SEARCHABLE_FIELDS = ("name", "roll_number", "department", "email")
MAX_NAME_LENGTH = 100
MAX_DEPARTMENT_LENGTH = 100
MAX_ROLL_NUMBER_LENGTH = 30
MIN_ACADEMIC_YEAR = 2000
MAX_ACADEMIC_YEAR = 2100
EMAIL_PATTERN = (
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
)


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.update(
        DATABASE=str(DATABASE),
        TESTING=False,
        SECRET_KEY=os.environ.get("STUDENT_SECRET_KEY"),
        ADMIN_USERNAME=os.environ.get("STUDENT_ADMIN_USERNAME"),
        ADMIN_PASSWORD_HASH=os.environ.get("STUDENT_ADMIN_PASSWORD_HASH"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("STUDENT_COOKIE_SECURE", "").lower()
        in {"1", "true", "yes"},
    )
    if test_config:
        app.config.update(test_config)

    def authentication_is_configured():
        secret_key = app.config.get("SECRET_KEY")
        return (
            isinstance(secret_key, str)
            and len(secret_key) >= 32
            and isinstance(app.config.get("ADMIN_USERNAME"), str)
            and bool(app.config["ADMIN_USERNAME"])
            and isinstance(app.config.get("ADMIN_PASSWORD_HASH"), str)
            and bool(app.config["ADMIN_PASSWORD_HASH"])
        )

    def csrf_token():
        token = session.get("csrf_token")
        if token is None:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def csrf_is_valid(token):
        expected = session.get("csrf_token", "")
        return bool(expected) and hmac.compare_digest(
            (token or "").encode("utf-8"),
            expected.encode("utf-8"),
        )

    def rollback_db():
        connection = g.get("db")
        if connection is not None:
            try:
                connection.rollback()
            except sqlite3.DatabaseError:
                app.logger.exception("Failed to roll back a database transaction.")

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db
    @app.teardown_appcontext
    def close_db(_error=None):
        conn = g.pop("db", None)
        if conn is not None: conn.close()
    with app.app_context():
        db().execute("""CREATE TABLE IF NOT EXISTS students (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          roll_number TEXT NOT NULL UNIQUE, department TEXT NOT NULL,
          academic_year TEXT NOT NULL DEFAULT '',
          email TEXT NOT NULL COLLATE NOCASE UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        columns={row["name"] for row in db().execute("PRAGMA table_info(students)").fetchall()}
        if "academic_year" not in columns:
            db().execute("ALTER TABLE students ADD COLUMN academic_year TEXT NOT NULL DEFAULT ''")
        db().commit()
    def validate(data, current_id=None):
        if not isinstance(data, dict):
            return None, "Request body must be a JSON object."
        keys=("name","roll_number","department","academic_year","email")
        item={k:str(data.get(k,"")).strip() for k in keys}
        missing=[k for k,v in item.items() if not v]
        if missing:
            labels={
                "name":"name",
                "roll_number":"roll number",
                "department":"department",
                "academic_year":"academic year",
                "email":"email",
            }
            return None, f"Please provide: {', '.join(labels[key] for key in missing)}."
        if (
            len(item["name"]) > MAX_NAME_LENGTH
            or len(item["department"]) > MAX_DEPARTMENT_LENGTH
        ):
            return None,"Name and department must be 100 characters or fewer."
        if len(item["roll_number"]) > MAX_ROLL_NUMBER_LENGTH:
            return None,"Roll number must be 30 characters or fewer."
        if not re.fullmatch(r"(?:19|20|21)\d{2}",item["academic_year"]):
            return None,"Academic year must be a four-digit year."
        academic_year=int(item["academic_year"])
        if academic_year < MIN_ACADEMIC_YEAR or academic_year > MAX_ACADEMIC_YEAR:
            return None,"Academic year must be between 2000 and 2100."
        raw_email=data.get("email","")
        if (not isinstance(raw_email,str) or raw_email!=raw_email.strip()
            or not re.fullmatch(EMAIL_PATTERN,item["email"])):
            return None,"Enter a valid email address."
        duplicate=db().execute("SELECT id FROM students WHERE (roll_number=? OR email=?) AND id!=?",
          (item["roll_number"],item["email"],current_id or -1)).fetchone()
        if duplicate: return None,"A student with this roll number or email already exists."
        return item,None

    @app.before_request
    def protect_api():
        if not request.path.startswith("/api/"):
            return None
        if not authentication_is_configured():
            return jsonify({"error":"Authentication is not configured."}),503
        if not session.get("authenticated"):
            return jsonify({"error":"Authentication required."}),401
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if not csrf_is_valid(request.headers.get("X-CSRF-Token", "")):
                return jsonify({"error":"Invalid or missing CSRF token."}),400
        return None

    @app.get("/")
    def index():
        if not authentication_is_configured():
            return render_template(
                "login.html",
                csrf_token="",
                error="Authentication is not configured. Set the required environment variables.",
            ),503
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return render_template("index.html", csrf_token=csrf_token())

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not authentication_is_configured():
            return render_template(
                "login.html",
                csrf_token="",
                error="Authentication is not configured. Set the required environment variables.",
            ),503
        if session.get("authenticated"):
            return redirect(url_for("index"))
        token = csrf_token()
        if request.method == "GET":
            return render_template("login.html", csrf_token=token)
        if not csrf_is_valid(request.form.get("csrf_token", "")):
            return render_template(
                "login.html",
                csrf_token=token,
                error="Your login session expired. Please try again.",
            ),400
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        try:
            password_matches = check_password_hash(
                app.config["ADMIN_PASSWORD_HASH"], password
            )
        except ValueError:
            app.logger.error("Configured administrator password hash is invalid.")
            return render_template(
                "login.html",
                csrf_token=token,
                error="Authentication is unavailable. Check the server configuration.",
            ),503
        if not (
            hmac.compare_digest(
                username.encode("utf-8"),
                app.config["ADMIN_USERNAME"].encode("utf-8"),
            )
            and password_matches
        ):
            return render_template(
                "login.html",
                csrf_token=token,
                error="Invalid username or password.",
            ),401
        session.clear()
        session["authenticated"] = True
        session["csrf_token"] = secrets.token_urlsafe(32)
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        if not authentication_is_configured():
            return jsonify({"error":"Authentication is not configured."}),503
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        if not csrf_is_valid(request.form.get("csrf_token", "")):
            return jsonify({"error":"Invalid or missing CSRF token."}),400
        session.clear()
        return redirect(url_for("login"))

    @app.get("/api/students")
    def list_students():
        q=request.args.get("q","").strip()
        department=request.args.get("department","").strip()
        academic_year=request.args.get("academic_year","").strip()
        try:
            conditions=[]
            params=[]
            if q:
                conditions.append(
                    "("
                    + " OR ".join(
                        f"{field} LIKE ?" for field in SEARCHABLE_FIELDS
                    )
                    + ")"
                )
                params.extend([f"%{q}%"] * len(SEARCHABLE_FIELDS))
            if department:
                conditions.append("department COLLATE NOCASE = ?")
                params.append(department)
            if academic_year:
                conditions.append("academic_year = ?")
                params.append(academic_year)
            sql="""SELECT id,name,roll_number,department,academic_year,email,created_at FROM students"""
            if conditions:
                sql+=" WHERE "+" AND ".join(conditions)
            sql+=" ORDER BY id DESC"
            rows=db().execute(sql,params).fetchall()
        except sqlite3.DatabaseError:
            return jsonify({"error":"Database operation failed."}),500
        return jsonify([dict(r) for r in rows])

    @app.get("/api/students/summary")
    def student_summary():
        try:
            counts = db().execute(
                "SELECT COUNT(*) AS total_students, "
                "COUNT(DISTINCT department COLLATE NOCASE) AS department_count "
                "FROM students"
            ).fetchone()
            departments = db().execute(
                "SELECT DISTINCT department FROM students ORDER BY department COLLATE NOCASE"
            ).fetchall()
        except sqlite3.DatabaseError:
            return jsonify({"error":"Database operation failed."}),500
        return jsonify({
            "total_students": counts["total_students"],
            "department_count": counts["department_count"],
            "departments": [row["department"] for row in departments],
        })

    @app.post("/api/students")
    def create_student():
        try:
            item,error=validate(request.get_json(silent=True) or {})
            if error: return jsonify({"error":error}),400
            cur=db().execute("INSERT INTO students(name,roll_number,department,academic_year,email) VALUES(?,?,?,?,?)",
              (item["name"],item["roll_number"],item["department"],item["academic_year"],item["email"]))
            db().commit()
            row=db().execute("SELECT * FROM students WHERE id=?",(cur.lastrowid,)).fetchone()
        except sqlite3.IntegrityError: return jsonify({"error":"Roll number and email must be unique."}),409
        except sqlite3.DatabaseError:
            return jsonify({"error":"Database operation failed."}),500
        return jsonify(dict(row)),201
    @app.put("/api/students/<int:student_id>")
    def update_student(student_id):
        try:
            if not db().execute("SELECT id FROM students WHERE id=?",(student_id,)).fetchone():
                return jsonify({"error":"Student not found."}),404
            item,error=validate(request.get_json(silent=True) or {},student_id)
            if error: return jsonify({"error":error}),400
            db().execute("UPDATE students SET name=?,roll_number=?,department=?,academic_year=?,email=? WHERE id=?",
              (item["name"],item["roll_number"],item["department"],item["academic_year"],item["email"],student_id))
            db().commit()
            row=db().execute("SELECT * FROM students WHERE id=?",(student_id,)).fetchone()
        except sqlite3.IntegrityError:
            rollback_db()
            return jsonify({"error":"Roll number and email must be unique."}),409
        except sqlite3.DatabaseError:
            rollback_db()
            return jsonify({"error":"Database operation failed."}),500
        return jsonify(dict(row))

    @app.delete("/api/students/<int:student_id>")
    def delete_student(student_id):
        try:
            cur=db().execute("DELETE FROM students WHERE id=?",(student_id,))
            db().commit()
        except sqlite3.DatabaseError:
            rollback_db()
            return jsonify({"error":"Database operation failed."}),500
        if cur.rowcount==0: return jsonify({"error":"Student not found."}),404
        return jsonify({"message":"Student deleted successfully."})
    return app
app=create_app()
if __name__=="__main__":
    if (
        not all(app.config.get(key) for key in (
            "SECRET_KEY",
            "ADMIN_USERNAME",
            "ADMIN_PASSWORD_HASH",
        ))
        or len(app.config["SECRET_KEY"]) < 32
    ):
        raise RuntimeError(
            "Set STUDENT_SECRET_KEY, STUDENT_ADMIN_USERNAME, and "
            "STUDENT_ADMIN_PASSWORD_HASH, and use a secret key of at least "
            "32 characters before starting the Flask application."
        )
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"})

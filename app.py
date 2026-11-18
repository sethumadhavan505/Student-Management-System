from __future__ import annotations
import re, sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template, request, g

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "students.db"

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(DATABASE=str(DATABASE), TESTING=False, SECRET_KEY="change-this-before-production")
    if test_config: app.config.update(test_config)
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
        if len(item["name"])>100 or len(item["department"])>100: return None,"Name and department must be 100 characters or fewer."
        if len(item["roll_number"])>30: return None,"Roll number must be 30 characters or fewer."
        if not re.fullmatch(r"(?:19|20|21)\d{2}",item["academic_year"]):
            return None,"Academic year must be a four-digit year."
        academic_year=int(item["academic_year"])
        if academic_year<2000 or academic_year>2100:
            return None,"Academic year must be between 2000 and 2100."
        raw_email=data.get("email","")
        email_pattern=r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
        if (not isinstance(raw_email,str) or raw_email!=raw_email.strip()
            or not re.fullmatch(email_pattern,item["email"])):
            return None,"Enter a valid email address."
        duplicate=db().execute("SELECT id FROM students WHERE (roll_number=? OR email=?) AND id!=?",
          (item["roll_number"],item["email"],current_id or -1)).fetchone()
        if duplicate: return None,"A student with this roll number or email already exists."
        return item,None
    @app.get("/")
    def index(): return render_template("index.html")
    @app.get("/api/students")
    def list_students():
        q=request.args.get("q","").strip()
        department=request.args.get("department","").strip()
        academic_year=request.args.get("academic_year","").strip()
        try:
            conditions=[]
            params=[]
            if q:
                conditions.append("(name LIKE ? OR roll_number LIKE ? OR department LIKE ? OR email LIKE ?)")
                params.extend([f"%{q}%"]*4)
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
        if not db().execute("SELECT id FROM students WHERE id=?",(student_id,)).fetchone():
            return jsonify({"error":"Student not found."}),404
        item,error=validate(request.get_json(silent=True) or {},student_id)
        if error: return jsonify({"error":error}),400
        try:
            db().execute("UPDATE students SET name=?,roll_number=?,department=?,academic_year=?,email=? WHERE id=?",
              (item["name"],item["roll_number"],item["department"],item["academic_year"],item["email"],student_id))
            db().commit()
        except sqlite3.IntegrityError: return jsonify({"error":"Roll number and email must be unique."}),409
        return jsonify(dict(db().execute("SELECT * FROM students WHERE id=?",(student_id,)).fetchone()))
    @app.delete("/api/students/<int:student_id>")
    def delete_student(student_id):
        cur=db().execute("DELETE FROM students WHERE id=?",(student_id,)); db().commit()
        if cur.rowcount==0: return jsonify({"error":"Student not found."}),404
        return jsonify({"message":"Student deleted successfully."})
    return app
app=create_app()
if __name__=="__main__": app.run(debug=True)

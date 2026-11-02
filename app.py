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
          email TEXT NOT NULL COLLATE NOCASE UNIQUE,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        db().commit()
    def validate(data, current_id=None):
        keys=("name","roll_number","department","email")
        item={k:str(data.get(k,"")).strip() for k in keys}
        missing=[k for k,v in item.items() if not v]
        if missing: return None, f"Please provide: {', '.join(missing)}."
        if len(item["name"])>100 or len(item["department"])>100: return None,"Name and department must be 100 characters or fewer."
        if len(item["roll_number"])>30: return None,"Roll number must be 30 characters or fewer."
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",item["email"]): return None,"Enter a valid email address."
        duplicate=db().execute("SELECT id FROM students WHERE (roll_number=? OR email=?) AND id!=?",
          (item["roll_number"],item["email"],current_id or -1)).fetchone()
        if duplicate: return None,"A student with this roll number or email already exists."
        return item,None
    @app.get("/")
    def index(): return render_template("index.html")
    @app.get("/api/students")
    def list_students():
        q=request.args.get("q","").strip()
        rows=db().execute("""SELECT id,name,roll_number,department,email,created_at FROM students
          WHERE name LIKE ? OR roll_number LIKE ? OR department LIKE ? OR email LIKE ? ORDER BY id DESC""",
          tuple([f"%{q}%"]*4)).fetchall()
        return jsonify([dict(r) for r in rows])
    @app.post("/api/students")
    def create_student():
        item,error=validate(request.get_json(silent=True) or {})
        if error: return jsonify({"error":error}),400
        try:
            cur=db().execute("INSERT INTO students(name,roll_number,department,email) VALUES(?,?,?,?)",
              (item["name"],item["roll_number"],item["department"],item["email"]))
            db().commit()
        except sqlite3.IntegrityError: return jsonify({"error":"Roll number and email must be unique."}),409
        return jsonify(dict(db().execute("SELECT * FROM students WHERE id=?",(cur.lastrowid,)).fetchone())),201
    @app.put("/api/students/<int:student_id>")
    def update_student(student_id):
        if not db().execute("SELECT id FROM students WHERE id=?",(student_id,)).fetchone():
            return jsonify({"error":"Student not found."}),404
        item,error=validate(request.get_json(silent=True) or {},student_id)
        if error: return jsonify({"error":error}),400
        try:
            db().execute("UPDATE students SET name=?,roll_number=?,department=?,email=? WHERE id=?",
              (item["name"],item["roll_number"],item["department"],item["email"],student_id))
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

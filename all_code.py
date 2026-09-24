import sqlite3
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    route,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================


def connect():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================


def init_db():
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rollno TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                course TEXT NOT NULL,
                photo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = con.execute("PRAGMA table_info(students)").fetchall()
        column_names = [column["name"] for column in columns]

        if "photo" not in column_names:
            con.execute("ALTER TABLE students ADD COLUMN photo TEXT")

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL UNIQUE,
                total_classes INTEGER NOT NULL DEFAULT 0,
                attended_classes INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                marks REAL NOT NULL DEFAULT 0,
                max_marks REAL NOT NULL DEFAULT 100,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
                student_id INTEGER,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )


# ============================================================
# USER FUNCTIONS
# ============================================================


def create_user(username, password_hash, role, student_id=None):
    username = str(username).strip()
    role = str(role).strip().lower()

    if not username:
        raise ValueError("Username is required.")

    if not password_hash:
        raise ValueError("Password is required.")

    if role not in ("admin", "teacher", "student"):
        raise ValueError("Invalid user role.")

    try:
        with connect() as con:
            cursor = con.execute(
                """
                INSERT INTO users (username, password_hash, role, student_id)
                VALUES (?, ?, ?, ?)
                """,
                (username, password_hash, role, student_id),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        if "username" in str(exc).lower():
            raise ValueError("Username already exists.")
        raise ValueError("Unable to create user.")



def get_user_by_username(username):
    username = str(username).strip()
    with connect() as con:
        return con.execute(
            """
            SELECT id, username, password_hash, role, student_id
            FROM users
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()



def get_user_by_id(user_id):
    with connect() as con:
        return con.execute(
            """
            SELECT id, username, password_hash, role, student_id
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()



def get_users():
    with connect() as con:
        return con.execute(
            """
            SELECT id, username, role, student_id
            FROM users
            ORDER BY id DESC
            """
        ).fetchall()



def delete_user(user_id):
    with connect() as con:
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ============================================================
# STUDENT CRUD FUNCTIONS
# ============================================================


def add_student(rollno, name, email, course, photo=None):
    try:
        with connect() as con:
            cursor = con.execute(
                """
                INSERT INTO students (rollno, name, email, course, photo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rollno, name, email, course, photo),
            )
            student_id = cursor.lastrowid

            con.execute(
                """
                INSERT INTO attendance (student_id, total_classes, attended_classes)
                VALUES (?, 0, 0)
                """,
                (student_id,),
            )

            return student_id

    except sqlite3.IntegrityError as exc:
        if "rollno" in str(exc).lower():
            raise ValueError("Roll number already exists.")
        raise ValueError("Unable to add student.")



def get_students(query=""):
    q = f"%{query.strip()}%"

    with connect() as con:
        if query:
            return con.execute(
                """
                SELECT *
                FROM students
                WHERE rollno LIKE ?
                   OR name LIKE ?
                   OR email LIKE ?
                   OR course LIKE ?
                ORDER BY id DESC
                """,
                (q, q, q, q),
            ).fetchall()

        return con.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()



def get_student(student_id):
    with connect() as con:
        return con.execute(
            "SELECT * FROM students WHERE id = ? LIMIT 1",
            (student_id,),
        ).fetchone()



def update_student(student_id, name, email, course, photo=None):
    with connect() as con:
        if photo is not None:
            con.execute(
                """
                UPDATE students
                SET name = ?, email = ?, course = ?, photo = ?
                WHERE id = ?
                """,
                (name, email, course, photo, student_id),
            )
        else:
            con.execute(
                """
                UPDATE students
                SET name = ?, email = ?, course = ?
                WHERE id = ?
                """,
                (name, email, course, student_id),
            )



def delete_student(student_id):
    with connect() as con:
        con.execute("DELETE FROM students WHERE id = ?", (student_id,))


# ============================================================
# ATTENDANCE FUNCTIONS
# ============================================================


def get_attendance(student_id):
    with connect() as con:
        row = con.execute(
            """
            SELECT total_classes, attended_classes
            FROM attendance
            WHERE student_id = ?
            LIMIT 1
            """,
            (student_id,),
        ).fetchone()

        if row is None:
            return {"total_classes": 0, "attended_classes": 0, "percentage": 0}

        total = int(row["total_classes"])
        attended = int(row["attended_classes"])
        percentage = round((attended / total) * 100, 2) if total > 0 else 0

        return {
            "total_classes": total,
            "attended_classes": attended,
            "percentage": percentage,
        }



def update_attendance(student_id, total_classes, attended_classes):
    try:
        total = int(total_classes)
        attended = int(attended_classes)
    except (TypeError, ValueError):
        raise ValueError("Attendance values must be numeric.")

    if total < 0 or attended < 0:
        raise ValueError("Attendance values cannot be negative.")

    if attended > total:
        raise ValueError("Attended classes cannot be more than total classes.")

    with connect() as con:
        con.execute(
            """
            UPDATE attendance
            SET total_classes = ?, attended_classes = ?
            WHERE student_id = ?
            """,
            (total, attended, student_id),
        )


# ============================================================
# RESULTS FUNCTIONS
# ============================================================


def get_results(student_id):
    with connect() as con:
        return con.execute(
            """
            SELECT *
            FROM results
            WHERE student_id = ?
            ORDER BY id DESC
            """,
            (student_id,),
        ).fetchall()



def add_result(student_id, subject, marks, max_marks):
    subject = str(subject).strip()
    try:
        marks_value = float(marks)
        max_value = float(max_marks)
    except (TypeError, ValueError):
        raise ValueError("Marks must be numeric.")

    if not subject:
        raise ValueError("Subject is required.")

    if max_value <= 0:
        raise ValueError("Maximum marks must be greater than zero.")

    if marks_value < 0 or marks_value > max_value:
        raise ValueError("Marks must be between 0 and maximum marks.")

    with connect() as con:
        con.execute(
            """
            INSERT INTO results (student_id, subject, marks, max_marks)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, subject, marks_value, max_value),
        )



def delete_result(result_id):
    with connect() as con:
        con.execute("DELETE FROM results WHERE id = ?", (result_id,))



def get_result_summary(student_id):
    with connect() as con:
        row = con.execute(
            """
            SELECT COUNT(*) AS total_subjects,
                   AVG(marks) AS average_marks,
                   MAX(marks) AS highest_marks,
                   MIN(marks) AS lowest_marks
            FROM results
            WHERE student_id = ?
            """,
            (student_id,),
        ).fetchone()

        if row is None or row["total_subjects"] == 0:
            return {
                "total_subjects": 0,
                "average_marks": 0,
                "highest_marks": 0,
                "lowest_marks": 0,
            }

        return {
            "total_subjects": int(row["total_subjects"]),
            "average_marks": round(float(row["average_marks"] or 0), 2),
            "highest_marks": float(row["highest_marks"] or 0),
            "lowest_marks": float(row["lowest_marks"] or 0),
        }


# ============================================================
# DASHBOARD REPORTS
# ============================================================


def get_dashboard_stats():
    with connect() as con:
        student_count = con.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]

        attendance_data = con.execute(
            "SELECT SUM(total_classes) AS total, SUM(attended_classes) AS attended FROM attendance"
        ).fetchone()

        total_classes = attendance_data["total"] or 0
        attended_classes = attendance_data["attended"] or 0

        percentage = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0

        result_count = con.execute("SELECT COUNT(*) AS count FROM results").fetchone()["count"]

        return {
            "total_students": student_count,
            "attendance_percentage": percentage,
            "total_results": result_count,
        }


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)
app.secret_key = "student-management-system-secret-key"

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

init_db()


# ============================================================
# AUTH DECORATOR
# ============================================================


def admin_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            session.clear()
            flash("Admin access required.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


# ============================================================
# LOGIN / LOGOUT
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("login.html")

        user = get_user_by_username(username)

        if user is None:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        if not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        if user["role"] != "admin":
            flash("This login is only for administrators.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        flash("Welcome Admin!", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ============================================================
# HELPER FUNCTIONS
# ============================================================


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# DASHBOARD AND STUDENT ROUTES
# ============================================================

@app.route("/")
@admin_required
def home():
    students = get_students()
    stats = get_dashboard_stats()
    return render_template("index.html", students=students, stats=stats)


@app.route("/students")
@admin_required
def students_page():
    query = request.args.get("q", "").strip()
    students = get_students(query)
    return render_template("students.html", students=students, query=query)


@app.route("/add", methods=["GET", "POST"])
@admin_required
def add():
    if request.method == "POST":
        rollno = request.form.get("rollno", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()
        photo = request.files.get("photo")

        if not all([rollno, name, email, course]):
            flash("All fields are required.", "error")
            return render_template("add_student.html")

        photo_filename = None

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                flash("Only JPG, JPEG, PNG and WEBP images are allowed.", "error")
                return render_template("add_student.html")

            original_name = secure_filename(photo.filename)
            extension = original_name.rsplit(".", 1)[1].lower()
            photo_filename = f"student_{rollno}.{extension}"
            photo.save(UPLOAD_FOLDER / photo_filename)

        try:
            add_student(rollno, name, email, course, photo_filename)
            flash("Student added successfully.", "success")
            return redirect(url_for("students_page"))

        except ValueError as exc:
            if photo_filename:
                photo_path = UPLOAD_FOLDER / photo_filename
                if photo_path.exists():
                    photo_path.unlink()
            flash(str(exc), "error")

    return render_template("add_student.html")


@app.route("/student/<int:student_id>")
@admin_required
def student_details(student_id):
    student = get_student(student_id)

    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students_page"))

    attendance = get_attendance(student_id)
    total_classes = attendance["total_classes"]
    present_classes = attendance["attended_classes"]
    absent_classes = total_classes - present_classes
    attendance_percentage = attendance["percentage"]

    if total_classes > 0:
        present_percentage = round((present_classes / total_classes) * 100, 2)
        absent_percentage = round((absent_classes / total_classes) * 100, 2)
    else:
        present_percentage = 0
        absent_percentage = 0

    results = get_results(student_id)
    result_summary = get_result_summary(student_id)

    return render_template(
        "student_details.html",
        student=student,
        attendance=attendance,
        total_classes=total_classes,
        present_classes=present_classes,
        absent_classes=absent_classes,
        attendance_percentage=attendance_percentage,
        present_percentage=present_percentage,
        absent_percentage=absent_percentage,
        results=results,
        result_summary=result_summary,
    )


@app.route("/edit/<int:student_id>", methods=["GET", "POST"])
@admin_required
def edit(student_id):
    student = get_student(student_id)

    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students_page"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()

        if not all([name, email, course]):
            flash("All fields are required.", "error")
            return render_template("edit_student.html", student=student)

        photo = request.files.get("photo")
        photo_filename = None

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                flash("Only JPG, JPEG, PNG and WEBP images are allowed.", "error")
                return render_template("edit_student.html", student=student)

            original_name = secure_filename(photo.filename)
            extension = original_name.rsplit(".", 1)[1].lower()
            photo_filename = f"student_{student['rollno']}.{extension}"
            photo.save(UPLOAD_FOLDER / photo_filename)

            old_photo = student["photo"]
            if old_photo:
                old_photo_path = UPLOAD_FOLDER / old_photo
                if old_photo_path.exists() and old_photo_path.name != photo_filename:
                    old_photo_path.unlink()

        update_student(student_id, name, email, course, photo_filename)
        flash("Student updated successfully.", "success")
        return redirect(url_for("student_details", student_id=student_id))

    return render_template("edit_student.html", student=student)


@app.post("/delete/<int:student_id>")
@admin_required
def delete(student_id):
    student = get_student(student_id)

    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students_page"))

    if student["photo"]:
        photo_path = UPLOAD_FOLDER / student["photo"]
        if photo_path.exists():
            photo_path.unlink()

    delete_student(student_id)
    flash("Student deleted successfully.", "success")
    return redirect(url_for("students_page"))


@app.route("/student/<int:student_id>/attendance", methods=["GET", "POST"])
@admin_required
def attendance(student_id):
    student = get_student(student_id)

    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students_page"))

    if request.method == "POST":
        total_classes = request.form.get("total_classes", "0")
        attended_classes = request.form.get("attended_classes", "0")

        try:
            update_attendance(student_id, total_classes, attended_classes)
            flash("Attendance updated successfully.", "success")
            return redirect(url_for("student_details", student_id=student_id))
        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")

    attendance_data = get_attendance(student_id)
    return render_template("attendance.html", student=student, attendance=attendance_data)


@app.route("/student/<int:student_id>/result", methods=["GET", "POST"])
@admin_required
def result(student_id):
    student = get_student(student_id)

    if student is None:
        flash("Student not found.", "error")
        return redirect(url_for("students_page"))

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        marks = request.form.get("marks", "0")
        max_marks = request.form.get("max_marks", "100")

        try:
            add_result(student_id, subject, marks, max_marks)
            flash("Result added successfully.", "success")
            return redirect(url_for("student_details", student_id=student_id))
        except (ValueError, TypeError) as exc:
            flash(str(exc), "error")

    results = get_results(student_id)
    result_summary = get_result_summary(student_id)
    return render_template("result.html", student=student, results=results, result_summary=result_summary)


@app.post("/result/delete/<int:result_id>")
@admin_required
def result_delete(result_id):
    delete_result(result_id)
    flash("Result deleted successfully.", "success")
    return redirect(request.referrer or url_for("students_page"))


# ============================================================
# CREATE DEFAULT ADMIN USER
# ============================================================


def create_default_admin():
    username = "admin"
    password = "admin123"
    existing_user = get_user_by_username(username)

    if existing_user:
        print("Admin user already exists.")
    else:
        password_hash = generate_password_hash(password)
        create_user(username=username, password_hash=password_hash, role="admin")
        print("Admin account created successfully.")
        print("Username:", username)
        print("Password:", password)


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    create_default_admin()
    app.run(debug=True)

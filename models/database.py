import sqlite3
from pathlib import Path


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "database.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect():

    connection = sqlite3.connect(DATABASE)

    # Rows ko dictionary ki tarah access karne ke liye
    connection.row_factory = sqlite3.Row

    # Foreign key enable
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    with connect() as con:

        # ----------------------------------------------------
        # STUDENTS TABLE
        # ----------------------------------------------------

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS students (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                rollno TEXT NOT NULL UNIQUE,

                name TEXT NOT NULL,

                email TEXT NOT NULL,

                course TEXT NOT NULL,

                photo TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ----------------------------------------------------
        # OLD DATABASE UPGRADE
        # ----------------------------------------------------

        columns = con.execute(
            "PRAGMA table_info(students)"
        ).fetchall()

        column_names = [
            column["name"]
            for column in columns
        ]

        if "photo" not in column_names:

            con.execute(
                """
                ALTER TABLE students
                ADD COLUMN photo TEXT
                """
            )

        # ----------------------------------------------------
        # ATTENDANCE TABLE
        # ----------------------------------------------------

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                student_id INTEGER NOT NULL UNIQUE,

                total_classes INTEGER NOT NULL DEFAULT 0,

                attended_classes INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (student_id)
                    REFERENCES students(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # RESULTS TABLE
        # ----------------------------------------------------

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS results (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                student_id INTEGER NOT NULL,

                subject TEXT NOT NULL,

                marks REAL NOT NULL DEFAULT 0,

                max_marks REAL NOT NULL DEFAULT 100,

                FOREIGN KEY (student_id)
                    REFERENCES students(id)
                    ON DELETE CASCADE
            )
            """
        )

        # ----------------------------------------------------
        # USERS TABLE
        # ----------------------------------------------------

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                role TEXT NOT NULL
                    CHECK (
                        role IN (
                            'admin',
                            'teacher',
                            'student'
                        )
                    ),

                student_id INTEGER,

                FOREIGN KEY (student_id)
                    REFERENCES students(id)
                    ON DELETE CASCADE
            )
            """
        )


# ============================================================
# USER FUNCTIONS
# ============================================================

def create_user(
    username,
    password_hash,
    role,
    student_id=None
):

    username = str(username).strip()
    role = str(role).strip().lower()

    if not username:
        raise ValueError("Username is required.")

    if not password_hash:
        raise ValueError("Password is required.")

    if role not in (
        "admin",
        "teacher",
        "student"
    ):
        raise ValueError("Invalid user role.")

    try:

        with connect() as con:

            cursor = con.execute(
                """
                INSERT INTO users
                (
                    username,
                    password_hash,
                    role,
                    student_id
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    role,
                    student_id
                )
            )

            return cursor.lastrowid

    except sqlite3.IntegrityError as exc:

        if "username" in str(exc).lower():

            raise ValueError(
                "Username already exists."
            )

        raise ValueError(
            "Unable to create user."
        )


# ============================================================
# GET USER BY USERNAME
# ============================================================

def get_user_by_username(username):

    username = str(username).strip()

    with connect() as con:

        return con.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                role,
                student_id

            FROM users

            WHERE username = ?

            LIMIT 1
            """,
            (username,)
        ).fetchone()


# ============================================================
# GET USER BY ID
# ============================================================

def get_user_by_id(user_id):

    with connect() as con:

        return con.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                role,
                student_id

            FROM users

            WHERE id = ?

            LIMIT 1
            """,
            (user_id,)
        ).fetchone()


# ============================================================
# GET ALL USERS
# ============================================================

def get_users():

    with connect() as con:

        return con.execute(
            """
            SELECT
                id,
                username,
                role,
                student_id

            FROM users

            ORDER BY id DESC
            """
        ).fetchall()


# ============================================================
# DELETE USER
# ============================================================

def delete_user(user_id):

    with connect() as con:

        con.execute(
            """
            DELETE FROM users

            WHERE id = ?
            """,
            (user_id,)
        )


# ============================================================
# ADD STUDENT
# ============================================================

def add_student(
    rollno,
    name,
    email,
    course,
    photo=None
):

    try:

        with connect() as con:

            cursor = con.execute(
                """
                INSERT INTO students
                (
                    rollno,
                    name,
                    email,
                    course,
                    photo
                )

                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    rollno,
                    name,
                    email,
                    course,
                    photo
                )
            )

            student_id = cursor.lastrowid

            # New student ke liye attendance record
            con.execute(
                """
                INSERT INTO attendance
                (
                    student_id,
                    total_classes,
                    attended_classes
                )

                VALUES (?, 0, 0)
                """,
                (student_id,)
            )

            return student_id

    except sqlite3.IntegrityError as exc:

        if "rollno" in str(exc).lower():

            raise ValueError(
                "Roll number already exists."
            )

        raise ValueError(
            "Unable to add student."
        )


# ============================================================
# GET ALL STUDENTS
# ============================================================

def get_students(query=""):

    with connect() as con:

        if query:

            search = f"%{query}%"

            return con.execute(
                """
                SELECT
                    s.*,

                    COALESCE(
                        a.total_classes,
                        0
                    ) AS total_classes,

                    COALESCE(
                        a.attended_classes,
                        0
                    ) AS attended_classes,

                    CASE

                        WHEN COALESCE(
                            a.total_classes,
                            0
                        ) > 0

                        THEN ROUND(
                            (
                                CAST(
                                    COALESCE(
                                        a.attended_classes,
                                        0
                                    ) AS REAL
                                )
                                /
                                a.total_classes
                            ) * 100,
                            2
                        )

                        ELSE 0

                    END AS attendance_percentage

                FROM students s

                LEFT JOIN attendance a
                    ON s.id = a.student_id

                WHERE
                    s.rollno LIKE ?
                    OR s.name LIKE ?
                    OR s.email LIKE ?
                    OR s.course LIKE ?

                ORDER BY s.id DESC
                """,
                (
                    search,
                    search,
                    search,
                    search
                )
            ).fetchall()

        return con.execute(
            """
            SELECT
                s.*,

                COALESCE(
                    a.total_classes,
                    0
                ) AS total_classes,

                COALESCE(
                    a.attended_classes,
                    0
                ) AS attended_classes,

                CASE

                    WHEN COALESCE(
                        a.total_classes,
                        0
                    ) > 0

                    THEN ROUND(
                        (
                            CAST(
                                COALESCE(
                                    a.attended_classes,
                                    0
                                ) AS REAL
                            )
                            /
                            a.total_classes
                        ) * 100,
                        2
                    )

                    ELSE 0

                END AS attendance_percentage

            FROM students s

            LEFT JOIN attendance a
                ON s.id = a.student_id

            ORDER BY s.id DESC
            """
        ).fetchall()


# ============================================================
# GET SINGLE STUDENT
# ============================================================

def get_student(student_id):

    with connect() as con:

        return con.execute(
            """
            SELECT
                s.*,

                COALESCE(
                    a.total_classes,
                    0
                ) AS total_classes,

                COALESCE(
                    a.attended_classes,
                    0
                ) AS attended_classes,

                CASE

                    WHEN COALESCE(
                        a.total_classes,
                        0
                    ) > 0

                    THEN ROUND(
                        (
                            CAST(
                                COALESCE(
                                    a.attended_classes,
                                    0
                                ) AS REAL
                            )
                            /
                            a.total_classes
                        ) * 100,
                        2
                    )

                    ELSE 0

                END AS attendance_percentage

            FROM students s

            LEFT JOIN attendance a
                ON s.id = a.student_id

            WHERE s.id = ?

            LIMIT 1
            """,
            (student_id,)
        ).fetchone()



# ============================================================
# GET STUDENT BY ROLL NUMBER
# ============================================================

def get_student_by_rollno(rollno):

    with connect() as con:

        return con.execute(
            """
            SELECT *
            FROM students
            WHERE rollno = ?
            LIMIT 1
            """,
            (str(rollno).strip(),)
        ).fetchone()


# ============================================================
# UPDATE STUDENT
# ============================================================

def update_student(
    student_id,
    name,
    email,
    course,
    photo=None
):

    with connect() as con:

        if photo is not None:

            con.execute(
                """
                UPDATE students

                SET
                    name = ?,
                    email = ?,
                    course = ?,
                    photo = ?

                WHERE id = ?
                """,
                (
                    name,
                    email,
                    course,
                    photo,
                    student_id
                )
            )

        else:

            con.execute(
                """
                UPDATE students

                SET
                    name = ?,
                    email = ?,
                    course = ?

                WHERE id = ?
                """,
                (
                    name,
                    email,
                    course,
                    student_id
                )
            )


# ============================================================
# DELETE STUDENT
# ============================================================

def delete_student(student_id):

    with connect() as con:

        con.execute(
            """
            DELETE FROM students

            WHERE id = ?
            """,
            (student_id,)
        )


# ============================================================
# GET ATTENDANCE
# ============================================================

def get_attendance(student_id):

    with connect() as con:

        attendance = con.execute(
            """
            SELECT
                *
            FROM attendance

            WHERE student_id = ?

            LIMIT 1
            """,
            (student_id,)
        ).fetchone()

        if attendance is None:

            return {
                "total_classes": 0,
                "attended_classes": 0,
                "percentage": 0
            }

        total = attendance["total_classes"]
        attended = attendance["attended_classes"]

        if total > 0:

            percentage = round(
                (attended / total) * 100,
                2
            )

        else:

            percentage = 0

        return {
            "total_classes": total,
            "attended_classes": attended,
            "percentage": percentage
        }


# ============================================================
# UPDATE ATTENDANCE
# ============================================================

def update_attendance(
    student_id,
    total_classes,
    attended_classes
):

    try:

        total_classes = int(total_classes)
        attended_classes = int(attended_classes)

    except (ValueError, TypeError):

        raise ValueError(
            "Classes must be valid numbers."
        )

    if total_classes < 0:

        raise ValueError(
            "Total classes cannot be negative."
        )

    if attended_classes < 0:

        raise ValueError(
            "Attended classes cannot be negative."
        )

    if attended_classes > total_classes:

        raise ValueError(
            "Attended classes cannot be greater than total classes."
        )

    with connect() as con:

        con.execute(
            """
            INSERT INTO attendance
            (
                student_id,
                total_classes,
                attended_classes
            )

            VALUES (?, ?, ?)

            ON CONFLICT(student_id)

            DO UPDATE SET

                total_classes =
                    excluded.total_classes,

                attended_classes =
                    excluded.attended_classes
            """,
            (
                student_id,
                total_classes,
                attended_classes
            )
        )


# ============================================================
# GET RESULTS
# ============================================================

def get_results(student_id):

    with connect() as con:

        rows = con.execute(
            """
            SELECT
                id,
                student_id,
                subject,
                marks,
                max_marks,

                ROUND(
                    (
                        marks
                        /
                        max_marks
                    ) * 100,
                    2
                ) AS percentage

            FROM results

            WHERE student_id = ?

            ORDER BY id DESC
            """,
            (student_id,)
        ).fetchall()

        results = []

        for row in rows:

            percentage = float(
                row["percentage"]
            )

            if percentage >= 90:
                grade = "A+"

            elif percentage >= 80:
                grade = "A"

            elif percentage >= 70:
                grade = "B+"

            elif percentage >= 60:
                grade = "B"

            elif percentage >= 50:
                grade = "C"

            elif percentage >= 40:
                grade = "D"

            else:
                grade = "F"

            results.append(
                {
                    "id": row["id"],
                    "student_id": row["student_id"],
                    "subject": row["subject"],
                    "marks": row["marks"],
                    "max_marks": row["max_marks"],
                    "percentage": row["percentage"],
                    "grade": grade
                }
            )

        return results


# ============================================================
# ADD RESULT
# ============================================================

def add_result(
    student_id,
    subject,
    marks,
    max_marks
):

    subject = str(subject).strip()

    if not subject:

        raise ValueError(
            "Subject is required."
        )

    try:

        marks = float(marks)
        max_marks = float(max_marks)

    except (ValueError, TypeError):

        raise ValueError(
            "Marks must be valid numbers."
        )

    if max_marks <= 0:

        raise ValueError(
            "Maximum marks must be greater than 0."
        )

    if marks < 0:

        raise ValueError(
            "Marks cannot be negative."
        )

    if marks > max_marks:

        raise ValueError(
            "Marks cannot be greater than maximum marks."
        )

    with connect() as con:

        con.execute(
            """
            INSERT INTO results
            (
                student_id,
                subject,
                marks,
                max_marks
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                student_id,
                subject,
                marks,
                max_marks
            )
        )


# ============================================================
# DELETE RESULT
# ============================================================

def delete_result(result_id):

    with connect() as con:

        con.execute(
            """
            DELETE FROM results

            WHERE id = ?
            """,
            (result_id,)
        )


# ============================================================
# RESULT SUMMARY
# ============================================================

def get_result_summary(student_id):

    with connect() as con:

        result = con.execute(
            """
            SELECT

                COALESCE(
                    SUM(marks),
                    0
                ) AS total_marks,

                COALESCE(
                    SUM(max_marks),
                    0
                ) AS max_marks

            FROM results

            WHERE student_id = ?
            """,
            (student_id,)
        ).fetchone()

        total_marks = float(
            result["total_marks"]
        )

        max_marks = float(
            result["max_marks"]
        )

        if max_marks > 0:

            percentage = round(
                (
                    total_marks
                    /
                    max_marks
                ) * 100,
                2
            )

        else:

            percentage = 0

        if percentage >= 90:
            grade = "A+"

        elif percentage >= 80:
            grade = "A"

        elif percentage >= 70:
            grade = "B+"

        elif percentage >= 60:
            grade = "B"

        elif percentage >= 50:
            grade = "C"

        elif percentage >= 40:
            grade = "D"

        else:
            grade = "F"

        return {
            "total_marks": total_marks,
            "max_marks": max_marks,
            "percentage": percentage,
            "grade": grade
        }


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

def get_dashboard_stats():

    with connect() as con:

        # ----------------------------------------------------
        # Total Students
        # ----------------------------------------------------

        total = con.execute(
            """
            SELECT COUNT(*)
            FROM students
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Total Courses
        # ----------------------------------------------------

        courses = con.execute(
            """
            SELECT COUNT(
                DISTINCT course
            )

            FROM students
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Students Added Today
        # ----------------------------------------------------

        today = con.execute(
            """
            SELECT COUNT(*)

            FROM students

            WHERE date(created_at)
                = date('now')
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # Average Attendance
        # ----------------------------------------------------

        average_attendance = con.execute(
            """
            SELECT

                COALESCE(
                    AVG(
                        CASE

                            WHEN total_classes > 0

                            THEN (
                                CAST(
                                    attended_classes
                                    AS REAL
                                )
                                /
                                total_classes
                            ) * 100

                            ELSE 0

                        END
                    ),
                    0
                )

            FROM attendance
            """
        ).fetchone()[0]

        return {
            "total": total,
            "courses": courses,
            "today": today,
            "average_attendance": round(
                average_attendance,
                2
            )
        }
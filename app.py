from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from functools import wraps
from pathlib import Path

from werkzeug.utils import secure_filename
from werkzeug.security import (
    check_password_hash
)

from models.database import (
    init_db,
    add_student,
    get_students,
    get_student,
    update_student,
    delete_student,
    get_dashboard_stats,
    get_attendance,
    update_attendance,
    get_results,
    add_result,
    delete_result,
    get_result_summary,
    get_user_by_username,
    get_student_by_rollno
)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = "student-management-system-secret-key"


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_FOLDER = (
    BASE_DIR
    / "static"
    / "uploads"
)

UPLOAD_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = str(
    UPLOAD_FOLDER
)


ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


# ============================================================
# DATABASE INITIALIZE
# ============================================================

init_db()


# ============================================================
# ============================================================
# ROLE DECORATORS
# ============================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


def roles_required(*allowed_roles):

    def decorator(function):

        @wraps(function)
        def decorated_function(*args, **kwargs):

            if "user_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") not in allowed_roles:

                flash(
                    "You do not have permission to access this page.",
                    "error"
                )

                return redirect(url_for("role_dashboard"))

            return function(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(function):
    return roles_required("admin")(function)


def teacher_required(function):
    return roles_required("admin", "teacher")(function)


# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if "user_id" in session:
        return redirect(url_for("role_dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return render_template("login.html")

        user = get_user_by_username(username)

        if user is None:

            flash(
                "Invalid username or password.",
                "error"
            )

            return render_template("login.html")

        if not check_password_hash(
            user["password_hash"],
            password
        ):

            flash(
                "Invalid username or password.",
                "error"
            )

            return render_template("login.html")

        if (
            user["role"] == "student"
            and not user["student_id"]
        ):

            flash(
                "This student account is not linked to a student record.",
                "error"
            )

            return render_template("login.html")

        session.clear()

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["student_id"] = user["student_id"]

        flash(
            f"Welcome {user['username']}!",
            "success"
        )

        return redirect(url_for("role_dashboard"))

    return render_template("login.html")


# ============================================================
# ROLE DASHBOARD
# ============================================================

@app.route("/role-dashboard")
@login_required
def role_dashboard():

    role = session.get("role")

    if role == "admin":
        return redirect(url_for("home"))

    if role == "teacher":
        return redirect(url_for("teacher_dashboard"))

    if role == "student":
        return redirect(url_for("student_dashboard"))

    session.clear()

    return redirect(url_for("login"))


# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# HELPER - CHECK IMAGE
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
@admin_required
def home():

    students = get_students()

    stats = get_dashboard_stats()

    return render_template(
        "index.html",
        students=students,
        stats=stats
    )


# ============================================================
# ============================================================
# TEACHER DASHBOARD
# ============================================================

@app.route("/teacher-dashboard")
@roles_required("teacher")
def teacher_dashboard():

    students = get_students()
    stats = get_dashboard_stats()

    return render_template(
        "teacher_dashboard.html",
        students=students,
        stats=stats
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student-dashboard")
@roles_required("student")
def student_dashboard():

    student_id = session.get("student_id")

    if not student_id:

        session.clear()

        flash(
            "Student account is not properly linked.",
            "error"
        )

        return redirect(url_for("login"))

    student = get_student(student_id)

    if student is None:

        session.clear()

        flash(
            "Student record not found.",
            "error"
        )

        return redirect(url_for("login"))

    attendance_data = get_attendance(student_id)

    results = get_results(student_id)

    result_summary = get_result_summary(student_id)

    return render_template(
        "student_dashboard.html",
        student=student,
        attendance=attendance_data,
        results=results,
        result_summary=result_summary
    )


# ============================================================
# STUDENTS LIST + SEARCH
# Admin + Teacher
# ============================================================

@app.route("/students")
@teacher_required
def students_page():

    query = request.args.get(
        "q",
        ""
    ).strip()

    students = get_students(
        query
    )

    return render_template(
        "students.html",
        students=students,
        query=query
    )


# ============================================================
# ADD STUDENT
# ============================================================

@app.route(
    "/add",
    methods=["GET", "POST"]
)
@admin_required
def add():

    if request.method == "POST":

        rollno = request.form.get(
            "rollno",
            ""
        ).strip()

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        course = request.form.get(
            "course",
            ""
        ).strip()

        photo = request.files.get(
            "photo"
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not all([
            rollno,
            name,
            email,
            course
        ]):

            flash(
                "All fields are required.",
                "error"
            )

            return render_template(
                "add_student.html"
            )


        # ----------------------------------------------------
        # SAVE PHOTO
        # ----------------------------------------------------

        photo_filename = None

        if photo and photo.filename:

            if not allowed_file(
                photo.filename
            ):

                flash(
                    "Only JPG, JPEG, PNG and WEBP images are allowed.",
                    "error"
                )

                return render_template(
                    "add_student.html"
                )


            original_name = secure_filename(
                photo.filename
            )

            extension = (
                original_name
                .rsplit(
                    ".",
                    1
                )[1]
                .lower()
            )


            photo_filename = (
                f"student_{rollno}.{extension}"
            )


            photo.save(
                UPLOAD_FOLDER
                / photo_filename
            )


        # ----------------------------------------------------
        # ADD STUDENT
        # ----------------------------------------------------

        try:

            add_student(
                rollno,
                name,
                email,
                course,
                photo_filename
            )

            flash(
                "Student added successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "students_page"
                )
            )


        except ValueError as exc:

            if photo_filename:

                photo_path = (
                    UPLOAD_FOLDER
                    / photo_filename
                )

                if photo_path.exists():

                    photo_path.unlink()


            flash(
                str(exc),
                "error"
            )


    return render_template(
        "add_student.html"
    )


# ============================================================
# STUDENT DETAILS
# ============================================================

@app.route(
    "/student/<int:student_id>"
)
@teacher_required
def student_details(student_id):

    student = get_student(
        student_id
    )


    if student is None:

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for(
                "students_page"
            )
        )


    # --------------------------------------------------------
    # ATTENDANCE
    # --------------------------------------------------------

    attendance = get_attendance(
        student_id
    )


    total_classes = (
        attendance["total_classes"]
    )

    present_classes = (
        attendance["attended_classes"]
    )


    absent_classes = (
        total_classes
        - present_classes
    )


    attendance_percentage = (
        attendance["percentage"]
    )


    if total_classes > 0:

        present_percentage = round(
            (
                present_classes
                /
                total_classes
            ) * 100,
            2
        )

        absent_percentage = round(
            (
                absent_classes
                /
                total_classes
            ) * 100,
            2
        )

    else:

        present_percentage = 0

        absent_percentage = 0


    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    results = get_results(
        student_id
    )


    result_summary = get_result_summary(
        student_id
    )


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

        result_summary=result_summary
    )


# ============================================================
# EDIT STUDENT
# ============================================================

@app.route(
    "/edit/<int:student_id>",
    methods=["GET", "POST"]
)
@admin_required
def edit(student_id):

    student = get_student(
        student_id
    )


    if student is None:

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for(
                "students_page"
            )
        )


    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        course = request.form.get(
            "course",
            ""
        ).strip()


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not all([
            name,
            email,
            course
        ]):

            flash(
                "All fields are required.",
                "error"
            )

            return render_template(
                "edit_student.html",
                student=student
            )


        # ----------------------------------------------------
        # NEW PHOTO
        # ----------------------------------------------------

        photo = request.files.get(
            "photo"
        )

        photo_filename = None


        if photo and photo.filename:

            if not allowed_file(
                photo.filename
            ):

                flash(
                    "Only JPG, JPEG, PNG and WEBP images are allowed.",
                    "error"
                )

                return render_template(
                    "edit_student.html",
                    student=student
                )


            original_name = secure_filename(
                photo.filename
            )


            extension = (
                original_name
                .rsplit(
                    ".",
                    1
                )[1]
                .lower()
            )


            photo_filename = (
                f"student_{student['rollno']}.{extension}"
            )


            photo.save(
                UPLOAD_FOLDER
                / photo_filename
            )


            # ------------------------------------------------
            # REMOVE OLD PHOTO
            # ------------------------------------------------

            old_photo = student["photo"]

            if old_photo:

                old_photo_path = (
                    UPLOAD_FOLDER
                    / old_photo
                )

                if (
                    old_photo_path.exists()
                    and
                    old_photo_path.name
                    != photo_filename
                ):

                    old_photo_path.unlink()


        # ----------------------------------------------------
        # UPDATE STUDENT
        # ----------------------------------------------------

        update_student(
            student_id,
            name,
            email,
            course,
            photo_filename
        )


        flash(
            "Student updated successfully.",
            "success"
        )


        return redirect(
            url_for(
                "student_details",
                student_id=student_id
            )
        )


    return render_template(
        "edit_student.html",
        student=student
    )


# ============================================================
# DELETE STUDENT
# ============================================================

@app.post(
    "/delete/<int:student_id>"
)
@admin_required
def delete(student_id):

    student = get_student(
        student_id
    )


    if student is None:

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for(
                "students_page"
            )
        )


    # --------------------------------------------------------
    # DELETE PHOTO
    # --------------------------------------------------------

    if student["photo"]:

        photo_path = (
            UPLOAD_FOLDER
            / student["photo"]
        )

        if photo_path.exists():

            photo_path.unlink()


    # --------------------------------------------------------
    # DELETE STUDENT
    # --------------------------------------------------------

    delete_student(
        student_id
    )


    flash(
        "Student deleted successfully.",
        "success"
    )


    return redirect(
        url_for(
            "students_page"
        )
    )


# ============================================================
# ATTENDANCE
# ============================================================

@app.route(
    "/student/<int:student_id>/attendance",
    methods=["GET", "POST"]
)
@teacher_required
def attendance(student_id):

    student = get_student(
        student_id
    )


    if student is None:

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for(
                "students_page"
            )
        )


    # --------------------------------------------------------
    # UPDATE ATTENDANCE
    # --------------------------------------------------------

    if request.method == "POST":

        total_classes = request.form.get(
            "total_classes",
            "0"
        )

        attended_classes = request.form.get(
            "attended_classes",
            "0"
        )


        try:

            update_attendance(
                student_id,
                total_classes,
                attended_classes
            )


            flash(
                "Attendance updated successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "student_details",
                    student_id=student_id
                )
            )


        except (
            ValueError,
            TypeError
        ) as exc:

            flash(
                str(exc),
                "error"
            )


    # --------------------------------------------------------
    # GET ATTENDANCE
    # --------------------------------------------------------

    attendance_data = get_attendance(
        student_id
    )


    return render_template(
        "attendance.html",

        student=student,

        attendance=attendance_data
    )


# ============================================================
# RESULT
# ============================================================

@app.route(
    "/student/<int:student_id>/result",
    methods=["GET", "POST"]
)
@teacher_required
def result(student_id):

    student = get_student(
        student_id
    )


    if student is None:

        flash(
            "Student not found.",
            "error"
        )

        return redirect(
            url_for(
                "students_page"
            )
        )


    # --------------------------------------------------------
    # ADD RESULT
    # --------------------------------------------------------

    if request.method == "POST":

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        marks = request.form.get(
            "marks",
            "0"
        )

        max_marks = request.form.get(
            "max_marks",
            "100"
        )


        try:

            add_result(
                student_id,
                subject,
                marks,
                max_marks
            )


            flash(
                "Result added successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "student_details",
                    student_id=student_id
                )
            )


        except (
            ValueError,
            TypeError
        ) as exc:

            flash(
                str(exc),
                "error"
            )


    # --------------------------------------------------------
    # GET RESULTS
    # --------------------------------------------------------

    results = get_results(
        student_id
    )


    result_summary = get_result_summary(
        student_id
    )


    return render_template(
        "result.html",

        student=student,

        results=results,

        result_summary=result_summary
    )


# ============================================================
# DELETE RESULT
# ============================================================

@app.post(
    "/result/delete/<int:result_id>"
)
@teacher_required
def result_delete(result_id):

    delete_result(
        result_id
    )


    flash(
        "Result deleted successfully.",
        "success"
    )


    return redirect(
        request.referrer
        or
        url_for(
            "students_page"
        )
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
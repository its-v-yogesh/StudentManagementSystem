from werkzeug.security import generate_password_hash

from models.database import (
    create_user,
    get_user_by_username,
    get_student_by_rollno
)


print("\n===================================")
print("   STUDENT MANAGEMENT SYSTEM")
print("   USER ACCOUNT CREATOR")
print("===================================\n")


# ==========================================
# CREATE TEACHER ACCOUNT
# ==========================================

teacher_username = "teacher"
teacher_password = "teacher123"

existing_teacher = get_user_by_username(teacher_username)

if existing_teacher:
    print("Teacher account already exists.")
else:
    create_user(
        username=teacher_username,
        password_hash=generate_password_hash(teacher_password),
        role="teacher"
    )

    print("Teacher account created successfully!")


# ==========================================
# CREATE STUDENT ACCOUNT
# ==========================================

student_username = "student"
student_password = "student123"

# IMPORTANT:
# Yahan apne database me already existing
# student ka Roll Number likho.

rollno = input("\nEnter existing student Roll Number: ").strip()

student = get_student_by_rollno(rollno)

if student is None:

    print("\nStudent with this Roll Number was not found.")
    print("First add the student from the admin dashboard.")
    
else:

    existing_student_user = get_user_by_username(student_username)

    if existing_student_user:

        print("Student account already exists.")

    else:

        create_user(
            username=student_username,
            password_hash=generate_password_hash(student_password),
            role="student",
            student_id=student["id"]
        )

        print("\nStudent account created successfully!")


print("\n===================================")
print("LOGIN DETAILS")
print("===================================")

print("\nTeacher Login")
print("Username : teacher")
print("Password : teacher123")

print("\nStudent Login")
print("Username : student")
print("Password : student123")

print("\n===================================")
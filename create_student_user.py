from werkzeug.security import generate_password_hash

from models.database import (
    get_students,
    get_student_by_rollno,
    get_user_by_username,
    create_user
)


print("\n======================================")
print("       CREATE STUDENT USER")
print("======================================\n")


# --------------------------------------
# SHOW EXISTING STUDENTS
# --------------------------------------

students = get_students()

if not students:
    print("❌ Database mein koi student nahi hai.")
    print("\nPehle Admin Login karke student add karo.")
    exit()


print("Existing Students:")
print("--------------------------------------")

for student in students:
    print(
        f"ID: {student['id']} | "
        f"Roll No: {student['rollno']} | "
        f"Name: {student['name']}"
    )

print("--------------------------------------")


# --------------------------------------
# GET ROLL NUMBER
# --------------------------------------

rollno = input("\nEnter Student Roll Number: ").strip()


if not rollno:
    print("\n❌ Roll Number required.")
    exit()


# --------------------------------------
# FIND STUDENT
# --------------------------------------

student = get_student_by_rollno(rollno)


if student is None:

    print("\n❌ Student not found.")

    print(
        "\nJo Roll Number upar list mein dikh raha hai, "
        "usi ko exactly enter karo."
    )

    exit()


print("\nStudent Found!")
print("--------------------------------------")
print("Student ID :", student["id"])
print("Roll No    :", student["rollno"])
print("Name       :", student["name"])
print("Course     :", student["course"])
print("--------------------------------------")


# --------------------------------------
# USERNAME
# --------------------------------------

username = input(
    "\nEnter username for student "
    "(Press Enter for 'student'): "
).strip()


if not username:
    username = "student"


# --------------------------------------
# PASSWORD
# --------------------------------------

password = input(
    "Enter password "
    "(Press Enter for 'student123'): "
)


if not password:
    password = "student123"


# --------------------------------------
# CHECK USERNAME
# --------------------------------------

existing_user = get_user_by_username(username)


if existing_user:

    print("\n❌ This username already exists.")

    print("--------------------------------------")
    print("Username   :", existing_user["username"])
    print("Role       :", existing_user["role"])
    print("Student ID :", existing_user["student_id"])
    print("--------------------------------------")

    if existing_user["role"] == "student":

        if existing_user["student_id"] == student["id"]:

            print("\n✅ This student account already exists.")

            print("\nLogin Details:")
            print("Username :", username)
            print("Password : student123")

        else:

            print(
                "\n⚠ This username is already linked "
                "to another student."
            )

    else:

        print(
            "\n⚠ This username belongs to "
            f"{existing_user['role']}."
        )

    exit()


# --------------------------------------
# CREATE USER
# --------------------------------------

password_hash = generate_password_hash(password)


create_user(
    username=username,
    password_hash=password_hash,
    role="student",
    student_id=student["id"]
)


# --------------------------------------
# SUCCESS
# --------------------------------------

print("\n======================================")
print("       STUDENT USER CREATED")
print("======================================")

print("\nStudent Name :", student["name"])
print("Roll Number  :", student["rollno"])
print("Username     :", username)
print("Password     :", password)

print("\nYou can now login as Student.")
print("======================================\n")
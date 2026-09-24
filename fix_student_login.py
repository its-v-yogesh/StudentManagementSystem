from werkzeug.security import generate_password_hash
from models.database import (
    get_user_by_username,
    get_student_by_rollno,
    create_user
)


print("\n======================================")
print("     STUDENT LOGIN FIX")
print("======================================\n")


# --------------------------------------
# ENTER STUDENT ROLL NUMBER
# --------------------------------------

rollno = input("Enter Student Roll Number: ").strip()

if not rollno:
    print("\nRoll number cannot be empty.")
    exit()


# --------------------------------------
# FIND STUDENT
# --------------------------------------

student = get_student_by_rollno(rollno)

if student is None:

    print("\n❌ Student not found!")

    print("\nPlease check the Roll Number.")
    print("The student must already exist in your Student Management System.")

    exit()


print("\nStudent found successfully!")

print("--------------------------------------")
print("Student ID :", student["id"])
print("Roll No    :", student["rollno"])
print("Name       :", student["name"])
print("Email      :", student["email"])
print("Course     :", student["course"])
print("--------------------------------------")


# --------------------------------------
# STUDENT LOGIN DETAILS
# --------------------------------------

username = "student"
password = "student123"


# --------------------------------------
# CHECK EXISTING USER
# --------------------------------------

existing_user = get_user_by_username(username)


if existing_user:

    print("\n⚠ Student username already exists.")

    print("--------------------------------------")
    print("Username  :", existing_user["username"])
    print("Role      :", existing_user["role"])
    print("Student ID:", existing_user["student_id"])
    print("--------------------------------------")


    # Check whether it is linked correctly

    if existing_user["role"] != "student":

        print("\n❌ Problem:")
        print("Username 'student' is not a student account.")

        print("\nDelete/change this account before creating student login.")

        exit()


    if existing_user["student_id"] != student["id"]:

        print("\n❌ Problem:")
        print("Student account is linked to a different student.")

        print("\nExisting Student ID:",
              existing_user["student_id"])

        print("Correct Student ID:",
              student["id"])

        print("\nPlease remove the old student account")
        print("and run this script again.")

        exit()


    # If everything is correct
    print("\n✅ Student account is correctly linked.")

    print("\nUse these login details:")

    print("--------------------------------------")
    print("Username : student")
    print("Password : student123")
    print("--------------------------------------")

    exit()


# --------------------------------------
# CREATE NEW STUDENT USER
# --------------------------------------

password_hash = generate_password_hash(password)


create_user(
    username=username,
    password_hash=password_hash,
    role="student",
    student_id=student["id"]
)


print("\n======================================")
print("✅ STUDENT ACCOUNT CREATED")
print("======================================")

print("\nLogin Details:")
print("--------------------------------------")
print("Username : student")
print("Password : student123")
print("--------------------------------------")

print("\nStudent ID:", student["id"])
print("Student Name:", student["name"])

print("\nYou can now login as student.")
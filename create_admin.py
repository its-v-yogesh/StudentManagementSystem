from werkzeug.security import generate_password_hash

from models.database import (
    init_db,
    create_user,
    get_user_by_username
)


# Initialize database
init_db()


# Admin details
username = "admin"
password = "admin123"


# Check if admin already exists
existing_user = get_user_by_username(username)


if existing_user:

    print("Admin user already exists.")

else:

    password_hash = generate_password_hash(password)

    create_user(
        username=username,
        password_hash=password_hash,
        role="admin"
    )

    print("Admin account created successfully.")
    print("Username:", username)
    print("Password:", password)
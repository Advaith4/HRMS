import sys
from sqlmodel import Session, select
sys.path.append(".")
from src.database.connection import engine
from src.models import User
from src.core.security import hash_password

users_to_reset = ["Advaith", "advaithg", "arun", "bipin", "manager", "candidate", "admin", "admin1"]

with Session(engine) as session:
    for username in users_to_reset:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            user.hashed_password = hash_password("Pass123!")
            session.add(user)
            print(f"Reset password for user: {username} (Role: {user.role})")
        else:
            print(f"User not found: {username}")
    session.commit()
print("Password reset process completed.")

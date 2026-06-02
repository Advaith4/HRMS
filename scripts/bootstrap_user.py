"""Create or promote a TalentForge user with a controlled role."""

import argparse

from sqlmodel import Session, select

from src.core.security import hash_password
from src.database.connection import create_db_and_tables, engine
from src.models import USER_ROLES, User


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", required=True, choices=sorted(USER_ROLES))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_db_and_tables()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == args.username)).first()
        if user:
            user.hashed_password = hash_password(args.password)
            user.role = args.role
        else:
            user = User(
                username=args.username,
                hashed_password=hash_password(args.password),
                role=args.role,
            )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"TalentForge user ready: id={user.id} username={user.username} role={user.role}")

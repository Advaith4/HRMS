import sys
from sqlmodel import Session, select
sys.path.append(".")
from src.database.connection import engine
from src.models import User, Employee

with Session(engine) as session:
    users = session.exec(select(User)).all()
    print("--- Database Users and Employee Profiles ---")
    for u in users:
        emp = session.exec(select(Employee).where(Employee.user_id == u.id)).first()
        emp_status = f"Employee Profile Found (Code: {emp.employee_code})" if emp else "No Employee Profile Found"
        print(f"ID: {u.id} | Username: {u.username} | Role: {u.role} | Status: {emp_status}")

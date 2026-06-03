import sys
from sqlmodel import Session, select
sys.path.append(".")
from src.database.connection import engine
from src.models import User, Employee
from src.core.security import hash_password

def setup():
    demo_accounts = [
        {"username": "demo_hr", "role": "hr", "emp_code": "EMP-HR999", "dept": "HR Operations", "desig": "HR Manager", "salary": 95000.0},
        {"username": "demo_manager", "role": "manager", "emp_code": "EMP-MGR88", "dept": "Engineering", "desig": "Engineering Manager", "salary": 140000.0},
        {"username": "demo_employee", "role": "employee", "emp_code": "EMP-EMP77", "dept": "Engineering", "desig": "Software Engineer", "salary": 75000.0},
    ]

    with Session(engine) as session:
        for acc in demo_accounts:
            # Check if user exists
            user = session.exec(select(User).where(User.username == acc["username"])).first()
            if not user:
                user = User(
                    username=acc["username"],
                    hashed_password=hash_password("Pass123!"),
                    role=acc["role"],
                    location="Hyderabad, India",
                    experience="Senior" if acc["role"] != "employee" else "Mid-level"
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                print(f"Created User: {user.username} (ID: {user.id})")
            else:
                user.role = acc["role"]
                session.add(user)
                session.commit()
                print(f"User {user.username} already exists (ID: {user.id}), updated role to {user.role}")

            # Check if employee record exists for manager and employee
            emp = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
            if not emp:
                emp = Employee(
                    user_id=user.id,
                    employee_code=acc["emp_code"],
                    department=acc["dept"],
                    designation=acc["desig"],
                    salary=acc["salary"],
                    full_name=user.username.replace("_", " ").title(),
                    email=f"{user.username}@talentforge.ai",
                    phone="+91 98765 43210",
                    status="Active",
                    work_location="Remote",
                    skills="Python, React, FastApi"
                )
                session.add(emp)
                session.commit()
                print(f"Created Employee record for {user.username} (Code: {emp.employee_code})")
            else:
                print(f"Employee record already exists for {user.username} (Code: {emp.employee_code})")

if __name__ == "__main__":
    setup()

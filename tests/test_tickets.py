import os
import uuid

os.environ["DATABASE_URL"] = f"sqlite:///data/test_{uuid.uuid4().hex[:8]}.db"
os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.models import Employee, User, EmployeeTicket

create_db_and_tables()
client = TestClient(app)

def _register(username: str, role: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "Pass123!"},
    )
    assert response.status_code == 201, response.text
    if role == "candidate":
        return response.json()["access_token"]

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).one()
        user.role = role
        session.add(user)
        session.commit()

    login = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]

def test_ticket_creation_and_flow():
    # 1. Create users with different roles
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    employee_username = f"emp_{uuid.uuid4().hex[:8]}"
    employee_token = _register(employee_username, "employee")
    manager_username = f"mgr_{uuid.uuid4().hex[:8]}"
    manager_token = _register(manager_username, "manager")
    
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    emp_headers = {"Authorization": f"Bearer {employee_token}"}
    mgr_headers = {"Authorization": f"Bearer {manager_token}"}

    # Fetch User IDs for mapping/assignment
    with Session(engine) as session:
        hr_user = session.exec(select(User).where(User.role == "hr")).first()
        emp_user = session.exec(select(User).where(User.username == employee_username)).one()
        mgr_user = session.exec(select(User).where(User.username == manager_username)).one()
        
        hr_id = hr_user.id
        emp_id = emp_user.id
        mgr_id = mgr_user.id
        
        # We need to register the employee user as an Employee in the employee table
        employee_record = Employee(
            user_id=emp_id,
            employee_code=f"EMP-{uuid.uuid4().hex[:6]}",
            department="Engineering",
            designation="Developer",
            salary=60000,
        )
        session.add(employee_record)
        
        # Register the manager user as an Employee to test department fetch in resolvers
        manager_record = Employee(
            user_id=mgr_id,
            employee_code=f"EMP-{uuid.uuid4().hex[:6]}",
            department="Operations",
            designation="Manager",
            salary=90000,
        )
        session.add(manager_record)
        session.commit()

    # 2. Raise a ticket as the employee
    ticket_payload = {
        "title": "AC Not Working",
        "description": "The AC in the third floor engineering bay is not working since yesterday.",
        "category": "Workplace Concern",
        "priority": "Medium"
    }
    
    create_resp = client.post("/api/tickets", headers=emp_headers, json=ticket_payload)
    assert create_resp.status_code == 201, create_resp.text
    ticket_data = create_resp.json()
    assert ticket_data["title"] == "AC Not Working"
    assert ticket_data["status"] == "Open"
    ticket_id = ticket_data["id"]

    # 3. Test list_resolvers endpoint
    # normal employee should not be able to list resolvers
    resolvers_denied = client.get("/api/tickets/resolvers", headers=emp_headers)
    assert resolvers_denied.status_code == 403

    # HR and Managers should be able to list resolvers
    resolvers_ok = client.get("/api/tickets/resolvers", headers=hr_headers)
    assert resolvers_ok.status_code == 200
    resolvers_list = resolvers_ok.json()
    
    # Confirm it returns HR and Managers with appropriate department information
    mgr_in_resolvers = [r for r in resolvers_list if r["id"] == mgr_id]
    assert len(mgr_in_resolvers) == 1
    assert mgr_in_resolvers[0]["department"] == "Operations"
    assert mgr_in_resolvers[0]["role"] == "manager"
    
    hr_in_resolvers = [r for r in resolvers_list if r["id"] == hr_id]
    assert len(hr_in_resolvers) == 1
    # HR is not registered in Employee table, so department should be "N/A"
    assert hr_in_resolvers[0]["department"] == "N/A"
    assert hr_in_resolvers[0]["role"] == "hr"

    # 4. Assign the ticket
    # Trying to assign to a normal employee should fail with 400
    assign_fail = client.put(f"/api/tickets/{ticket_id}/assign", headers=hr_headers, json={"assigned_to": emp_id})
    assert assign_fail.status_code == 400
    assert "Assigned user must be an HR, Manager, or Admin user" in assign_fail.json()["error"]

    # Assigning to a manager should succeed
    assign_ok = client.put(f"/api/tickets/{ticket_id}/assign", headers=hr_headers, json={"assigned_to": mgr_id})
    assert assign_ok.status_code == 200
    assert assign_ok.json()["status"] == "Assigned"
    assert assign_ok.json()["assigned_to"] == mgr_id
    assert assign_ok.json()["assigned_to_username"] == manager_username

    # 5. Update status and add resolution note
    status_update = client.put(
        f"/api/tickets/{ticket_id}/status", 
        headers=hr_headers, 
        json={"status": "Resolved", "resolution_note": "AC unit repair scheduled."}
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "Resolved"
    assert status_update.json()["resolution_note"] == "AC unit repair scheduled."


import sys
import httpx
sys.path.append(".")

client = httpx.Client(base_url="http://127.0.0.1:8000")

def test_employee_flow():
    # 1. Login as arun
    print("Trying login for arun...")
    login_res = client.post("/api/auth/login", json={"username": "arun", "password": "Pass123!"})
    if login_res.status_code != 200:
        print("Login failed:", login_res.status_code, login_res.text)
        return
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful. Token acquired.")

    # 2. Get dashboard
    print("\nFetching employee dashboard...")
    dash_res = client.get("/api/employees/dashboard", headers=headers)
    print("Status:", dash_res.status_code)
    print("Dashboard Data:", dash_res.json())

    # 3. Check-In
    print("\nTesting check-in...")
    check_in_res = client.post("/api/employees/attendance/check-in", headers=headers)
    print("Status:", check_in_res.status_code)
    print("Check-In Data:", check_in_res.json())

    # 4. Check-Out
    print("\nTesting check-out...")
    check_out_res = client.post("/api/employees/attendance/check-out", headers=headers)
    print("Status:", check_out_res.status_code)
    print("Check-Out Data:", check_out_res.json())

    # 5. Leave Submit
    print("\nTesting leave request submission...")
    leave_res = client.post("/api/employees/leave", headers=headers, json={
        "leave_type": "Sick",
        "start_date": "2026-06-10",
        "end_date": "2026-06-12",
        "reason": "Test health leave"
    })
    print("Status:", leave_res.status_code)
    print("Leave Request Data:", leave_res.json())

if __name__ == "__main__":
    test_employee_flow()

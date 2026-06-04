import os
import sys
import httpx

# Test calling the local FastAPI server directly
BASE_URL = "http://127.0.0.1:8000"

def test_login_and_fetch():
    client = httpx.Client(timeout=20.0)
    
    # 1. Login as hruser
    print("Attempting login as 'hruser'...")
    login_resp = client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "hruser",
        "password": "Pass123!"
    })
    
    if login_resp.status_code != 200:
        print("Login failed:", login_resp.text)
    else:
        login_data = login_resp.json()
        token = login_data["access_token"]
        role = login_data["role"]
        print(f"Logged in successfully. Role: {role}")
        
        # Fetch HR Dashboard
        headers = {"Authorization": f"Bearer {token}"}
        dashboard_resp = client.get(f"{BASE_URL}/api/dashboard/hr", headers=headers)
        if dashboard_resp.status_code == 200:
            dash_data = dashboard_resp.json()
            print("HR Dashboard Data Summary:")
            print(f"  Jobs count: {len(dash_data.get('jobs', []))}")
            print(f"  Applications count: {len(dash_data.get('applications', []))}")
            print(f"  Candidates count: {len(dash_data.get('candidates', []))}")
        else:
            print("Failed to fetch HR dashboard:", dashboard_resp.text)

    # 2. Login as candidate aka
    print("\nAttempting login as 'aka'...")
    login_resp_c = client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "aka",
        "password": "Pass123!"
    })
    
    if login_resp_c.status_code != 200:
        print("Login failed:", login_resp_c.text)
    else:
        login_data_c = login_resp_c.json()
        token_c = login_data_c["access_token"]
        role_c = login_data_c["role"]
        print(f"Logged in successfully. Role: {role_c}")
        
        # Fetch Candidate Dashboard
        headers_c = {"Authorization": f"Bearer {token_c}"}
        dashboard_resp_c = client.get(f"{BASE_URL}/api/dashboard/candidate", headers=headers_c)
        if dashboard_resp_c.status_code == 200:
            dash_data_c = dashboard_resp_c.json()
            print("Candidate Dashboard Data Summary:")
            print(f"  Available careers count: {len(dash_data_c.get('jobs', []))}")
            print(f"  My Applications count: {len(dash_data_c.get('applications', []))}")
            print(f"  Has resume: {dash_data_c.get('has_resume')}")
        else:
            print("Failed to fetch Candidate dashboard:", dashboard_resp_c.text)

    # 3. Login as employee demo_employee
    print("\nAttempting login as 'demo_employee'...")
    login_resp_e = client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "demo_employee",
        "password": "Pass123!"
    })
    
    if login_resp_e.status_code != 200:
        print("Login failed:", login_resp_e.text)
    else:
        login_data_e = login_resp_e.json()
        token_e = login_data_e["access_token"]
        role_e = login_data_e["role"]
        print(f"Logged in successfully. Role: {role_e}")
        
        # Fetch Employee Dashboard
        headers_e = {"Authorization": f"Bearer {token_e}"}
        dashboard_resp_e = client.get(f"{BASE_URL}/api/employees/dashboard", headers=headers_e)
        if dashboard_resp_e.status_code == 200:
            dash_data_e = dashboard_resp_e.json()
            print("Employee Dashboard Data Summary:")
            print(f"  Employee Name: {dash_data_e.get('employee', {}).get('full_name')}")
            print(f"  Code: {dash_data_e.get('employee', {}).get('employee_code')}")
            print(f"  Attendance status: {(dash_data_e.get('attendance_status') or {}).get('status')}")
            print(f"  Leave Summary Pending: {dash_data_e.get('leave_summary', {}).get('pending', 0)}")
        else:
            print("Failed to fetch Employee dashboard:", dashboard_resp_e.text)

if __name__ == "__main__":
    test_login_and_fetch()

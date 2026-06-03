import requests

# 1. Login as HR
login_res = requests.post("http://127.0.0.1:8000/api/auth/login", json={"username": "Advaith", "password": "Pass123!"})
if login_res.status_code != 200:
    print("HR Login Failed:", login_res.text)
    exit(1)

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Hire application ID 15
hire_payload = {
    "department": "Engineering",
    "designation": "AI/ML Engineer",
    "salary": 1200000,
    "joining_date": "2026-07-01",
    "employee_code": "TF-99999"
}

hire_res = requests.post("http://127.0.0.1:8000/api/applications/15/hire", json=hire_payload, headers=headers)
print("Hire Status Code:", hire_res.status_code)
print("Hire Response:", hire_res.json() if hire_res.status_code in (200, 201) else hire_res.text)

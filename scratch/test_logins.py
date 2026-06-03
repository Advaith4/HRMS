import requests

users = [
    ("Advaith", "Pass123!"),
    ("advaithg", "Pass123!"),
    ("manager", "Pass123!"),
    ("candidate", "Pass123!"),
]

for username, password in users:
    try:
        res = requests.post("http://127.0.0.1:8000/api/auth/login", json={"username": username, "password": password})
        print(f"User: {username} | Status: {res.status_code} | Response: {res.json() if res.status_code == 200 else res.text}")
    except Exception as e:
        print(f"User: {username} | Error: {e}")

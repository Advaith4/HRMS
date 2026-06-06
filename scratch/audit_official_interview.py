import requests
import json

base_url = 'http://localhost:8000'

res = requests.post(f'{base_url}/api/auth/login', json={'username': 'candidate_test_1', 'password': 'Pass123!'})
token = res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Complete the previous session
res = requests.get(f'{base_url}/api/interview/sessions', headers=headers)
sessions = res.json()
session_id = sessions[0]['session_id']

print('Completing session ID:', session_id)
res = requests.post(f'{base_url}/api/interview/{session_id}/complete', headers=headers)
print('Complete status:', res.status_code)
print(res.text)

# Check status
res = requests.get(f'{base_url}/api/dashboard/candidate', headers=headers)
dash = res.json()
print("Dashboard status:", dash.get("interview_status"))

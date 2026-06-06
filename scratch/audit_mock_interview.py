import requests
import json
import time

base_url = 'http://localhost:8000'

res = requests.post(f'{base_url}/api/auth/login', json={'username': 'candidate_test_1', 'password': 'Pass123!'})
token = res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

print('Starting mock interview...')
res = requests.post(f'{base_url}/api/mock-interview/start', json={'role': 'Backend Developer', 'difficulty': 5}, headers=headers)
if res.status_code != 200:
    print('Start failed:', res.text)
    exit(1)
    
session_id = res.json()['session_id']
print('Session ID:', session_id)

# Submit answers
for i in range(3):
    print(f'\\nSubmitting turn {i+1}...')
    ans_res = requests.post(f'{base_url}/api/mock-interview/answer', json={'session_id': session_id, 'answer': 'I built REST APIs using FastAPI and deployed them.'}, headers=headers)
    print(f'Turn {i+1} status:', ans_res.status_code)
    if ans_res.status_code != 200:
        print('Error JSON:')
        try:
            print(json.dumps(ans_res.json(), indent=2))
        except:
            print(ans_res.text)
        break
    else:
        print('Next q:', ans_res.json().get('next_question'))

print('\\nCompleting mock interview...')
res = requests.post(f'{base_url}/api/mock-interview/{session_id}/complete', headers=headers)
print('Complete status:', res.status_code)
print(res.text)

print('\\nDone.')

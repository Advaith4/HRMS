import requests
import json
import traceback

base_url = 'http://localhost:8000'

# First, log in as a candidate to get a token.
username = 'admin' # admin might bypass some checks? Let's use candidate_123
res = requests.post(f'{base_url}/api/auth/login', json={'username': 'candidate_test_1', 'password': 'Pass123!'})
if res.status_code != 200:
    res = requests.post(f'{base_url}/api/auth/register', json={'username': 'candidate_test_1', 'password': 'Pass123!'})
    if res.status_code != 201:
        print('Could not register or login:', res.text)
        exit(1)
token = res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Start interview
# We need to start an official interview or a mock interview
# Mock interview is easier to start
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

print('\\nDone.')

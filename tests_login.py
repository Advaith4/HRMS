import time
import requests

base = 'http://127.0.0.1:8000'

def wait_for_server(url, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            return True
        except requests.RequestException:
            time.sleep(1)
    return False

if not wait_for_server(base):
    print('SERVER_NOT_READY: backend did not respond on', base)
    raise SystemExit(1)

print('Registering...')
try:
    r = requests.post(base + '/api/auth/register', json={'username': 'testuser', 'password': 'password123'}, timeout=10)
    print('REG', r.status_code, r.text)
except Exception as e:
    print('REG ERROR', e)

print('Logging in...')
try:
    r2 = requests.post(base + '/api/auth/login', json={'username': 'testuser', 'password': 'password123'}, timeout=10)
    print('LOGIN', r2.status_code, r2.text)
except Exception as e:
    print('LOGIN ERROR', e)

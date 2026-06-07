import requests
try:
    r = requests.get('http://127.0.0.1:8000', timeout=5)
    print('BACKEND', r.status_code)
    print(r.text[:300])
except Exception as e:
    print('BACKEND ERROR', e)

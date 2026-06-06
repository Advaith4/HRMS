import requests
base='http://127.0.0.1:8000'
print('Registering...')
try:
    r=requests.post(base+'/api/auth/register', json={'username':'testuser','password':'password123'})
    print('REG', r.status_code, r.text)
except Exception as e:
    print('REG ERROR', e)
print('Logging in...')
try:
    r2=requests.post(base+'/api/auth/login', json={'username':'testuser','password':'password123'})
    print('LOGIN', r2.status_code, r2.text)
except Exception as e:
    print('LOGIN ERROR', e)

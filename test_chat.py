#!/usr/bin/env python
import urllib.request
import urllib.error
import json

url = 'http://127.0.0.1:8000/api/chat'
data = json.dumps({'message': '你好，请简要介绍一下你自己'}).encode('utf-8')
req = urllib.request.Request(
    url, 
    data=data, 
    method='POST', 
    headers={
        'Content-Type': 'application/json', 
        'Origin': 'http://localhost:4173'
    }
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print('POST Status:', r.status)
        print('Response Headers:', dict(r.headers))
        content = r.read().decode('utf-8')
        lines = content.split('\n\n')
        for i, line in enumerate(lines[:10]):
            if line.strip():
                print(f'Event {i}: {line[:150]}')
except urllib.error.HTTPError as e:
    print('ERROR', e.code)
    print(e.read().decode()[:500])
except Exception as e:
    import traceback
    traceback.print_exc()

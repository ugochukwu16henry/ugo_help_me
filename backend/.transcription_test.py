from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    ts = client.get('/transcription/status')
    mock = client.post('/transcription/mock', json={'text': 'What did I build in my previous role?'})
    runtime = client.get('/brain/runtime/status')
    ask = client.post('/brain/ask', json={'question': 'What did I build in my previous role?'})
    print('transcription_status', ts.status_code, ts.json())
    print('transcription_mock', mock.status_code, mock.json())
    print('runtime', runtime.status_code, runtime.json())
    print('ask', ask.status_code, ask.json().keys())
print('transcription-smoke-ok')

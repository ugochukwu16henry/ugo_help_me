from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    before = client.get('/transcription/status').json()
    client.post('/transcription/mock', json={'text': 'Can you hear this test question?'})
    after = client.get('/transcription/status').json()
    print('before_last', before.get('last_transcript'))
    print('after_last', after.get('last_transcript'))
print('transcript-preview-smoke-ok')

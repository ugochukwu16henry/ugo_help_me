from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

docs_dir = Path('data/my_docs')
docs_dir.mkdir(parents=True, exist_ok=True)
test_file = docs_dir / 'delete_me_test.txt'
test_file.write_text('delete this file', encoding='utf-8')

with TestClient(app) as client:
    r = client.post('/rag/documents/delete', json={'selected_docs': ['delete_me_test.txt']})
    print('status', r.status_code)
    print('body', r.json())

print('exists_after', test_file.exists())

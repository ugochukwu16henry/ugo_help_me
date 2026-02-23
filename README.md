# UGO Assist

This workspace contains:

- `frontend/` — Electron overlay UI.
- `backend/` — Python backend (ingestion, RAG, orchestration, WebSocket API).

## Current status

- Stage-by-stage implementation plan is in `IMPLEMENTATION_PLAN.md`.
- Initial runnable scaffold is included for Stage 1 + Stage 3 foundation.

## Quick start

### 1) Frontend

```bash
cd frontend
npm install
npm run dev
```

### 2) Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8765
```

The Electron renderer expects backend WebSocket endpoint:

- `ws://127.0.0.1:8765/ws/overlay`

## Implemented so far

- Stage 1 foundation: Electron transparent always-on-top overlay, click-through, content protection enabled.
- Stage 3 foundation: Document load + chunk + local Chroma persistence and retrieval.
- Stage 4 foundation: Trigger logic API (`?` and silence tick path) + WebSocket push to overlay.
- Stage 2 currently scaffolded: threaded audio/screen worker service classes are in place and ready for real capture integration.

## API smoke checks

After backend starts:

```bash
curl http://127.0.0.1:8765/health
curl -X POST http://127.0.0.1:8765/rag/build
curl -X POST http://127.0.0.1:8765/brain/ask -H "Content-Type: application/json" -d "{\"question\":\"What projects did I lead?\"}"
```

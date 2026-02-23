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
- Stage 4 runtime wiring: background brain runtime loop continuously processes transcript queue and silence triggers, then pushes answers to overlay.
- Stage 2 completed: real ingestion services for center-zone screen capture (`mss`) and dual audio source capture (mic + WASAPI loopback via `pyaudiowpatch`) with start/stop/status controls.
- Ingestion starts manually through API (`/ingestion/start`) to keep startup stable across environments.
- Native audio capture is disabled by default for stability. Set `enable_native_audio_capture=true` in config when you want real WASAPI mic/loopback capture.

## API smoke checks

After backend starts:

```bash
curl http://127.0.0.1:8765/health
curl -X POST http://127.0.0.1:8765/rag/build
curl -X POST http://127.0.0.1:8765/brain/ask -H "Content-Type: application/json" -d "{\"question\":\"What projects did I lead?\"}"
curl -X POST http://127.0.0.1:8765/brain/ingest -H "Content-Type: application/json" -d "{\"text\":\"Can you summarize my biggest project?\"}"
curl http://127.0.0.1:8765/brain/runtime/status
curl http://127.0.0.1:8765/ingestion/status
curl -X POST http://127.0.0.1:8765/ingestion/stop
curl -X POST http://127.0.0.1:8765/ingestion/start
```

## Screen focus control

You can choose exactly what the app reads from the screen:

- Full monitor capture
- Center focus region (ratio)
- Custom focus rectangle (left/top/width/height)

Examples:

```bash
curl http://127.0.0.1:8765/ingestion/screen/monitors
curl http://127.0.0.1:8765/ingestion/screen/focus

curl -X POST http://127.0.0.1:8765/ingestion/screen/focus -H "Content-Type: application/json" -d "{\"mode\":\"full\",\"monitor_index\":1}"
curl -X POST http://127.0.0.1:8765/ingestion/screen/focus -H "Content-Type: application/json" -d "{\"mode\":\"center\",\"monitor_index\":1,\"ratio\":0.6}"
curl -X POST http://127.0.0.1:8765/ingestion/screen/focus -H "Content-Type: application/json" -d "{\"mode\":\"custom\",\"monitor_index\":1,\"left\":300,\"top\":200,\"width\":900,\"height\":500}"
```

## Overlay controls

- The overlay remains click-through by default.
- Press `Ctrl+Shift+H` to hide/show overlay instantly.
- Press `Ctrl+Shift+I` to unlock interaction and use built-in controls.
- Closing the window sends it to background (system tray) instead of fully exiting.
- Use tray icon menu to show/hide overlay, lock/unlock controls, or quit.
- Controls available in overlay:
  - start/stop ingestion
  - set focus mode (`full`, `center`, `custom`)
  - apply custom region values
- Press `Ctrl+Shift+I` again (or click `Lock`) to return to click-through mode.

# UGO Assist — Stage-by-Stage Implementation Plan

## 1) Consolidated Requirements (from provided docs)

- Frontend must be an **Electron overlay** that stays click-through (`pointer-events: none`) and supports OS content protection.
- Backend must run **high-speed ingestion**:
  - Screen capture (optimized region, not full screen).
  - Microphone + system audio loopback (Windows WASAPI loopback path).
  - Fast transcription pipeline (streaming-first design).
- Knowledge base must use **RAG** over personal documents with local persistent vector storage.
- Orchestration must be concurrent and non-blocking, with trigger logic to avoid unnecessary LLM calls.
- End-to-end goals:
  - Fast latency (target from question end to on-screen answer within ~3 seconds).
  - Accurate persona-grounded responses from personal documents.
  - Stability under long-running sessions.

---

## 2) Target Architecture

### Frontend (Electron)

- Transparent always-on-top overlay window.
- Content protection enabled via `BrowserWindow.setContentProtection(true)`.
- Renderer receives answer updates in real-time via WebSocket.
- Minimal UI: answer text panel + status indicators (capture/transcribe/rag/llm).

### Backend (Python)

- `ingestion/`:
  - `screen_capture.py` (MSS, configurable capture zone).
  - `audio_capture.py` (mic + loopback producer queues).
  - `transcription.py` (streaming transcription worker abstraction).
- `rag/`:
  - `build_index.py` (load/split/embed/store documents).
  - `retriever.py` (top-k retrieval by query).
- `brain/`:
  - trigger logic (`?` detection + silence window).
  - prompt assembly with persona instruction + retrieved chunks.
  - LLM response generation.
- `transport/`:
  - WebSocket server for pushing live updates to Electron.

### Data/Config

- `.env` for keys and model choices.
- `config.yaml` for thresholds (silence_ms, top_k, capture region, etc.).
- `data/my_docs/` for personal source docs.
- `data/chroma_db/` for persisted vectors.

---

## 3) Delivery Stages

## Stage A — Foundation & Scaffolding (Day 1)

**Goal:** repo bootstrapped and runnable skeleton.

Deliverables:

- Folder structure for `frontend/` and `backend/`.
- Python dependency manifests and Electron package setup.
- Shared config and startup scripts.

Acceptance:

- `npm run dev` launches overlay shell.
- backend process starts and logs health endpoint / WS endpoint.

## Stage B — Overlay (Stage 1 Spec)

**Goal:** Ghost-style overlay behavior is working.

Deliverables:

- Transparent frameless always-on-top window.
- `setContentProtection(true)` enabled.
- Click-through mode for non-interactive display.
- Simple renderer component for streamed text.

Acceptance:

- Overlay visible locally.
- Overlay updates text from backend WS messages.

## Stage C — Ingestion (Stage 2 Spec)

**Goal:** low-latency input from audio + screen.

Deliverables:

- Screen region capture worker (MSS).
- Microphone stream worker.
- System loopback worker abstraction with Windows strategy path.
- Unified queue/event bus for transcribed segments.

Acceptance:

- Ingestion services run concurrently.
- Events are timestamped and emitted to orchestrator.

## Stage D — RAG Memory (Stage 3 Spec)

**Goal:** personal knowledge retrieval is reliable.

Deliverables:

- Document ingestion pipeline (pdf/docx/txt).
- Chunking with overlap.
- Embedding + Chroma persistent collection.
- Retriever API returning top-k chunks + metadata.

Acceptance:

- Query with niche term returns matching document chunk.
- Index persists between restarts.

## Stage E — Brain Orchestration (Stage 4 Spec)

**Goal:** complete question-to-answer loop.

Deliverables:

- Trigger logic (`?` + silence > threshold).
- Prompt composer (persona + retrieved context + live transcript).
- LLM call worker with timeout and retries.
- WebSocket push of generated answer to overlay.

Acceptance:

- In test flow, question triggers answer generation and appears in overlay.
- Trigger suppression avoids excessive calls.

## Stage F — Hardening & Validation

**Goal:** measurable performance and robustness.

Deliverables:

- Latency instrumentation end-to-end.
- Memory watchdog for long sessions.
- Config tuning guide (top_k, chunk size, silence threshold).

Acceptance:

- Stable 2-hour run without crash.
- Meets functional latency and relevance checks.

---

## 4) Implementation Order (practical)

1. Build skeleton + WS transport first.
2. Implement overlay and verify live text updates.
3. Add ingestion workers with mocked transcription.
4. Add RAG pipeline and verify retrieval quality.
5. Integrate real transcription + LLM in orchestrator.
6. Add instrumentation and optimize bottlenecks.

---

## 5) Immediate Work Starting Now

In this session, we will implement:

1. Project skeleton (`frontend` + `backend`).
2. Electron overlay window with content protection and live WS text rendering.
3. Python backend WebSocket server + orchestrator skeleton.
4. Stage 3 RAG foundation (document loading, chunking, local Chroma persistence, retriever endpoint).
5. Run instructions and next implementation tasks.

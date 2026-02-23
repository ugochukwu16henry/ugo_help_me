from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import HTTPException

from app.brain.orchestrator import brain
from app.brain.runtime import brain_runtime
from app.ingestion.manager import ingestion_manager
from app.models import (
    BuildIndexResponse,
    QueryRequest,
    ScreenFocusRequest,
    TranscriptSegmentRequest,
)
from app.rag.service import rag_service
from app.transcription.service import TranscriptionService
from app.transport.overlay_hub import overlay_hub

app = FastAPI(title="UGO Assist Backend")
transcription_service = TranscriptionService(ingestion_manager, brain_runtime)


@app.on_event("startup")
async def startup_event():
    await brain_runtime.start()
    await transcription_service.start()


@app.on_event("shutdown")
async def shutdown_event():
    await transcription_service.stop()
    await brain_runtime.stop()
    ingestion_manager.stop()


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/rag/build", response_model=BuildIndexResponse)
async def build_rag_index():
    count = rag_service.build_index()
    return BuildIndexResponse(indexed_chunks=count)


@app.post("/brain/ask")
async def ask_brain(payload: QueryRequest):
    answer = brain.answer_question(payload.question)
    await overlay_hub.broadcast({"type": "answer", "message": answer})
    return {"answer": answer}


@app.post("/brain/ingest")
async def ingest_segment(payload: TranscriptSegmentRequest):
    await brain_runtime.submit_transcript(payload.text)
    return {"queued": True, "runtime": brain_runtime.status()}


@app.post("/brain/silence-tick")
async def silence_tick():
    maybe_answer = brain.on_silence_tick()
    if maybe_answer:
        await overlay_hub.broadcast({"type": "answer", "message": maybe_answer})
    return {"triggered": bool(maybe_answer)}


@app.get("/brain/runtime/status")
async def brain_runtime_status():
    return brain_runtime.status()


@app.get("/transcription/status")
async def transcription_status():
    return transcription_service.status()


@app.post("/transcription/mock")
async def transcription_mock(payload: TranscriptSegmentRequest):
    await transcription_service.submit_mock_text(payload.text)
    return {"queued": True, "runtime": brain_runtime.status()}


@app.get("/ingestion/status")
async def ingestion_status():
    return ingestion_manager.status()


@app.post("/ingestion/start")
async def ingestion_start():
    ingestion_manager.start()
    return {"started": True, "status": ingestion_manager.status()}


@app.post("/ingestion/stop")
async def ingestion_stop():
    ingestion_manager.stop()
    return {"stopped": True, "status": ingestion_manager.status()}


@app.get("/ingestion/screen/focus")
async def get_screen_focus():
    return ingestion_manager.get_screen_focus()


@app.post("/ingestion/screen/focus")
async def set_screen_focus(payload: ScreenFocusRequest):
    try:
        focus = ingestion_manager.set_screen_focus(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"focus": focus}


@app.get("/ingestion/screen/monitors")
async def list_screen_monitors():
    return {"monitors": ingestion_manager.list_monitors()}


@app.websocket("/ws/overlay")
async def ws_overlay(websocket: WebSocket):
    await overlay_hub.connect(websocket)
    await overlay_hub.broadcast({"type": "status", "message": "Backend connected"})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await overlay_hub.disconnect(websocket)

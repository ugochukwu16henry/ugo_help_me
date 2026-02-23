from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import HTTPException
from fastapi import File, UploadFile

from app.brain.orchestrator import brain
from app.brain.runtime import brain_runtime
from app.config import settings
from app.ingestion.manager import ingestion_manager
from app.models import (
    DocumentSelectionRequest,
    BuildIndexResponse,
    QueryRequest,
    ScreenFocusRequest,
    TranscriptSegmentRequest,
)
from app.rag.service import rag_service
from app.transcription.service import TranscriptionService
from app.transport.overlay_hub import overlay_hub

app = FastAPI(title="UGO Assist Backend")
transcription_service = TranscriptionService(ingestion_manager, brain_runtime, overlay_hub)

ALLOWED_DOC_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _safe_destination(filename: str) -> Path:
    safe_name = Path(filename or "upload.bin").name
    stem = Path(safe_name).stem or "upload"
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_DOC_EXTENSIONS:
        raise ValueError("Unsupported file type. Allowed: .pdf, .docx, .txt")

    docs_dir = settings.docs_dir
    docs_dir.mkdir(parents=True, exist_ok=True)

    destination = docs_dir / f"{stem}{suffix}"
    counter = 1
    while destination.exists():
        destination = docs_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return destination


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


@app.post("/rag/upload")
async def rag_upload(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    saved: list[str] = []
    rejected: list[str] = []

    for file in files:
        try:
            destination = _safe_destination(file.filename or "")
        except ValueError:
            rejected.append(file.filename or "unknown")
            continue

        content = await file.read()
        destination.write_bytes(content)
        saved.append(destination.name)

    return {
        "uploaded": saved,
        "rejected": rejected,
        "available": rag_service.list_available_docs(),
    }


@app.get("/rag/documents")
async def rag_documents() -> dict:
    return {
        "available": rag_service.list_available_docs(),
        "selected": rag_service.get_selected_docs(),
    }


@app.post("/rag/documents/select")
async def rag_documents_select(payload: DocumentSelectionRequest) -> dict:
    selected = rag_service.set_selected_docs(payload.selected_docs)
    return {
        "selected": selected,
        "available": rag_service.list_available_docs(),
    }


@app.post("/rag/documents/delete")
async def rag_documents_delete(payload: DocumentSelectionRequest) -> dict:
    if not payload.selected_docs:
        raise HTTPException(status_code=400, detail="No documents selected for deletion")
    return rag_service.delete_docs(payload.selected_docs)


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

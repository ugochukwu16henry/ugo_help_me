import asyncio
from queue import Empty
from typing import Any

from app.config import settings

try:
    import numpy as np
except Exception:
    np = None

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None


class ScreenOCRService:
    def __init__(self, ingestion_manager, brain_runtime, overlay_hub) -> None:
        self.ingestion_manager = ingestion_manager
        self.brain_runtime = brain_runtime
        self.overlay_hub = overlay_hub

        self._task: asyncio.Task | None = None
        self._running = False
        self._ocr_engine: Any = None
        self._last_error: str | None = None
        self._last_text: str = ""
        self._last_raw_text: str = ""
        self._frames_seen = 0
        self._frames_processed = 0
        self._last_submitted_text: str = ""

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    def status(self) -> dict:
        return {
            "running": bool(self._task and not self._task.done()),
            "enabled": settings.enable_screen_ocr,
            "engine_ready": self._ocr_engine is not None,
            "frames_seen": self._frames_seen,
            "frames_processed": self._frames_processed,
            "last_text": self._last_text,
            "last_raw_text": self._last_raw_text,
            "last_error": self._last_error,
        }

    def latest_text(self, relaxed: bool = False) -> str:
        if relaxed and self._last_raw_text:
            return self._last_raw_text
        return self._last_text

    async def _run(self) -> None:
        if not settings.enable_screen_ocr:
            return

        if RapidOCR is None or np is None:
            self._last_error = "rapidocr-onnxruntime or numpy unavailable"
            while self._running:
                await asyncio.sleep(0.5)
            return

        try:
            self._ocr_engine = RapidOCR()
        except Exception as exc:
            self._last_error = f"ocr init failed: {exc}"
            while self._running:
                await asyncio.sleep(0.5)
            return

        interval = max(120, int(settings.screen_ocr_interval_ms)) / 1000.0

        while self._running:
            latest_event = None
            while True:
                try:
                    latest_event = self.ingestion_manager.screen_events.get_nowait()
                except Empty:
                    break

            if latest_event is None:
                await asyncio.sleep(0.1)
                continue

            self._frames_seen += 1
            text = await asyncio.to_thread(self._extract_text, latest_event)
            if text:
                self._last_raw_text = text

            if text and len(text) >= int(settings.screen_ocr_min_chars) and text != self._last_text:
                self._last_text = text
                await self.overlay_hub.broadcast(
                    {"type": "transcript", "message": f"[screen] {text}", "source": "screen"}
                )

                if self._should_submit_to_brain(text):
                    await self.brain_runtime.submit_transcript(text)
                    self._last_submitted_text = text

            await asyncio.sleep(interval)

    def _extract_text(self, event) -> str:
        if self._ocr_engine is None:
            return ""

        width = int(getattr(event, "width", 0) or 0)
        height = int(getattr(event, "height", 0) or 0)
        frame = getattr(event, "frame", b"") or b""
        if width <= 0 or height <= 0 or not frame:
            return ""

        expected_len = width * height * 3
        if len(frame) < expected_len:
            return ""

        try:
            image = np.frombuffer(frame, dtype=np.uint8)[:expected_len].reshape((height, width, 3))
            result, _ = self._ocr_engine(image)
        except Exception as exc:
            self._last_error = str(exc)
            return ""

        self._frames_processed += 1
        if not result:
            return ""

        texts = []
        for item in result:
            if not item or len(item) < 2:
                continue
            text = str(item[1] or "").strip()
            if text:
                texts.append(text)

        merged = " ".join(texts).strip()
        return merged

    def _should_submit_to_brain(self, text: str) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return False

        if cleaned == self._last_submitted_text:
            return False

        lowered = cleaned.lower()
        if "?" in lowered:
            return True

        keywords = (
            "implement",
            "write a function",
            "build",
            "create",
            "solve",
            "task",
            "problem",
            "leetcode",
            "algorithm",
            "bug",
            "fix",
            "refactor",
            "optimize",
            "explain",
        )
        return any(token in lowered for token in keywords)

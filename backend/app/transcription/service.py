import asyncio
from queue import Empty
from typing import Any

from app.config import settings

try:
    import numpy as np
except Exception:
    np = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None


class TranscriptionService:
    def __init__(self, ingestion_manager, brain_runtime) -> None:
        self.ingestion_manager = ingestion_manager
        self.brain_runtime = brain_runtime
        self._task: asyncio.Task | None = None
        self._running = False
        self._model: Any = None
        self._last_error: str | None = None
        self._segments_seen = 0
        self._segments_transcribed = 0
        self._buffer = bytearray()
        self._window_bytes = int(
            settings.audio_sample_rate
            * max(1, settings.audio_channels)
            * 2
            * settings.transcription_min_seconds
        )

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

    async def submit_mock_text(self, text: str) -> None:
        await self.brain_runtime.submit_transcript(text)

    def status(self) -> dict:
        return {
            "running": bool(self._task and not self._task.done()),
            "enabled": settings.enable_transcription,
            "model_ready": self._model is not None,
            "segments_seen": self._segments_seen,
            "segments_transcribed": self._segments_transcribed,
            "last_error": self._last_error,
        }

    async def _run(self) -> None:
        if not settings.enable_transcription:
            return

        if WhisperModel is None or np is None:
            self._last_error = "faster-whisper or numpy unavailable"
            while self._running:
                await asyncio.sleep(0.5)
            return

        try:
            self._model = WhisperModel(
                settings.transcription_model_size,
                compute_type=settings.transcription_compute_type,
            )
        except Exception as exc:
            self._last_error = f"model init failed: {exc}"
            while self._running:
                await asyncio.sleep(0.5)
            return

        while self._running:
            consumed_any = False
            while True:
                try:
                    event = self.ingestion_manager.audio_events.get_nowait()
                except Empty:
                    break

                consumed_any = True
                self._segments_seen += 1
                payload = getattr(event, "payload", b"") or b""
                if not payload:
                    continue

                if self._energy(payload) < settings.vad_energy_threshold:
                    continue

                self._buffer.extend(payload)
                if len(self._buffer) >= self._window_bytes:
                    chunk = bytes(self._buffer)
                    self._buffer.clear()
                    text = await asyncio.to_thread(self._transcribe_bytes, chunk)
                    if text:
                        self._segments_transcribed += 1
                        await self.brain_runtime.submit_transcript(text)

            if not consumed_any:
                await asyncio.sleep(0.08)

    def _energy(self, payload: bytes) -> int:
        if len(payload) < 4:
            return 0
        view = memoryview(payload)
        sample_count = len(view) // 2
        if sample_count == 0:
            return 0

        samples = view[: sample_count * 2].cast("h")
        total = 0
        for sample in samples:
            total += abs(int(sample))
        return int(total / sample_count)

    def _transcribe_bytes(self, payload: bytes) -> str:
        if self._model is None:
            return ""

        sample_count = len(payload) // 2
        if sample_count == 0:
            return ""

        audio_int16 = np.frombuffer(payload, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(
            audio_float,
            language="en",
            beam_size=1,
            vad_filter=True,
        )
        text = " ".join((segment.text or "").strip() for segment in segments).strip()
        return text

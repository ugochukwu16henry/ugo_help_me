import asyncio

from app.brain.orchestrator import brain
from app.transport.overlay_hub import overlay_hub


class BrainRuntime:
    def __init__(self) -> None:
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def submit_transcript(self, text: str) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return

        if self._transcript_queue.full():
            try:
                self._transcript_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        await self._transcript_queue.put(cleaned)

    def status(self) -> dict:
        return {
            "running": bool(self._task and not self._task.done()),
            "queue_size": self._transcript_queue.qsize(),
        }

    async def _run_loop(self) -> None:
        while self._running:
            try:
                segment = await asyncio.wait_for(self._transcript_queue.get(), timeout=0.25)
                answer = brain.ingest_transcript_segment(segment)
                if answer:
                    await overlay_hub.broadcast({"type": "answer", "message": answer})
            except asyncio.TimeoutError:
                pass

            answer = brain.on_silence_tick()
            if answer:
                await overlay_hub.broadcast({"type": "answer", "message": answer})


brain_runtime = BrainRuntime()

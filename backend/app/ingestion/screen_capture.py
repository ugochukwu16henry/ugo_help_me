import threading
import time
from dataclasses import dataclass
from queue import Queue
from typing import Any


@dataclass
class ScreenFrameEvent:
    ts: float
    frame: Any


class ScreenCaptureService:
    def __init__(self, event_queue: Queue, interval_ms: int = 120) -> None:
        self.event_queue = event_queue
        self.interval_ms = interval_ms
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.event_queue.put(ScreenFrameEvent(ts=time.time(), frame=None))
            time.sleep(self.interval_ms / 1000)


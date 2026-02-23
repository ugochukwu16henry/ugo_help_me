import threading
import time
from dataclasses import dataclass
from queue import Queue


@dataclass
class AudioEvent:
    ts: float
    source: str
    payload: bytes


class AudioCaptureService:
    def __init__(self, event_queue: Queue, chunk_ms: int = 100) -> None:
        self.event_queue = event_queue
        self.chunk_ms = chunk_ms
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if any(worker.is_alive() for worker in self._threads):
            return

        self._stop_event.clear()
        self._threads = [
            threading.Thread(target=self._run_source, args=("mic",), daemon=True),
            threading.Thread(target=self._run_source, args=("loopback",), daemon=True),
        ]

        for worker in self._threads:
            worker.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run_source(self, source: str) -> None:
        while not self._stop_event.is_set():
            self.event_queue.put(AudioEvent(ts=time.time(), source=source, payload=b""))
            time.sleep(self.chunk_ms / 1000)


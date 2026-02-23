import threading
import time
from dataclasses import dataclass
from queue import Queue
from typing import Any


try:
    from mss import mss
except Exception:
    mss = None


@dataclass
class ScreenFrameEvent:
    ts: float
    frame: Any
    width: int
    height: int


@dataclass
class ScreenCaptureStatus:
    running: bool
    backend: str
    frames_captured: int
    last_error: str | None


class ScreenCaptureService:
    def __init__(
        self,
        event_queue: Queue,
        interval_ms: int = 120,
        zone_ratio: float = 0.6,
    ) -> None:
        self.event_queue = event_queue
        self.interval_ms = interval_ms
        self.zone_ratio = max(0.1, min(zone_ratio, 1.0))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.frames_captured = 0
        self.last_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def status(self) -> ScreenCaptureStatus:
        return ScreenCaptureStatus(
            running=bool(self._thread and self._thread.is_alive()),
            backend="mss" if mss else "stub",
            frames_captured=self.frames_captured,
            last_error=self.last_error,
        )

    def _capture_zone(self, monitor: dict) -> dict:
        width = int(monitor["width"] * self.zone_ratio)
        height = int(monitor["height"] * self.zone_ratio)
        left = monitor["left"] + (monitor["width"] - width) // 2
        top = monitor["top"] + (monitor["height"] - height) // 2
        return {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }

    def _run(self) -> None:
        if not mss:
            self.last_error = "mss is not installed; screen capture is running in stub mode"
            while not self._stop_event.is_set():
                self.event_queue.put(
                    ScreenFrameEvent(ts=time.time(), frame=None, width=0, height=0)
                )
                self.frames_captured += 1
                time.sleep(self.interval_ms / 1000)
            return

        try:
            with mss() as screen:
                monitor = screen.monitors[1]
                region = self._capture_zone(monitor)

                while not self._stop_event.is_set():
                    shot = screen.grab(region)
                    self.event_queue.put(
                        ScreenFrameEvent(
                            ts=time.time(),
                            frame=shot.rgb,
                            width=shot.width,
                            height=shot.height,
                        )
                    )
                    self.frames_captured += 1
                    time.sleep(self.interval_ms / 1000)
        except Exception as exc:
            self.last_error = str(exc)


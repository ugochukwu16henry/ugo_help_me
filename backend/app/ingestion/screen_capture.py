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
    focus: dict


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
        self.focus_mode = "center"
        self.monitor_index = 1
        self.custom_region: dict | None = None
        self._stop_event = threading.Event()
        self._focus_lock = threading.RLock()
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
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def status(self) -> ScreenCaptureStatus:
        return ScreenCaptureStatus(
            running=bool(self._thread and self._thread.is_alive()),
            backend="mss" if mss else "stub",
            frames_captured=self.frames_captured,
            last_error=self.last_error,
            focus=self.get_focus(),
        )

    def get_focus(self) -> dict:
        with self._focus_lock:
            return {
                "mode": self.focus_mode,
                "monitor_index": self.monitor_index,
                "ratio": self.zone_ratio,
                "custom_region": self.custom_region,
            }

    def set_focus_full(self, monitor_index: int = 1) -> dict:
        with self._focus_lock:
            self.focus_mode = "full"
            self.monitor_index = max(1, monitor_index)
            self.custom_region = None
            return self.get_focus()

    def set_focus_center(self, ratio: float = 0.6, monitor_index: int = 1) -> dict:
        with self._focus_lock:
            self.focus_mode = "center"
            self.zone_ratio = max(0.1, min(ratio, 1.0))
            self.monitor_index = max(1, monitor_index)
            self.custom_region = None
            return self.get_focus()

    def set_focus_custom(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        monitor_index: int = 1,
    ) -> dict:
        region = {
            "left": max(0, int(left)),
            "top": max(0, int(top)),
            "width": max(1, int(width)),
            "height": max(1, int(height)),
        }
        with self._focus_lock:
            self.focus_mode = "custom"
            self.monitor_index = max(1, monitor_index)
            self.custom_region = region
            return self.get_focus()

    def monitors(self) -> list[dict]:
        if not mss:
            return []
        try:
            with mss() as screen:
                result = []
                for idx, monitor in enumerate(screen.monitors):
                    if idx == 0:
                        continue
                    result.append(
                        {
                            "index": idx,
                            "left": monitor["left"],
                            "top": monitor["top"],
                            "width": monitor["width"],
                            "height": monitor["height"],
                        }
                    )
                return result
        except Exception:
            return []

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

    def _selected_monitor(self, monitors: list[dict], requested_index: int) -> dict:
        if requested_index < len(monitors):
            return monitors[requested_index]
        return monitors[1]

    def _effective_region(self, monitor: dict) -> dict:
        with self._focus_lock:
            mode = self.focus_mode
            custom = self.custom_region.copy() if self.custom_region else None

        if mode == "full":
            return {
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
            }

        if mode == "custom" and custom:
            left = monitor["left"] + custom["left"]
            top = monitor["top"] + custom["top"]
            max_width = max(1, monitor["width"] - custom["left"])
            max_height = max(1, monitor["height"] - custom["top"])
            return {
                "left": left,
                "top": top,
                "width": min(custom["width"], max_width),
                "height": min(custom["height"], max_height),
            }

        return self._capture_zone(monitor)

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
                while not self._stop_event.is_set():
                    with self._focus_lock:
                        monitor_index = self.monitor_index

                    monitor = self._selected_monitor(screen.monitors, monitor_index)
                    region = self._effective_region(monitor)
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


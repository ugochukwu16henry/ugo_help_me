from queue import Queue

from app.config import settings
from app.ingestion.audio_capture import AudioCaptureService
from app.ingestion.screen_capture import ScreenCaptureService


class IngestionManager:
    def __init__(self) -> None:
        self.audio_events: Queue = Queue(maxsize=1000)
        self.screen_events: Queue = Queue(maxsize=100)

        self.audio_service = AudioCaptureService(
            event_queue=self.audio_events,
            chunk_ms=settings.audio_chunk_ms,
            sample_rate=settings.audio_sample_rate,
            channels=settings.audio_channels,
            enable_native_capture=settings.enable_native_audio_capture,
        )
        self.screen_service = ScreenCaptureService(
            event_queue=self.screen_events,
            interval_ms=settings.screen_interval_ms,
            zone_ratio=settings.capture_zone_ratio,
        )

    def start(self) -> None:
        self.audio_service.start()
        self.screen_service.start()

    def stop(self) -> None:
        self.audio_service.stop()
        self.screen_service.stop()

    def status(self) -> dict:
        audio = self.audio_service.status()
        screen = self.screen_service.status()
        return {
            "audio": {
                "running": audio.running,
                "backend": audio.backend,
                "mic_chunks": audio.mic_chunks,
                "loopback_chunks": audio.loopback_chunks,
                "last_error": audio.last_error,
                "queue_size": self.audio_events.qsize(),
            },
            "screen": {
                "running": screen.running,
                "backend": screen.backend,
                "frames_captured": screen.frames_captured,
                "last_error": screen.last_error,
                "focus": screen.focus,
                "queue_size": self.screen_events.qsize(),
            },
        }

    def set_screen_focus(self, payload: dict) -> dict:
        mode = (payload.get("mode") or "").lower()
        monitor_index = int(payload.get("monitor_index", 1))

        if mode == "full":
            return self.screen_service.set_focus_full(monitor_index=monitor_index)

        if mode == "center":
            ratio = float(payload.get("ratio", settings.capture_zone_ratio))
            return self.screen_service.set_focus_center(
                ratio=ratio,
                monitor_index=monitor_index,
            )

        if mode == "custom":
            return self.screen_service.set_focus_custom(
                left=int(payload.get("left", 0)),
                top=int(payload.get("top", 0)),
                width=int(payload.get("width", 1)),
                height=int(payload.get("height", 1)),
                monitor_index=monitor_index,
            )

        raise ValueError("mode must be one of: full, center, custom")

    def get_screen_focus(self) -> dict:
        return self.screen_service.get_focus()

    def list_monitors(self) -> list[dict]:
        return self.screen_service.monitors()


ingestion_manager = IngestionManager()

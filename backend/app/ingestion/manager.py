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
                "queue_size": self.screen_events.qsize(),
            },
        }


ingestion_manager = IngestionManager()

import threading
import time
from dataclasses import dataclass
from queue import Queue


try:
    import pyaudiowpatch as pyaudio
except Exception:
    pyaudio = None


@dataclass
class AudioEvent:
    ts: float
    source: str
    payload: bytes


@dataclass
class AudioCaptureStatus:
    running: bool
    backend: str
    mic_chunks: int
    loopback_chunks: int
    last_error: str | None


class AudioCaptureService:
    def __init__(
        self,
        event_queue: Queue,
        chunk_ms: int = 100,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        self.event_queue = event_queue
        self.chunk_ms = chunk_ms
        self.sample_rate = sample_rate
        self.channels = channels
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self.mic_chunks = 0
        self.loopback_chunks = 0
        self.last_error: str | None = None

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

    def status(self) -> AudioCaptureStatus:
        return AudioCaptureStatus(
            running=any(worker.is_alive() for worker in self._threads),
            backend="pyaudiowpatch" if pyaudio else "stub",
            mic_chunks=self.mic_chunks,
            loopback_chunks=self.loopback_chunks,
            last_error=self.last_error,
        )

    def _run_source(self, source: str) -> None:
        if pyaudio is None:
            self._run_stub_source(source)
            return

        try:
            with pyaudio.PyAudio() as pa:
                device_index = (
                    self._find_default_loopback_device(pa)
                    if source == "loopback"
                    else None
                )

                frames_per_buffer = max(256, int(self.sample_rate * (self.chunk_ms / 1000)))

                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=frames_per_buffer,
                )

                while not self._stop_event.is_set():
                    data = stream.read(frames_per_buffer, exception_on_overflow=False)
                    self.event_queue.put(AudioEvent(ts=time.time(), source=source, payload=data))
                    if source == "mic":
                        self.mic_chunks += 1
                    else:
                        self.loopback_chunks += 1

                stream.stop_stream()
                stream.close()
        except Exception as exc:
            self.last_error = str(exc)
            self._run_stub_source(source)

    def _run_stub_source(self, source: str) -> None:
        if pyaudio is None:
            self.last_error = "pyaudiowpatch unavailable; running audio capture in stub mode"
        while not self._stop_event.is_set():
            self.event_queue.put(AudioEvent(ts=time.time(), source=source, payload=b""))
            if source == "mic":
                self.mic_chunks += 1
            else:
                self.loopback_chunks += 1
            time.sleep(self.chunk_ms / 1000)

    def _find_default_loopback_device(self, pa: "pyaudio.PyAudio") -> int | None:
        try:
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_output = pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            if default_output.get("isLoopbackDevice"):
                return int(default_output["index"])

            for loopback in pa.get_loopback_device_info_generator():
                if default_output["name"] in loopback["name"]:
                    return int(loopback["index"])
        except Exception as exc:
            self.last_error = str(exc)
        return None


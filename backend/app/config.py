import os
from pathlib import Path

from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    ws_path: str = "/ws/overlay"
    docs_dir: Path = DATA_DIR / "my_docs"
    chroma_path: Path = DATA_DIR / "chroma_db"
    collection_name: str = "personal_memory"
    chunk_size: int = 700
    chunk_overlap: int = 70
    top_k: int = 4
    silence_ms_trigger: int = 1500
    screen_interval_ms: int = 120
    capture_zone_ratio: float = 0.6
    audio_chunk_ms: int = 100
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    enable_native_audio_capture: bool = False
    enable_transcription: bool = True
    transcription_model_size: str = "base"
    transcription_compute_type: str = "int8"
    transcription_min_seconds: float = 1.6
    vad_energy_threshold: int = 450
    enable_screen_ocr: bool = True
    screen_ocr_interval_ms: int = 1200
    screen_ocr_min_chars: int = 12
    llm_provider: str = "auto"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    llm_timeout_seconds: int = 25


settings = Settings()

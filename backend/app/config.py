from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    ws_path: str = "/ws/overlay"
    docs_dir: Path = Path("data/my_docs")
    chroma_path: Path = Path("data/chroma_db")
    collection_name: str = "personal_memory"
    chunk_size: int = 700
    chunk_overlap: int = 70
    top_k: int = 4
    silence_ms_trigger: int = 1500


settings = Settings()

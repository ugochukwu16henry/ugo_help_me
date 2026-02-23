import time

from app.config import settings
from app.rag.service import rag_service


class BrainOrchestrator:
    def __init__(self) -> None:
        self._buffer: list[str] = []
        self._last_activity_ts: float = time.time()

    def ingest_transcript_segment(self, segment: str) -> str | None:
        cleaned = (segment or "").strip()
        if not cleaned:
            return None

        self._buffer.append(cleaned)
        self._last_activity_ts = time.time()

        if "?" in cleaned:
            question = self._collapse_buffer()
            return self.answer_question(question)

        return None

    def on_silence_tick(self) -> str | None:
        idle_ms = int((time.time() - self._last_activity_ts) * 1000)
        if idle_ms < settings.silence_ms_trigger:
            return None

        if not self._buffer:
            return None

        question = self._collapse_buffer()
        if not question.endswith("?"):
            return None

        return self.answer_question(question)

    def answer_question(self, question: str) -> str:
        context_chunks = rag_service.retrieve(question)

        if not context_chunks:
            return "No personal context retrieved yet. Build index and add docs to data/my_docs."

        context = "\n\n".join(context_chunks[:3])
        return (
            "Interview-style answer draft based on personal context:\n\n"
            f"Question: {question}\n\n"
            f"Relevant context:\n{context}"
        )

    def _collapse_buffer(self) -> str:
        text = " ".join(self._buffer).strip()
        self._buffer.clear()
        return text


brain = BrainOrchestrator()

import time

from app.config import settings
from app.llm.service import llm_service
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

        if "?" in cleaned or self._looks_like_question(cleaned):
            question = self._collapse_buffer()
            if not question.endswith("?"):
                question = f"{question} ?"
            return self.answer_question(question)

        return None

    def on_silence_tick(self) -> str | None:
        idle_ms = int((time.time() - self._last_activity_ts) * 1000)
        if idle_ms < settings.silence_ms_trigger:
            return None

        if not self._buffer:
            return None

        question = self._collapse_buffer()
        if not (question.endswith("?") or self._looks_like_question(question)):
            return None

        if not question.endswith("?"):
            question = f"{question} ?"

        return self.answer_question(question)

    def answer_question(self, question: str) -> str:
        context_chunks = rag_service.retrieve(question)
        context = "\n\n".join(context_chunks[:3]) if context_chunks else "No indexed personal context available."

        llm_answer = llm_service.generate(question=question, context=context)
        if llm_answer:
            return llm_answer

        if not context_chunks:
            return "No personal context retrieved yet and no LLM provider connected. Build index and connect OpenAI/Ollama."

        return (
            "Interview-style answer draft based on personal context:\n\n"
            f"Question: {question}\n\n"
            f"Relevant context:\n{context}"
        )

    def _looks_like_question(self, text: str) -> bool:
        lowered = (text or "").lower()
        keywords = (
            "implement",
            "write a function",
            "build",
            "create",
            "solve",
            "task",
            "problem",
            "leetcode",
            "algorithm",
            "bug",
            "fix",
            "refactor",
            "optimize",
            "explain",
        )
        return any(token in lowered for token in keywords)

    def _collapse_buffer(self) -> str:
        text = " ".join(self._buffer).strip()
        self._buffer.clear()
        return text


brain = BrainOrchestrator()

import json
import urllib.error
import urllib.request

from app.config import settings


class LLMService:
    def __init__(self) -> None:
        self._last_error: str | None = None

    def status(self) -> dict:
        provider = self._resolve_provider()
        available = provider in {"openai", "ollama"}
        return {
            "provider": provider,
            "available": available,
            "openai_configured": bool(settings.openai_api_key),
            "ollama_base_url": settings.ollama_base_url,
            "ollama_model": settings.ollama_model,
            "openai_model": settings.openai_model,
            "last_error": self._last_error,
        }

    def generate(self, question: str, context: str) -> str | None:
        provider = self._resolve_provider()

        if provider == "openai":
            try:
                return self._generate_openai(question, context)
            except Exception as exc:
                self._last_error = str(exc)
                return None

        if provider == "ollama":
            try:
                return self._generate_ollama(question, context)
            except Exception as exc:
                self._last_error = str(exc)
                return None

        self._last_error = "No LLM provider configured"
        return None

    def _resolve_provider(self) -> str:
        configured = (settings.llm_provider or "auto").lower().strip()

        if configured == "openai":
            return "openai" if settings.openai_api_key else "none"

        if configured == "ollama":
            return "ollama" if self._ollama_reachable() else "none"

        if settings.openai_api_key:
            return "openai"

        if self._ollama_reachable():
            return "ollama"

        return "none"

    def _ollama_reachable(self) -> bool:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        request = urllib.request.Request(url=url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def _generate_openai(self, question: str, context: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        prompt = self._build_prompt(question, context)
        payload = {
            "model": settings.openai_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an interview assistant. Give concise, practical coding-interview answers.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.openai_api_key}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            raise RuntimeError(f"OpenAI error {exc.code}: {error_body[:220]}") from exc

        parsed = json.loads(body)
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI returned no choices")

        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("OpenAI returned empty content")

        self._last_error = None
        return content

    def _generate_ollama(self, question: str, context: str) -> str:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
        model_name = self._resolve_ollama_model()
        payload = {
            "model": model_name,
            "prompt": self._build_prompt(question, context),
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 220},
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            raise RuntimeError(f"Ollama error {exc.code}: {error_body[:220]}") from exc

        parsed = json.loads(body)
        content = str(parsed.get("response") or "").strip()
        if not content:
            raise RuntimeError("Ollama returned empty response")

        self._last_error = None
        return content

    def _resolve_ollama_model(self) -> str:
        desired = (settings.ollama_model or "").strip()
        available = self._list_ollama_models()

        if desired and desired in available:
            return desired

        if available:
            return available[0]

        return desired or "llama3.2:3b"

    def _list_ollama_models(self) -> list[str]:
        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        request = urllib.request.Request(url=url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                body = response.read().decode("utf-8")
        except Exception:
            return []

        try:
            parsed = json.loads(body)
        except Exception:
            return []

        models = parsed.get("models") or []
        names: list[str] = []
        for model in models:
            name = str((model or {}).get("name") or "").strip()
            if name:
                names.append(name)
        return names

    def _build_prompt(self, question: str, context: str) -> str:
        safe_question = (question or "").strip()[:400]
        safe_context = (context or "").strip()[:1600]

        return (
            "Use the context to answer the interview question. "
            "If context is weak, still provide best-practice coding guidance.\n\n"
            f"Question:\n{safe_question}\n\n"
            f"Context:\n{safe_context}\n\n"
            "Give:\n"
            "1) Short direct answer\n"
            "2) Step-by-step reasoning\n"
            "3) If coding-related, an implementation outline"
        )


llm_service = LLMService()

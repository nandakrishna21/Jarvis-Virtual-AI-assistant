import asyncio, time, httpx
from app.config import settings
from app.utils.logging_setup import get_logger

logger = get_logger("jarvis.ollama")
_semaphore = asyncio.Semaphore(settings.max_concurrent_ai_jobs)
_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def _get_client() -> httpx.AsyncClient:
    """Reuse one HTTP client so connections are pooled instead of rebuilt."""
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=3.0),
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
        )
        _client_loop = loop
    return _client


async def chat(prompt: str, system: str | None = None) -> dict:
    start = time.time()
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "think": settings.ollama_think,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"num_ctx": settings.ollama_num_ctx, "num_predict": settings.ollama_num_predict},
    }
    try:
        async with _semaphore:
            r = await _get_client().post(f"{settings.ollama_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        return {"ok": True, "response": data["message"]["content"], "model": settings.ollama_model,
                "elapsed": round(time.time() - start, 2),
                "tokens": data.get("eval_count", 0),
                "tokens_per_second": round(data.get("eval_count", 0) / max(time.time() - start, 0.01), 2)}
    except Exception as e:
        logger.warning("ollama request failed: %s", e)
        return {"ok": False, "error": str(e),
                "hint": f"Start Ollama and pull the model: ollama pull {settings.ollama_model}"}


async def health() -> dict:
    try:
        r = await _get_client().get(f"{settings.ollama_url}/api/tags")
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        return {"ok": True, "models": models, "active_model": settings.ollama_model,
                "model_available": settings.ollama_model in models}
    except Exception:
        return {"ok": False, "models": [], "active_model": settings.ollama_model, "model_available": False}


async def running_models() -> list[dict]:
    try:
        r = await _get_client().get(f"{settings.ollama_url}/api/ps")
        r.raise_for_status()
        return r.json().get("models", [])
    except Exception:
        return []


async def unload_model() -> dict:
    try:
        r = await _get_client().post(f"{settings.ollama_url}/api/generate", json={"model": settings.ollama_model, "keep_alive": 0})
        r.raise_for_status()
        return {"ok": True, "unloaded": settings.ollama_model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def close_client() -> None:
    global _client, _client_loop
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
    _client_loop = None

import asyncio, time, httpx
from app.config import settings
from app.utils.logging_setup import get_logger

logger = get_logger("jarvis.ollama")
_semaphore = asyncio.Semaphore(settings.max_concurrent_ai_jobs)

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
            async with httpx.AsyncClient(timeout=300) as c:
                r = await c.post(f"{settings.ollama_url}/api/chat", json=payload)
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
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.ollama_url}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {"ok": True, "models": models, "active_model": settings.ollama_model,
                    "model_available": settings.ollama_model in models}
    except Exception:
        return {"ok": False, "models": [], "active_model": settings.ollama_model, "model_available": False}

async def running_models() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.ollama_url}/api/ps")
            r.raise_for_status()
            return r.json().get("models", [])
    except Exception:
        return []

async def unload_model() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{settings.ollama_url}/api/generate", json={"model": settings.ollama_model, "keep_alive": 0})
            r.raise_for_status()
            return {"ok": True, "unloaded": settings.ollama_model}
    except Exception as e:
        return {"ok": False, "error": str(e)}

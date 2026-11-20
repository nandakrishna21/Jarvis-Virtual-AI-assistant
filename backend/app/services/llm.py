"""Pluggable LLM providers.

Ollama stays the default because it runs locally with no key and no cost.
Gemini and OpenRouter are optional: when the key is missing or the call
fails, the request falls back to Ollama so the assistant never goes silent.
"""
import logging
import time

import httpx

from app.config import settings
from app.services import ollama

logger = logging.getLogger("jarvis.llm")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
PROVIDERS = ("ollama", "gemini", "openrouter", "nvidia")


def provider_status() -> dict:
    provider = (settings.llm_provider or "ollama").strip().lower()
    return {
        "provider": provider,
        "available": {
            "ollama": True,
            "gemini": bool(settings.gemini_api_key),
            "openrouter": bool(settings.openrouter_api_key),
            "nvidia": bool(settings.nvidia_api_key),
        },
        "active": provider if provider in PROVIDERS else "ollama",
        "fallback": "ollama",
        "models": {
            "ollama": settings.ollama_model,
            "gemini": "gemini-2.0-flash",
            "openrouter": settings.openrouter_model,
            "nvidia": settings.nvidia_model,
        },
        "notes": {
            "gemini": "set GEMINI_API_KEY to enable",
            "openrouter": "set OPENROUTER_API_KEY to enable",
            "nvidia": "set NVIDIA_API_KEY to enable",
            "ollama": "local model, always available",
        },
    }


def set_provider(name: str) -> dict:
    """Switch the active provider at runtime and persist the choice."""
    provider = (name or "").strip().lower()
    if provider not in PROVIDERS:
        return {"ok": False, "error": "provider must be one of " + ", ".join(PROVIDERS)}
    settings.llm_provider = provider
    try:
        from app.database.session import SessionLocal
        from app.database.models import AppSetting

        db = SessionLocal()
        try:
            row = db.query(AppSetting).filter(AppSetting.key == "llm_provider").first()
            if not row:
                row = AppSetting(key="llm_provider")
                db.add(row)
            row.value = provider
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not persist llm provider: %s", exc)
    return {"ok": True, **provider_status()}


def load_persisted_provider() -> str:
    """Restore the provider selected earlier. Called once at startup."""
    try:
        from app.database.session import SessionLocal
        from app.database.models import AppSetting

        db = SessionLocal()
        try:
            row = db.query(AppSetting).filter(AppSetting.key == "llm_provider").first()
            if row and row.value in PROVIDERS:
                settings.llm_provider = row.value
                return row.value
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not load llm provider: %s", exc)
    return settings.llm_provider


async def _gemini(prompt: str, system: str | None) -> dict:
    start = time.time()
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system}]} if system else None,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": settings.ollama_num_predict},
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            f"{GEMINI_URL}?key={settings.gemini_api_key}",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
    text = ""
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text += part.get("text", "")
    return {"ok": True, "response": text, "model": "gemini-2.0-flash",
            "elapsed": round(time.time() - start, 2), "provider": "gemini"}


async def _openrouter(prompt: str, system: str | None) -> dict:
    start = time.time()
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {"model": settings.openrouter_model, "messages": messages, "temperature": 0.3}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            OPENROUTER_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1:5173",
                "X-Title": "JARVIS",
            },
        )
        r.raise_for_status()
        data = r.json()
    text = ""
    choices = data.get("choices") or []
    if choices:
        text = (choices[0].get("message") or {}).get("content", "")
    return {"ok": True, "response": text, "model": settings.openrouter_model,
            "elapsed": round(time.time() - start, 2), "provider": "openrouter"}


async def _nvidia(prompt: str, system: str | None) -> dict:
    """NVIDIA NIM (OpenAI-compatible endpoint).

    Several NIM models are tried in turn: some return their answer in a
    reasoning channel instead of the content channel, so an empty reply means
    "try the next model" rather than "the call failed".
    """
    start = time.time()
    models = [settings.nvidia_model]
    for extra in (settings.nvidia_fallback_models or "").split(","):
        extra = extra.strip()
        if extra and extra not in models:
            models.append(extra)

    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
    }
    base = (settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1").rstrip("/")
    last_error = ""
    async with httpx.AsyncClient(timeout=120) as c:
        for model in models:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": settings.ollama_num_predict,
            }
            try:
                r = await c.post(f"{base}/chat/completions", json=payload, headers=headers)
            except Exception as exc:  # noqa: BLE001
                last_error = f"{model}: {exc}"
                continue
            if r.status_code != 200:
                last_error = f"{model}: HTTP {r.status_code} {r.text[:200]}"
                continue
            try:
                data = r.json()
            except Exception as exc:  # noqa: BLE001
                last_error = f"{model}: bad json ({exc})"
                continue
            choices = data.get("choices") or []
            if not choices:
                last_error = f"{model}: no choices"
                continue
            message = choices[0].get("message") or {}
            text = (message.get("content") or "").strip()
            if not text:
                text = (message.get("reasoning_content") or "").strip()
            if not text:
                last_error = f"{model}: empty reply"
                continue
            return {"ok": True, "response": text, "model": model,
                    "elapsed": round(time.time() - start, 2), "provider": "nvidia"}
    raise RuntimeError(f"nvidia provider failed: {last_error}")


async def chat(prompt: str, system: str | None = None) -> dict:
    """Chat through the configured provider, falling back to Ollama."""
    provider = (settings.llm_provider or "ollama").strip().lower()
    if provider == "nvidia" and settings.nvidia_api_key:
        try:
            result = await _nvidia(prompt, system)
            if result.get("ok"):
                return result
            logger.warning("nvidia provider failed, falling back to ollama")
        except Exception as exc:  # noqa: BLE001
            logger.warning("nvidia provider error: %s", exc)
            fallback = await ollama.chat(prompt, system)
            if fallback.get("ok"):
                fallback["fallback_from"] = "nvidia"
                fallback["fallback_reason"] = str(exc)
            return fallback
    if provider == "gemini" and settings.gemini_api_key:
        try:
            result = await _gemini(prompt, system)
            if result.get("ok"):
                return result
            logger.warning("gemini provider failed, falling back to ollama")
        except Exception as exc:  # noqa: BLE001
            logger.warning("gemini provider error: %s", exc)
            fallback = await ollama.chat(prompt, system)
            if fallback.get("ok"):
                fallback["fallback_from"] = "gemini"
                fallback["fallback_reason"] = str(exc)
            return fallback
    if provider == "openrouter" and settings.openrouter_api_key:
        try:
            result = await _openrouter(prompt, system)
            if result.get("ok"):
                return result
            logger.warning("openrouter provider failed, falling back to ollama")
        except Exception as exc:  # noqa: BLE001
            logger.warning("openrouter provider error: %s", exc)
            fallback = await ollama.chat(prompt, system)
            if fallback.get("ok"):
                fallback["fallback_from"] = "openrouter"
                fallback["fallback_reason"] = str(exc)
            return fallback
    result = await ollama.chat(prompt, system)
    result.setdefault("provider", "ollama")
    return result

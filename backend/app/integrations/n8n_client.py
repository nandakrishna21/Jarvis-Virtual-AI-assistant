"""Local n8n client.

n8n runs on the same machine at http://127.0.0.1:5678. JARVIS triggers
workflows through their webhook triggers, which needs no API key and keeps
all data on the laptop. Every call has a short timeout and returns a
structured result instead of raising, so a stopped n8n never breaks the app.
"""
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.n8n")

WEBHOOK_BASE = "/webhook/jarvis"


def _base() -> str:
    return settings.n8n_url.rstrip("/")


async def health() -> dict:
    url = f"{_base()}/healthz"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
        return {"ok": r.status_code == 200, "url": _base(), "status_code": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": _base(), "error": str(exc)}


async def list_workflows_api() -> dict:
    """Read workflows through the n8n public API. Needs an API key."""
    key = settings.__dict__.get("n8n_api_key") or ""
    if not key:
        return {"ok": False, "error": "n8n API key not configured", "workflows": []}
    url = f"{_base()}/api/v1/workflows"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers={"X-N8N-API-KEY": key})
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}", "workflows": []}
        data = r.json()
        return {
            "ok": True,
            "workflows": [
                {"id": w.get("id"), "name": w.get("name"), "active": w.get("active", False)}
                for w in data.get("data", [])
            ],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "workflows": []}


async def trigger(webhook_path: str, payload: dict, timeout: float = 120.0) -> dict:
    """POST to an n8n webhook trigger and return its response."""
    path = webhook_path.lstrip("/")
    if not path.startswith("webhook/") and not path.startswith("workflow/"):
        path = f"{WEBHOOK_BASE}/{path}"
    url = f"{_base()}/{path}"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
        elapsed = int((time.perf_counter() - started) * 1000)
        body = r.text
        try:
            body = json.loads(body)
        except ValueError:
            body = body[:500]
        return {
            "ok": r.status_code < 400,
            "status_code": r.status_code,
            "url": url,
            "response": body,
            "duration_ms": elapsed,
        }
    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.perf_counter() - started) * 1000)
        logger.warning("n8n trigger failed: %s", exc)
        return {"ok": False, "error": str(exc), "url": url, "duration_ms": elapsed}

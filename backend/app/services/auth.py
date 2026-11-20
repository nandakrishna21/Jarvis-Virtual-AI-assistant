"""Local API-key guard.

JARVIS is a single-user app bound to 127.0.0.1, so authentication is off by
default. Set JARVIS_API_KEY in the environment to require a key on every
mutating request. The key is never written to the database or logged.
"""
import hashlib
import hmac
import os

from app.config import settings


def api_key() -> str:
    configured = getattr(settings, "api_key", "")
    if not isinstance(configured, str):
        configured = ""
    prefixed = getattr(settings, "jarvis_api_key", "")
    if not isinstance(prefixed, str):
        prefixed = ""
    env = os.getenv("JARVIS_API_KEY", "") or ""
    if not isinstance(env, str):
        env = ""
    return (configured or prefixed or env).strip()


def enabled() -> bool:
    return bool(api_key())


def check(candidate: str | None) -> bool:
    expected = api_key()
    if not expected:
        return True
    if not candidate:
        return False
    return hmac.compare_digest(candidate.strip(), expected)


def fingerprint() -> str:
    """A short, non-reversible id so the UI can show which key is active."""
    key = api_key()
    if not key:
        return ""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def status() -> dict:
    return {
        "enabled": enabled(),
        "fingerprint": fingerprint(),
        "header": "X-API-Key",
        "protected_methods": ["POST", "PUT", "PATCH", "DELETE"],
        "note": (
            "Single-user local mode: no key required."
            if not enabled()
            else "A key is required for mutating requests."
        ),
    }

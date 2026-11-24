"""Public-demo guard.

When JARVIS is deployed for a resume showcase it must be usable by strangers
without exposing the owner's machine. Demo mode therefore only serves a small
allowlist of safe, read-mostly routes. Anything that can touch local files,
Gmail, the Windows host, n8n, uploads or stored resumes is rejected before it
reaches a handler.
"""
from app.config import settings

# Routes that remain available in public demo mode. Everything else under the
# API is disabled. Paths are matched after the /api prefix is stripped.
DEMO_ALLOWED_PREFIXES = (
    "/health",
    "/system/status",
    "/system/metrics",
    "/system/auth",
    "/system/llm",
    "/system/power",        # read only; the POST variants are blocked below
    "/assistant/greeting",
    "/assistant/history",
    "/assistant/help",
    "/weather",
    "/jobs",
    "/matching",
    "/notifications",
    "/analytics",
    "/profile",
    "/automation",          # read only; start/stop/run are blocked below
    "/voice/status",
    "/voice/agent/help",
)

DEMO_ALLOWED_EXACT = {
    "/chat": {"POST"},
    "/assistant/chat": {"POST"},
    "/assistant/command": {"POST"},
    "/voice/agent": {"POST"},
}

DEMO_BLOCKED_PREFIXES = (
    "/gmail",
    "/youtube",
    "/emails",
    "/files",
    "/developer",
    "/documents",
    "/resumes",
    "/applications",
    "/approvals",
    "/actions",
    "/interviews",
    "/tasks",
    "/reminders",
    "/schedules",
    "/study",
    "/hiring-news",
    "/system/startup",
    "/system/backup",
    "/system/backups",
    "/system/restore",
    "/system/unload-model",
    "/system/power/rest",
    "/system/power/wake",
    "/automation/run",
    "/automation/start",
    "/automation/stop",
    "/automation/pause",
    "/automation/resume",
    "/automation/rest",
    "/automation/wake",
    "/automation/run-now",
    "/voice/transcribe",
    "/voice/tts",
    "/voice/unload",
)


def enabled() -> bool:
    return bool(settings.demo_mode)


def normalize(path: str) -> str:
    path = (path or "/").split("?", 1)[0]
    if path == "/api":
        return "/"
    if path.startswith("/api/"):
        return path[4:]
    return path or "/"


def is_blocked(path: str, method: str) -> bool:
    """True when the request must be rejected in public demo mode."""
    if not enabled():
        return False
    clean = normalize(path)
    verb = method.upper()
    for prefix in DEMO_BLOCKED_PREFIXES:
        if clean == prefix or clean.startswith(prefix + "/"):
            return True
    # Demo mode is read-only apart from the explicitly allowlisted chat turns.
    if verb != "GET":
        allowed = DEMO_ALLOWED_EXACT.get(clean)
        return allowed is None or verb not in allowed
    for prefix in DEMO_ALLOWED_PREFIXES:
        if clean == prefix or clean.startswith(prefix + "/"):
            return False
    return True

"""Windows autostart for JARVIS.

The production entry point starts one process: the FastAPI backend, which also
serves the built dashboard from `frontend/dist`. That keeps memory use low on
this 8 GB host - no extra Vite dev server.
"""
import os, subprocess
from pathlib import Path

STARTUP_DIR = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
ENTRY_NAME = "JARVIS.cmd"
JARVIS_ROOT = Path(r"C:\JARVIS")

CMD_TEMPLATE = """@echo off
title JARVIS
powershell -NoProfile -ExecutionPolicy Bypass -File "{root}\\scripts\\start_prod.ps1"
exit /b 0
"""


def entry_path() -> Path:
    return STARTUP_DIR / ENTRY_NAME


def status() -> dict:
    p = entry_path()
    return {
        "startup_entry": str(p),
        "exists": p.exists(),
        "startup_folder": str(STARTUP_DIR),
        "backend_port": 8000,
        "frontend_port": 8000,
        "mode": "production (backend serves the built dashboard)",
    }


def enable() -> dict:
    script = JARVIS_ROOT / "scripts" / "start_prod.ps1"
    if not script.exists():
        return {"error": f"start script not found at {script}"}
    STARTUP_DIR.mkdir(parents=True, exist_ok=True)
    content = CMD_TEMPLATE.format(root=JARVIS_ROOT)
    entry_path().write_text(content, encoding="utf-8")
    return {"enabled": True, "path": str(entry_path()),
            "note": "JARVIS will start when you log in to Windows."}


def disable() -> dict:
    p = entry_path()
    if p.exists():
        p.unlink()
        return {"enabled": False, "removed": str(p)}
    return {"enabled": False, "removed": None, "note": "nothing to remove"}


def open_backend() -> dict:
    """Start the backend now (manual mode)."""
    python = str(JARVIS_ROOT / "backend" / ".venv" / "Scripts" / "python.exe")
    if not Path(python).exists():
        return {"error": "backend virtualenv missing"}
    subprocess.Popen(
        [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(JARVIS_ROOT / "backend"),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"started": "backend", "port": 8000}

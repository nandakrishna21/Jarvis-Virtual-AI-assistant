"""Test isolation.

Tests must never touch the real `jarvis.db`. The database URL is pointed at a
throwaway file in the temp folder before any application module is imported,
because the engine is created at import time.
"""
import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "jarvis_pytest.db"

for suffix in ("", "-wal", "-shm"):
    candidate = Path(str(_TEST_DB) + suffix)
    if candidate.exists():
        try:
            candidate.unlink()
        except OSError:
            pass

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["JARVIS_API_KEY"] = ""

"""Gemini speech-to-text for JARVIS voice input.

Sends a short recorded clip to Gemini's multimodal generateContent endpoint and
returns the transcript. Used as the fast cloud option when GEMINI_API_KEY is
set; the local Whisper model stays available as the offline fallback.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from app.config import settings

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
SUPPORTED = {".wav", ".mp3", ".aiff", ".aac", ".ogg", ".flac"}
MIME = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".aiff": "audio/aiff",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
PROMPT = (
    "Transcribe this audio exactly as spoken. Return only the transcript text, "
    "with no quotes and no commentary. If there is no speech, return an empty string."
)


def available() -> bool:
    return bool((settings.gemini_api_key or "").strip())


def _ffmpeg() -> str | None:
    for cand in (
        shutil.which("ffmpeg"),
        r"C:\Users\Nanda Krishna\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe",
    ):
        if cand and Path(cand).exists():
            return str(Path(cand))
    return None


def _to_supported(path: Path) -> tuple[Path, str]:
    """Gemini accepts wav/mp3/aiff/aac/ogg/flac; convert webm/m4a via ffmpeg."""
    suffix = path.suffix.lower()
    if suffix in SUPPORTED:
        return path, MIME[suffix]
    ff = _ffmpeg()
    if not ff:
        return path, "audio/webm"
    out = path.with_suffix(".wav")
    try:
        proc = subprocess.run(
            [ff, "-y", "-i", str(path), "-ar", "16000", "-ac", "1", str(out)],
            capture_output=True,
            timeout=60,
        )
    except Exception:
        return path, "audio/webm"
    if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return path, "audio/webm"
    return out, "audio/wav"


def transcribe(audio_bytes: bytes, filename: str = "clip.webm") -> dict:
    if not audio_bytes:
        return {"error": "empty audio"}
    if not available():
        return {"error": "GEMINI_API_KEY is not set"}

    tmp_dir = Path(os.environ.get("JARVIS_TEMP_DIR", r"C:\JARVIS\data\temp"))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, dir=str(tmp_dir), suffix=suffix) as f:
        f.write(audio_bytes)
        src = Path(f.name)

    converted: Path | None = None
    try:
        audio_path, mime = _to_supported(src)
        if audio_path != src:
            converted = audio_path
        encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": PROMPT},
                        {"inline_data": {"mime_type": mime, "data": encoded}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0},
        }
        model = (settings.gemini_stt_model or "gemini-2.0-flash").strip()
        start = time.time()
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{BASE}/{model}:generateContent",
                params={"key": settings.gemini_api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()
        text = ""
        for candidate in body.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text += part.get("text", "")
        return {
            "text": text.strip(),
            "engine": "gemini",
            "model": model,
            "elapsed": round(time.time() - start, 2),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "engine": "gemini"}
    finally:
        for path in (src, converted):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

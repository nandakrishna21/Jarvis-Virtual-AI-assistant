import os, re, tempfile, threading, time
from pathlib import Path

TEMP_DIR = Path(os.environ.get("JARVIS_TEMP_DIR", r"C:\JARVIS\data\temp"))
WHISPER_MODEL = os.environ.get("JARVIS_WHISPER_MODEL", "tiny")

_state = {
    "model": None,
    "loading": False,
    "load_seconds": 0,
    "last_used": None,
    "engine": "faster-whisper (local)",
    "error": None,
}
_lock = threading.Lock()


def status() -> dict:
    return {
        "stt_available": _state["model"] is not None or not _state["error"],
        "stt_loaded": _state["model"] is not None,
        "stt_loading": _state["loading"],
        "stt_engine": _state["engine"],
        "whisper_model": WHISPER_MODEL,
        "model_load_seconds": round(_state["load_seconds"], 1),
        "last_used": _state["last_used"],
        "error": _state["error"],
        "tts_available": _tts_available(),
        "tts_engine": "pyttsx3 (Windows local voices)",
    }


def _tts_available() -> bool:
    try:
        import pyttsx3  # noqa: F401
        return True
    except Exception:
        return False


def _get_model():
    if _state["model"] is not None:
        return _state["model"]
    with _lock:
        if _state["model"] is not None:
            return _state["model"]
        _state["loading"] = True
        start = time.time()
        try:
            from faster_whisper import WhisperModel
            _state["model"] = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
            _state["load_seconds"] = time.time() - start
            _state["error"] = None
        except Exception as e:
            _state["error"] = str(e)
            _state["model"] = None
            raise
        finally:
            _state["loading"] = False
    return _state["model"]


def transcribe(audio_bytes: bytes, filename: str = "clip.webm") -> dict:
    if not audio_bytes:
        return {"error": "empty audio"}
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, dir=str(TEMP_DIR), suffix=suffix) as f:
        f.write(audio_bytes)
        temp_path = f.name
    try:
        model = _get_model()
        start = time.time()
        segments, info = model.transcribe(temp_path, language="en", beam_size=1, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        _state["last_used"] = time.time()
        return {
            "text": text,
            "duration": round(info.duration, 2),
            "elapsed": round(time.time() - start, 2),
            "engine": _state["engine"],
        }
    except Exception as e:
        return {"error": str(e), "hint": "The first request downloads/loads the local Whisper model. Retry in a moment."}
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def speak(text: str, filename: str = "jarvis_reply.wav") -> dict:
    if not text or not text.strip():
        return {"error": "text is required"}
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TEMP_DIR / filename
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        engine.stop()
        if not out_path.exists() or out_path.stat().st_size == 0:
            return {"error": "no audio produced by Windows voice engine"}
        return {"path": str(out_path), "size": out_path.stat().st_size, "engine": "pyttsx3"}
    except Exception as e:
        return {"error": str(e), "hint": "The browser speech synthesis fallback still works."}


def unload() -> dict:
    with _lock:
        had = _state["model"] is not None
        _state["model"] = None
    return {"unloaded": had}


# ---------- conversational voice agent ----------

FOLLOWUP_PATTERNS = [
    r"^more\b", r"^next\b", r"^again\b", r"^repeat\b", r"^the (first|second|third|1st|2nd|3rd|last) one\b",
    r"^tell me more\b", r"^go on\b", r"^continue\b", r"^and\b", r"^what about\b", r"^how about\b",
    r"^why\b", r"^why not\b", r"^ok\b", r"^okay\b", r"^yes\b", r"^sure\b", r"^do it\b",
    r"^explain\b", r"^shorten that\b", r"^say that again\b",
]

CLEAR_PATTERNS = [r"^forget (everything|that|it)\b", r"^start over\b", r"^reset the conversation\b",
                  r"^clear (your )?memory\b"]

_convo_lock = threading.Lock()
_convo = {"turns": [], "last_message": "", "last_intent": ""}


def _is_followup(text: str) -> bool:
    low = text.strip().lower()
    if len(low) > 60:
        return False
    return any(re.search(p, low) for p in FOLLOWUP_PATTERNS)


def _is_clear(text: str) -> bool:
    low = text.strip().lower()
    return any(re.search(p, low) for p in CLEAR_PATTERNS)


def _convo_snapshot() -> dict:
    with _convo_lock:
        return {"turns": list(_convo["turns"]), "last_message": _convo["last_message"],
                "last_intent": _convo["last_intent"]}


def _convo_push(user: str, assistant: str, intent: str) -> None:
    with _convo_lock:
        _convo["turns"].append({"user": user, "assistant": assistant})
        _convo["turns"] = _convo["turns"][-10:]
        _convo["last_message"] = user
        _convo["last_intent"] = intent


def _convo_clear() -> None:
    with _convo_lock:
        _convo["turns"] = []
        _convo["last_message"] = ""
        _convo["last_intent"] = ""


def to_speech(text: str, max_chars: int = 900) -> str:
    """Turn a chat answer into something pleasant to listen to."""
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.S)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", "the link", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*[-*•]\s*", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*\d+[.)]\s*", "", cleaned, flags=re.M)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    if len(cleaned) > max_chars:
        cut = cleaned[:max_chars]
        stop = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        if stop > 120:
            cut = cut[: stop + 1]
        cleaned = cut.strip() + "."
    return cleaned


async def _chat_with_context(prompt: str, turns: list[dict]) -> dict:
    from app.services.llm import chat as llm_chat

    context = "\n".join(f"User: {t['user']}\nJARVIS: {t['assistant']}" for t in turns[-4:])
    message = (
        "You are JARVIS, a concise local voice assistant for a job seeker. "
        "Answer in at most three short sentences that sound natural when spoken aloud. "
        "No markdown, no bullet lists, no URLs.\n\n"
        f"Conversation so far:\n{context}\n\nUser: {prompt}"
    )
    return await llm_chat(message)


async def agent_reply(message: str, history: list[dict] | None = None) -> dict:
    """Answer one voice turn by routing it through the real orchestrator.

    The same intents as the chat work here (jobs, tasks, gmail, news, study,
    approvals, document generation). Anything that mutates still returns an
    approval proposal instead of acting.
    """
    from app.orchestrator import router

    text = (message or "").strip()
    if not text:
        return {"ok": False, "error": "nothing was heard"}

    if _is_clear(text):
        _convo_clear()
        return {"ok": True, "intent": "chat", "reply": "Okay, I forgot the earlier conversation.",
                "spoken": "Okay, I forgot the earlier conversation.", "reset": True}

    turns = []
    for item in (history or [])[-6:]:
        if isinstance(item, dict):
            user = str(item.get("user") or item.get("text") or "").strip()
            assistant = str(item.get("assistant") or item.get("reply") or "").strip()
            if user:
                turns.append({"user": user, "assistant": assistant})
    if not turns:
        turns = _convo_snapshot()["turns"]

    effective = text
    followup = _is_followup(text)
    last_message = _convo_snapshot()["last_message"]
    if followup and last_message and text.lower() not in ("yes", "ok", "okay", "sure", "do it"):
        effective = f"{last_message}. {text}"

    try:
        intent = router.detect_intent(effective)
        if intent == "chat" and turns:
            result = await _chat_with_context(effective, turns)
            result["intent"] = "chat"
        else:
            result = await router.handle(effective)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}

    reply = (result.get("response") or result.get("error") or "").strip()
    spoken = to_speech(reply)
    if result.get("requires_approval"):
        spoken = (spoken + " " if spoken else "") + (
            "This action needs your approval. Open the approvals panel to confirm it."
        )
    if result.get("open_url"):
        spoken = (spoken + " " if spoken else "") + (
            f"Tap the open button in the chat to open {result.get('open_label') or 'the link'}."
        )
    _convo_push(text, spoken or reply, result.get("intent") or "")
    return {
        "ok": bool(result.get("ok", True)),
        "intent": result.get("intent"),
        "reply": reply,
        "spoken": spoken,
        "requires_approval": bool(result.get("requires_approval")),
        "proposal": result.get("proposal"),
        "open_url": result.get("open_url"),
        "open_label": result.get("open_label"),
        "weather": result.get("weather"),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "elapsed": result.get("elapsed"),
    }

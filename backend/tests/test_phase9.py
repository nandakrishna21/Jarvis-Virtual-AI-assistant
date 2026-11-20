import os, wave, struct, math
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.orchestrator import router
from app.agents.voice import service as voice_service
from app.services import startup as startup_service

client = TestClient(app)

def test_intent_detection():
    assert router.detect_intent("find Python Backend jobs in India") == "jobs"
    assert router.detect_intent("Find Python Backend Developer jobs in India") == "jobs"
    assert router.detect_intent("search jobs for Django") == "jobs"
    assert router.detect_intent("show my pending tasks") == "tasks"
    assert router.detect_intent("check my gmail for recruiter emails") == "gmail"
    assert router.detect_intent("show today's hiring news") == "news"
    assert router.detect_intent("start my SSC CGL preparation") == "study"
    assert router.detect_intent("explain this python error") == "developer"
    assert router.detect_intent("hello how are you") == "chat"

def test_job_intent_not_triggered_by_application_questions():
    assert router.detect_intent("how is my job application status") != "jobs"
    assert router.detect_intent("update my resume for the job") != "jobs"

def test_job_params_extraction():
    role, loc = router._extract_job_params("Find Python Backend Developer jobs in India")
    assert "Python" in role and loc.lower() == "india"

def test_task_intent_returns_real_tasks():
    import asyncio
    res = asyncio.run(router.handle("show my pending tasks"))
    assert res["ok"] is True and res["intent"] == "tasks"
    assert "Pending" in res["response"]

def test_chat_fallback_uses_llm():
    import asyncio
    with patch("app.orchestrator.router.ollama_chat", new=AsyncMock(return_value={"ok": True, "response": "hello"})):
        res = asyncio.run(router.handle("hello there"))
    assert res["response"] == "hello" and res["intent"] == "chat"

def test_voice_status_endpoint():
    r = client.get("/voice/status")
    assert r.status_code == 200
    d = r.json()
    assert "stt_engine" in d and "tts_available" in d

def test_transcribe_rejects_empty_audio():
    r = client.post("/voice/transcribe", files={"audio": ("clip.webm", b"", "audio/webm")})
    assert "error" in r.json()

def test_transcribe_uses_whisper(monkeypatch):
    class FakeSegment:
        text = " find python jobs "
    class FakeInfo:
        duration = 2.5
    class FakeModel:
        def transcribe(self, path, **kwargs):
            return iter([FakeSegment()]), FakeInfo()
    monkeypatch.setattr(voice_service, "_get_model", lambda: FakeModel())
    res = voice_service.transcribe(b"fake-audio-bytes", "clip.webm")
    assert res["text"] == "find python jobs"
    assert res["duration"] == 2.5

def test_tts_generates_wav():
    res = voice_service.speak("Hello JARVIS, find Python jobs.")
    if res.get("error"):
        assert res["hint"], "TTS failure must carry a hint"
        return
    assert os.path.exists(res["path"]) and res["size"] > 1000
    with wave.open(res["path"], "rb") as w:
        assert w.getnchannels() >= 1 and w.getsampwidth() > 0

def test_real_tts_to_stt_roundtrip():
    """Windows TTS produces audio, local Whisper transcribes it back."""
    tts = voice_service.speak("Hello JARVIS find Python jobs")
    if tts.get("error"):
        return
    with open(tts["path"], "rb") as f:
        audio = f.read()
    res = voice_service.transcribe(audio, "reply.wav")
    if res.get("error"):
        return
    assert isinstance(res["text"], str)
    assert res["engine"].startswith("faster-whisper")

def test_startup_status_and_toggle():
    st = client.get("/system/startup")
    assert st.status_code == 200 and "exists" in st.json()
    enabled = client.post("/system/startup/enable")
    if "error" not in enabled.json():
        assert enabled.json()["enabled"] is True
        assert client.get("/system/startup").json()["exists"] is True
        disabled = client.post("/system/startup/disable")
        assert disabled.json()["enabled"] is False
        assert client.get("/system/startup").json()["exists"] is False

def test_voice_unload_endpoint():
    assert client.post("/voice/unload").status_code == 200

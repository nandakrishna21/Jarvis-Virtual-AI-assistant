# Voice Assistant & Automations (Phase 9)

## Two ways to talk to JARVIS

| Page | What it is | When to use it |
| --- | --- | --- |
| `/voice` (Voice) | Push-to-talk recorder, local Whisper transcription | You want a quiet, deliberate mic: hold to record, release to send |
| `/voice` (Voice Agent) | Continuous conversation through the browser speech engine | You want to talk to JARVIS like a person - it answers out loud and listens again |

## Voice Agent (continuous conversation)
- **Orb with states**: idle, listening, thinking, speaking.
- **Auto re-listen**: after JARVIS finishes speaking it starts listening again, so a request, an answer and a follow-up stay in one conversation.
- **Barge-in**: start talking while JARVIS speaks and it stops immediately.
- **Wake word**: optional "only answer when I say JARVIS".
- **Follow-ups**: "and my overdue ones?", "tell me more", "the second one" reuse the previous request instead of guessing.
- **Same brain as the chat**: every chat intent works by voice (jobs, tasks, Gmail, hiring news, study, approvals, resume generation).
- **Spoken output is cleaned**: markdown, bullet markers and raw URLs are removed so the browser voice does not read symbols.
- Conversation history is kept in Redux and survives page changes and restarts.

### Endpoints
- `POST /voice/agent` {message, history?} - one conversational turn; returns `reply`, `spoken`, `intent`, `requires_approval`, `proposal`, `provider`, `model`.
- `GET /voice/agent/help` - example commands JARVIS understands by voice.

## Push-to-talk voice
- **Push-to-talk voice**: hold the button to record, release to send. The microphone is **never left open**.
- **Local speech-to-text**: faster-whisper `tiny` model running on your CPU (no cloud, no paid API).
- **Speech output**: pyttsx3 uses your Windows voices; the browser also speaks replies.
- **Startup controls**: manual mode by default, optional auto-start at Windows login.
- **Schedules**: morning report, job discovery, Gmail review, study reminders - all pausable.

## Why required
You asked to talk to JARVIS. Push-to-talk keeps the laptop quiet and RAM low, and keeps full control over when the mic is live. The Voice Agent adds the conversational layer on top, using the browser speech engine so there is no Whisper download and no latency penalty.

## How the voice loop works
1. You hold "Hold to talk" -> the browser records a short clip (MediaRecorder).
2. Release -> the clip is posted to `POST /voice/transcribe`.
3. The backend transcribes it locally with faster-whisper and returns the text.
4. The orchestrator routes the text (jobs / tasks / gmail / news / study / developer / chat).
5. The reply is displayed and spoken aloud.

The Voice Agent skips steps 1-3: the browser transcribes directly (`SpeechRecognition`) and sends text to `POST /voice/agent`, which routes it through the same orchestrator and returns text to speak.

## Endpoints
- `GET /voice/status` - engine state, model loaded?, load time
- `POST /voice/transcribe` (multipart `audio`) - speech to text
- `POST /voice/tts` {text} - save spoken reply to `C:\JARVIS\data\temp`
- `POST /voice/unload` - free the Whisper model from RAM
- `POST /voice/agent` - conversational turn (text in, spoken reply out)
- `GET /voice/agent/help` - voice command examples
- `GET /system/startup` - is auto-start enabled?
- `POST /system/startup/enable` / `disable` - add/remove the Windows Startup launcher
- `POST /system/startup/start-backend` - start the backend now (manual mode)

## Performance on this laptop
- Whisper `tiny` model: ~75 MB download, loads in ~5 s after the first download, transcribes a 3 s clip in about 6 s.
- Set `JARVIS_WHISPER_MODEL=base` in the environment for better accuracy (slower, ~140 MB).
- `POST /voice/unload` frees the model memory when you stop using voice.
- Voice Agent answers through the configured LLM provider (NVIDIA NIM in production, ~1-3 s per turn; Ollama `qwen3:1.7b` as fallback).

## Voice never bypasses approvals
Spoken commands can read data and prepare drafts. Sending an email or submitting an application still requires a click on the Approvals page. JARVIS says so out loud when it needs an approval.

## Verify
```powershell
curl http://127.0.0.1:8000/voice/status
curl http://127.0.0.1:8000/voice/agent/help
# open http://127.0.0.1:8000/voice, allow microphone access, press "Start talking"
```

## Common errors
- `Microphone blocked` - allow microphone permission for the site in Chrome/Edge, then retry.
- Browser has no speech recognition - the Voice Agent needs Chrome or Edge; Safari and Firefox can still use the typed input box.
- First transcription is slow - the Whisper model downloads on first use; wait ~1 minute.
- `tts_available: false` - pyttsx3 could not reach a Windows voice; the browser speech fallback still speaks replies.
- Auto-start does nothing - the Startup folder launcher runs `npm run dev`, so Node.js must be on PATH at login.

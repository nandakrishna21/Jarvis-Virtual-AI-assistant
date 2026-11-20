# Voice Assistant & Automations (Phase 9)

## What it does
- **Push-to-talk voice**: hold the button to record, release to send. The microphone is **never left open**.
- **Local speech-to-text**: faster-whisper `tiny` model running on your CPU (no cloud, no paid API).
- **Speech output**: pyttsx3 uses your Windows voices; the browser also speaks replies.
- **Startup controls**: manual mode by default, optional auto-start at Windows login.
- **Schedules**: morning report, job discovery, Gmail review, study reminders - all pausable.

## Why required
You asked to talk to JARVIS. Push-to-talk keeps the laptop quiet and RAM low, and keeps full control over when the mic is live.

## How the voice loop works
1. You hold "Hold to talk" -> the browser records a short clip (MediaRecorder).
2. Release -> the clip is posted to `POST /voice/transcribe`.
3. The backend transcribes it locally with faster-whisper and returns the text.
4. The orchestrator routes the text (jobs / tasks / gmail / news / study / developer / chat).
5. The reply is displayed and spoken aloud.

## Endpoints
- `GET /voice/status` - engine state, model loaded?, load time
- `POST /voice/transcribe` (multipart `audio`) - speech to text
- `POST /voice/tts` {text} - save spoken reply to `C:\JARVIS\data\temp`
- `POST /voice/unload` - free the Whisper model from RAM
- `GET /system/startup` - is auto-start enabled?
- `POST /system/startup/enable` / `disable` - add/remove the Windows Startup launcher
- `POST /system/startup/start-backend` - start the backend now (manual mode)

## Performance on this laptop
- Whisper `tiny` model: ~75 MB download, loads in ~5 s after the first download, transcribes a 3 s clip in about 6 s.
- Set `JARVIS_WHISPER_MODEL=base` in the environment for better accuracy (slower, ~140 MB).
- `POST /voice/unload` frees the model memory when you stop using voice.

## Voice never bypasses approvals
Spoken commands can read data and prepare drafts. Sending an email or submitting an application still requires a click on the Approvals page.

## Verify
```powershell
curl http://127.0.0.1:8000/voice/status
# open http://127.0.0.1:5173/voice, allow microphone access, hold the button
```

## Common errors
- `Microphone blocked` - allow microphone permission for 127.0.0.1:5173 in Chrome/Edge, then retry.
- First transcription is slow - the Whisper model downloads on first use; wait ~1 minute.
- `tts_available: false` - pyttsx3 could not reach a Windows voice; the browser speech fallback still speaks replies.
- Auto-start does nothing - the Startup folder launcher runs `npm run dev`, so Node.js must be on PATH at login.

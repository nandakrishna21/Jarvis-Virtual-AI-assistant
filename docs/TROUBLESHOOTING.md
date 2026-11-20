# Troubleshooting

## What it does
Fixes for the errors you are most likely to hit on this laptop.

## Why
Most problems are environmental: Ollama not running, the wrong folder, a stale process holding port 8000, or a missing credential.

## Quick checklist
```powershell
curl http://127.0.0.1:8000/health      # backend alive?
curl http://127.0.0.1:8000/system/status  # Ollama alive?
curl http://127.0.0.1:5173/              # dashboard alive?
```

## Backend problems

**`Address already in use` / port 8000 busy**
```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess
Stop-Process -Id <pid> -Force
```

**`ModuleNotFoundError: No module named 'app'`** - you are in the wrong folder.
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**`No module named venv`** - Python was not installed with venv. Re-run from the official installer and tick "Add to PATH".

**Database looks empty after a new install** - the first request creates all tables automatically; run a search or open a page.

**Corrupt database**
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\backup.py list
.\.venv\Scripts\python scripts\backup.py restore jarvis_20261108_120000.db
```

## Ollama problems

**`ollama: command not found`** - restart PowerShell after installing, or use the full path:
`C:\Users\<you>\AppData\Local\Programs\Ollama\ollama.exe`.

**`Connection refused` on 127.0.0.1:11434** - Ollama is not running. Start it from the Start Menu, or:
```powershell
ollama serve
```

**`model 'qwen3:1.7b' not found`**
```powershell
ollama pull qwen3:1.7b
```

**Replies are very slow (1 minute+)** - the 4B model on this CPU. Switch to `qwen3:1.7b` in `backend/.env` and set `OLLAMA_THINK=false`.

**Replies contain "thinking" notes** - set `OLLAMA_THINK=false` and restart the backend.

**RAM above 90%**
```powershell
curl -X POST http://127.0.0.1:8000/system/unload-model
```
Then close unused Chrome tabs. JARVIS itself only needs ~26 MB.

## Frontend problems

**Blank white page** - open the browser console (F12). If the API is failing, check the backend is on port 8000.

**`ERR_CONNECTION_REFUSED` on /api requests** - the backend is not running.

**Changes do not show** - hard refresh with Ctrl+F5, then restart `npm run dev` if needed.

**`npm` not found** - reinstall Node.js LTS from https://nodejs.org/ and reopen PowerShell.

**Port 5173 in use** - Vite automatically uses the next free port; read the URL it prints.

## Gmail problems

**`credentials.json` missing** - download it again from Google Cloud Console (Desktop OAuth client) and place it at `C:\JARVIS\credentials\credentials.json`.

**`Access blocked: app not verified`** - expected for personal use. Add your own Google account as a **test user** on the OAuth consent screen.

**`token lacks gmail.send scope`** - run `.\.venv\Scripts\python scripts\gmail_auth.py --send` and approve again.

**`draft changed since approval request`** - the draft was edited after the approval was created. Create a new draft and approve it again.

## Voice problems

**`Microphone blocked`** - allow microphone permission for `http://127.0.0.1:5173` in Chrome/Edge, then reload.

**First transcription is slow (about a minute)** - the Whisper model downloads on first use. It works offline afterwards.

**`tts_available: false`** - no Windows voice engine was found. The browser speech fallback still speaks replies.

**Transcription is inaccurate** - the `tiny` model is fast but rough. Set `JARVIS_WHISPER_MODEL=base` in the environment and restart.

## Job discovery problems

**No results** - the source HTML changed or the site blocked the request. Open `https://wellfound.com/jobs?q=Python` in your browser and compare. Add another source in `app/agents/job_discovery/connectors.py`.

**All jobs say "unverified"** - that is correct. Open the original link to confirm the job is live.

**`no practice question stored for topic`** - the question bank has no item for that topic. Add one to `QUESTION_BANK` in `app/agents/government_exam/service.py`.

## Scheduler problems

**Schedules never run** - they are disabled by default. Set `enabled: true` on the schedule and call `POST /schedules/resume`.

**I want everything off** - `POST /schedules/pause` (this also disables every stored schedule).

## Tests

```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python -m pytest tests -q          # all tests
.\.venv\Scripts\python -m pytest tests\test_phase10.py -v   # integration only
```
A failing test usually means an environment change (for example Ollama stopped) rather than broken code - read the failure message first.

## Logs
```powershell
Get-Content C:\JARVIS\logs\jarvis.log -Tail 40
```
The file rotates at 1 MB and keeps 3 older copies (`jarvis.log.1` and so on). Logs never contain tokens or email bodies.

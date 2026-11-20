# JARVIS Personal AI Assistant

Local, lightweight Windows assistant that coordinates specialist agents through one orchestrator, one SQLite database and one local Ollama model.

## Status
Phases 1-11 complete. Backend: **153 tests passing** (`pytest tests -q`, isolated test database). Frontend: Vite production build clean, oxlint **0 errors / 0 warnings**, route-level code splitting. Production build serves the dashboard and the API from one process at **http://127.0.0.1:8000** (89 routes).

## What’s new
- **Chat-first Command Center**: greets you on open, holographic orb, quick commands, inline approval cards.
- **Approval before every action**: mutating requests become proposals → you Approve/Reject → only then executed.
- **Resume Generator**: paste a job description → get a resume built from *your own* old resume, with the JD skills first, bullets re-ordered, and a coverage report that lists the requirements you still cannot prove.
- **Email Access**: connect Gmail, read recruiter/interview/job-alert mail, and let JARVIS prepare the reply - you send it yourself.
- **Document Studio**: structured resume sections (summary/experience/education/projects) + job-specific resume & cover-letter generation with numbered versions and download. Ask "tailor my resume for job 3" and approve it.
- **Honest job matching**: skills are read from the real posting, seniority is measured ("No experience required" → entry), and every score shows its components (skills 35 / experience 25 / responsibilities 20 / location 10 / education 10) plus what is missing.
- **Job feedback loop**: mark a match as good or bad - skills in the jobs you like are boosted, skills in rejected jobs are penalised, and all matches are re-scored immediately.
- **Bulk decisions + CSV export**: select several matches to approve (shortlist) or reject in one action, or export the ranked list to CSV.
- **Hiring news that works**: Hacker News "Ask HN: Who is hiring?" plus WeWorkRemotely, Remotive and Arbeitnow, with weighted relevance so Python/AI/backend roles rank first.
- **AI providers**: Ollama (local, default fallback), **NVIDIA NIM** (your key, active now), Gemini and OpenRouter - switchable from Settings with automatic fallback to Ollama.
- **Optional API-key guard**: set `JARVIS_API_KEY` to require an `X-API-Key` header on every mutating request.
- **Automation**: n8n 2.46.7 installed (`C:\JARVIS\n8n`) with 5 workflows; on 8 GB RAM n8n may OOM so JARVIS auto-falls back to native execution (after approval).
- **Pages**: Command Center, AI Assistant, Job Discovery, Matched Jobs, Resume Intelligence, Resume Generator, Email Access, Document Studio, Application Manager, Interviews, Automation Center, Analytics, Settings.

## Run (production)
```powershell
# build the dashboard once
cd C:\JARVIS\frontend
npm run build

# start API + dashboard (one process, one port)
powershell -ExecutionPolicy Bypass -File C:\JARVIS\scripts\start_prod.ps1
```
Open **http://127.0.0.1:8000**. Stop with `C:\JARVIS\scripts\stop_prod.ps1`.
Windows autostart is already enabled (`/system/startup/enable` → `Startup\JARVIS.cmd`), so JARVIS starts when you log in.

## Run (development)
```powershell
# 1. backend
cd C:\JARVIS\backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. frontend (Vite proxies /api to the backend)
cd C:\JARVIS\frontend
npm run dev
```
Open http://127.0.0.1:5173

## Modules
| Module | Entry point |
|---|---|
| Jobs + resume matching | `/jobs/search`, `/jobs/match-resume`, `/jobs/top-matches` |
| Job decisions | `/jobs/bulk-action`, `/jobs/{id}/feedback`, `/jobs/feedback/weights`, `/jobs/export.csv` |
| Application preparation | `/applications/prepare` (approval required, never auto-submits) |
| Gmail (read-only first) | `/emails/fetch`, `/emails/draft`, `/emails/approve-send` |
| Hiring news | `/hiring-news/fetch` |
| Government exam mentor | `/study/start`, `/study/answer`, `/study/progress` |
| Tasks + reminders + schedules | `/tasks`, `/schedules` |
| Developer assistant | `/developer/analyze`, `/developer/explain` |
| File management | `/files`, `/files/summarize` |
| Approvals | `/approvals`, `/actions`, `/actions/{id}/approve`, `/actions/{id}/reject` |
| Resume sections | `/resumes/{id}/sections` (GET/POST), `/sections/{id}` (PATCH/DELETE) |
| Resume generator (from JD) | `/resume-generator/preview`, `/resume-generator/save`, `/resume-generator/versions`, `/resume-generator/{id}/download` |
| Email access | `/gmail/status`, `/gmail/account`, `/emails`, `/emails/{id}`, `/emails/fetch`, `/emails/draft` |
| Tailored documents | `/documents/generate`, `/documents`, `/documents/{id}/download` |
| Interviews | `/interviews` (CRUD), `/interviews/{id}` (PATCH/DELETE) |
| Analytics | `/analytics/overview`, `/analytics/jobs`, `/analytics/applications` |
| Automation | `/automation`, `/automation/run`, `/automation/logs`, `/automation/n8n` |
| LLM provider | `/system/llm` (GET/PUT) |
| Security | `/system/auth` (GET) |
| Voice (push-to-talk) | `/voice/transcribe`, `/voice/tts` |
| Startup controls | `/system/startup/enable`, `/system/startup/disable` |
| System monitor | `/system/status`, `/system/unload-model` |
| Backup / restore | `/system/backup`, `/system/backups`, `/system/restore?name=<file>` |

## Test
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python -m pytest tests -q   # uses a throwaway DB in %TEMP%, never jarvis.db
cd C:\JARVIS\frontend
npm run build
npx oxlint
```

## AI model
Ollama `qwen3:1.7b` (default, ~8 tok/s on this laptop), `qwen3:4b` also pulled for higher-memory machines. Set `OLLAMA_MODEL` in `backend/.env` to switch. The model unloads 2 minutes after the last request. Only one AI job runs at a time.

Cloud providers (never required, keys live only in `backend/.env`, never in the DB or git):
```powershell
LLM_PROVIDER=nvidia         # ollama | nvidia | gemini | openrouter
NVIDIA_API_KEY=...
NVIDIA_MODEL=nvidia/nemotron-3.5-bolt-e4b
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
```
Switch the active provider at runtime from Settings → AI Provider. If the selected provider has no key or fails, JARVIS falls back to Ollama automatically. The NVIDIA provider tries a small chain of NIM models and uses the first one that answers, because some models reply in a reasoning channel instead of the content channel.

> Your NVIDIA key was pasted into this chat in plain text. Treat it as exposed: rotate it in the NVIDIA console and put the new value in `backend/.env` (that file is gitignored).

## Security
Single-user local mode by default: the app binds to `127.0.0.1` and no key is needed. To require a key on every mutating request (POST/PUT/PATCH/DELETE):
```powershell
# backend/.env
JARVIS_API_KEY=choose-a-long-random-string
```
Clients then send `X-API-Key: choose-a-long-random-string`. `GET /system/auth` reports whether the guard is on and shows a non-reversible fingerprint.

## Backup
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\backup.py create weekly
.\.venv\Scripts\python scripts\backup.py list
```

## Documentation
| Doc | Purpose |
|---|---|
| `docs/INSTALLATION_GUIDE.md` | first-time setup |
| `docs/USER_GUIDE.md` | day-to-day use of every page |
| `docs/ARCHITECTURE.md` | how the pieces fit together |
| `docs/APPROVAL_SECURITY.md` | what needs approval, what is never automated |
| `docs/PERFORMANCE_GUIDE.md` | measured RAM/CPU/latency and tuning |
| `docs/TROUBLESHOOTING.md` | fixes for common errors |
| `docs/GMAIL_SETUP.md` | Google OAuth setup |
| `docs/JOB_DISCOVERY.md` | job sources and scoring |
| `docs/RESUME_GENERATOR.md` | paste a JD, get a targeted resume |
| `docs/EMAIL_ACCESS.md` | connect Gmail, read and draft replies |
| `docs/EXAM_MENTOR.md` | exam mentor usage |
| `docs/HIRING_NEWS.md` | news sources |
| `docs/PRODUCTIVITY.md` | tasks, schedules, developer, files |
| `docs/DASHBOARD.md` | frontend walkthrough |
| `docs/VOICE.md` | voice assistant |
| `docs/AUTOMATION.md` | n8n workflows and native fallback |
| `docs/PROGRESS.md` | phase checklist and test counts |

## Still pending (one user action)
- **Gmail OAuth consent** — see `docs/GMAIL_SETUP.md`:
  ```powershell
  cd C:\JARVIS\backend
  .\.venv\Scripts\python scripts\gmail_auth.py
  ```
  Needs `C:\JARVIS\credentials\credentials.json`. Add `--send` to also get the `gmail.send` scope.

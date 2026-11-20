# JARVIS Progress Checklist

- [x] Phase 1 — Foundation: FastAPI + SQLite + Ollama client, /health, /chat, /system/status (3 tests pass)
- [x] Phase 2 — Job Discovery: resume PDF parsing, Wellfound/Hirist connectors (public only), dedupe, scoring 35/25/20/10/10, ranking, /jobs/* (6 tests)
- [x] Phase 3 — Application Mgmt: /applications/prepare creates Ready-for-approval + pending Approval with hash snapshot; /approvals approve/reject; approve = Approved but NOT auto-submitted (manual submit via original URL); status machine enforces 11 statuses; history logged (7 tests)
- [x] Phase 4 — Gmail: OAuth read-only (`scripts/gmail_auth.py`), categorisation (recruiter/interview/assessment/job_alert/spam/other), company+role+date extraction, drafts, send blocked without approval AND without gmail.send scope, changed-draft refusal (11 tests)
- [x] Phase 5 — Hiring News: RSS/JSON public feeds (WWR, Remotive), role+hire keyword filtering, 45-day freshness flag, salary only if published, URL-hash dedupe, saved to SQLite (7 tests)
- [x] Phase 6 — Govt Exam Mentor: syllabus seed (SSC CGL/CHSL, RBI Assistant, IBPS PO), daily 3-topic plan (weak-topic priority), Ollama teaching, verified question bank, answer evaluation, mastery + weak-topic tracking (12 tests)
- [x] Phase 7 — Tasks + Developer + Files: natural-language task parsing (today/tomorrow/7 PM), categories, overdue, confirm-before-delete, reminders fire once, productivity report, scheduler pause/resume/stop, Python AST analysis + dangerous-command detection, file access locked to C:\JARVIS (17 tests)
- [x] Phase 8 — Frontend Dashboard: React 19 + Vite 8 + TS 7 + Tailwind 4, 14 pages, typed API client with `/api` proxy to 127.0.0.1:8000, live CPU/RAM/Ollama header, approvals UI, lint + typecheck + build clean
- [x] Phase 9 — Voice + Automations: push-to-talk mic (never left open), local faster-whisper `tiny` STT, pyttsx3 TTS + browser speech, orchestrator intent routing to real agents, Windows startup controls, schedule pause/resume (17 tests)
- [x] Phase 10 — Final integration: rotating logs, backup/restore (CLI + API), 16 live endpoints verified, 30 integration/recovery tests, 5 performance/load scripts, 5 new docs
- [x] Phase 11 — Approval-first command center + gap completion: `ActionProposal` action layer, n8n automation with native fallback, JARVIS UI redesign, Document Studio (structured sections + tailored resume/cover-letter versioning + download), pluggable LLM providers (Ollama/Gemini/OpenRouter with fallback), optional API-key auth guard, interviews/analytics/profile/notifications APIs, 84 routes (37 tests)

## Phase 13 — Resume Generator, Email Access, NVIDIA provider
- **Resume Generator** — new `services/resume_generator.py` + `api/resume_generator.py` + **Resume Generator** page. Paste a JD → parse title/company/skills/experience → check every requirement against the active resume (text + structured sections) → rebuild the resume (JD skills first, bullets re-ordered by relevance) → coverage report with honest gaps. Optional AI summary rewrite that is rejected if it mentions a technology absent from the resume. Chat intent `resume_generator` goes through the normal approval card.
- **Resume Intelligence upgraded** — editable skill chips, editable resume text with re-detection, "this looks like a stub" warning, `Set active` per version, `is_active` column now drives job matching.
- **Email Access** — new page + `/gmail/account` (connected address, scopes), `/emails/{id}` (full body), `Prepare reply` with Copy / "Open in your mail app" so the user sends the mail themselves. `/emails/drafts` no longer shadowed by `/emails/{id}`.
- **NVIDIA NIM provider** — `NVIDIA_API_KEY` / `NVIDIA_MODEL` in `backend/.env` (now actually loaded: `SettingsConfigDict(env_file=".env")`), OpenAI-compatible endpoint, model chain `nvidia/nemotron-3.5-bolt-e4b` → `meta/muse-glimmer-30b` → `nvidia/nemotron-3.5-lightning-30b-a3b` because some NIM models answer in a reasoning channel. Active provider switched to NVIDIA; Ollama stays the automatic fallback. ~1-3 s answers.
- **Bugs fixed** — `Settings` never read `backend/.env`; `asyncio.run()` inside the async resume generator silently disabled the AI polish; `parse_jd` company regex was case-sensitive; JD title was not trimmed ("Python Backend Developer to build and scale our APIs"); coverage only checked the skill list instead of the full resume text; double bullet markers ("- - Built REST APIs"); overlapping skills ("rest" and "rest api").

**Total tests: 153/153 passing (backend).** Frontend: oxlint **0 errors / 0 warnings**, `npm run build` clean with route-level code splitting (largest chunk 390 kB, main bundle 13 kB). Tests now run against a throwaway database in `%TEMP%` and never touch `jarvis.db`.

## Phase 12 — Production deployment + matching quality
- **Single-origin production build** — the FastAPI app now serves `frontend/dist` (SPA with history fallback) and strips the `/api` prefix itself, so dashboard and API live on one port: `http://127.0.0.1:8000`.
- **Service scripts** — `scripts/start_prod.ps1` (starts Ollama if needed, starts uvicorn, waits for `/health`), `scripts/stop_prod.ps1`. Windows autostart entry now calls the production script instead of a Vite dev server.
- **Job matching fixed** — connectors now fill real skills, seniority is parsed from the posting (`No experience required` → entry, `1 year(s)` → mid, `senior` → senior), and the score shows every component plus the notes behind it. Live top results are now `Python Developer @ InstaAstro` 75%, `Python Developer @ Simpli Intern` 72% instead of generic director/architect roles at 53%.
- **Job feedback loop** — `POST /jobs/{id}/feedback` (good/bad) learns skill boosts and penalties from your judgements, stores them in `app_settings` and re-scores every stored job immediately.
- **Bulk decisions + CSV export** — `POST /jobs/bulk-action` (approve → shortlist, reject) writes application history; `GET /jobs/export.csv` downloads the ranked list. UI: checkboxes, "Approve selected"/"Reject selected", thumbs up/down per job, export button.
- **Hiring news fixed** — added the Hacker News "Ask HN: Who is hiring?" thread (parsed from the `Company | Role | Location | …` comment header) plus WeWorkRemotely region/skills parsing, weighted relevance and retry with backoff. A fetch now stores ~10 relevant rows instead of 1.
- **Test isolation** — `backend/tests/conftest.py` points `DATABASE_URL` at a temp file, so test runs no longer pollute the live database.
- **Data hygiene** — `backend/scripts/reset_operational_data.py` clears operational tables while keeping preferences, settings and real hiring news; `scripts/restore_resume_profile.py` restores the baseline resume skills.
- **Routing bug fixed** — `/jobs/{job_id}` no longer shadows `/jobs/collect`, `/jobs/search`, `/jobs/export.csv` or `/jobs/feedback/weights`.

## Phase 12 — Bugs found and fixed
- `required_skills` was filled with the *matching* skills instead of the job's real requirements → now stores the actual extracted requirements.
- A job re-discovery wiped user feedback → feedback is preserved by URL across runs.
- `fetch_jobs` let a network failure escape to the caller → each source group is now failure-isolated.
- `_parse_date` crashed on epoch timestamps (Arbeitnow) → int/float timestamps are handled.
- `application_url` uniqueness broke on Hacker News rows → each comment now uses its own permalink.


## Phase 9 — Orchestrator routing
`/chat` classifies the request and calls the matching specialist agent instead of only talking to the model:
jobs, tasks, gmail, news, study, developer, files, and a general chat fallback.

Live check (2026-11-09): "Find Python backend jobs in India" → `jobs` (2.3 s), "show my pending tasks" → `tasks` (0.1 s),
"start my SSC CGL preparation" → `study` (38.2 s), "what is 2+2" → `chat` (15.5 s).

## Phase 10 — What was added
- **Logging** — `app/utils/logging_setup.py`: rotating file handler (1 MB × 3), noisy loggers (httpx, uvicorn.access, comtypes) at WARNING, logs never contain tokens or email bodies.
- **Backup / restore** — `app/services/backup.py`: sqlite3 online backup (safe while the server runs), integrity check, safety copy before every restore, newest 20 kept.
  - CLI: `scripts/backup.py create|list|restore|prune`
  - API: `POST /system/backup`, `GET /system/backups`, `POST /system/restore?name=<file>`
- **Test scripts** — `scripts/performance_test.py` (per-endpoint latency + RAM to `data/reports/performance_report.json`), `scripts/concurrency_test.py` (proves the AI semaphore serialises requests).
- **Docs added** — `docs/ARCHITECTURE.md`, `docs/APPROVAL_SECURITY.md`, `docs/PERFORMANCE_GUIDE.md`, `docs/TROUBLESHOOTING.md`, `docs/USER_GUIDE.md`.

## Phase 10 — Bugs found and fixed
- `/jobs/top-matches` was shadowed by `/jobs/{job_id}` → route moved earlier.
- Resume parsing was not patchable in tests → now resolved through `resume_module`.
- Chat fallback swallowed failures → now returns an `error` field.
- Job connector returned empty titles → rewritten to parse real Wellfound card HTML (title, company, location, salary incl. `₹`, posting date).
- Vite proxy 502s after a backend restart → restart the dev server (stale upstream sockets).

## Phase 11 — What was added
- **Approval-first action layer** — `ActionProposal` model + `services/proposals.py` (SHA-256 payload hash, pending→approved/rejected/executed/failed) + `services/action_handlers.py` (14 registered handlers). Chat, API and UI all funnel through it.
- **Orchestrator rewrite** — actionable intents propose; read-only intents execute directly.
- **New APIs** — `actions`, `assistant`, `automation`, `documents`, `interviews`, `analytics`, `profile`, `notifications`, `resumes`; 84 routes total.
- **Automation** — n8n webhook client + 5 workflows + native fallback; `POST /automation/run` creates a proposal first.
- **Document Studio** — `resume_sections` + `document_versions` tables, `services/documents.py` (deterministic tailoring, honest gap disclosure), API + UI page, versioned downloads.
- **Pluggable LLM** — `services/llm.py` dispatches to Ollama (default), Gemini or OpenRouter; runtime switch via `PUT /system/llm`; automatic fallback to Ollama on missing key or provider failure.
- **Auth guard** — `services/auth.py` + middleware; optional `JARVIS_API_KEY` env requires `X-API-Key` on mutating requests; `GET /system/auth` reports a fingerprint only.
- **Frontend** — JARVIS dark-navy/cyan redesign, Document Studio page, Settings AI-provider + security panels, route-level lazy loading, `manualChunks` for react/charts/ui.
- **Docs added** — `docs/AUTOMATION.md`, `docs/DOCUMENT_STUDIO.md`.

## Phase 11 — Bugs found and fixed
- `settings.api_key` was shadowed by a same-named module function → renamed access and made the lookup type-safe.
- `"tailor my resume"` matched the `resume` intent before `documents` → reordered `INTENTS`.
- `vite.config.ts` `manualChunks` object form is invalid in Vite 8 / rolldown → switched to the function form.
- `AutomationCenter.tsx` referenced a `load()` that was removed during the lint cleanup → restored.
- Frontend `set-state-in-effect` warnings across 7 pages → rewritten to async effects with cancellation guards (oxlint now 0 warnings).

## Ollama (installed)
- Ollama 0.40.15 via winget. Models pulled: `qwen3:4b` (2.5 GB) and `qwen3:1.7b` (1.2 GB).
- **Benchmark on this laptop (8 GB RAM, i5-1035G1, CPU-only):**
  - qwen3:4b: 180 s for a one-sentence answer, 2.3 tok/s, RAM 93% used → too slow.
  - qwen3:1.7b with `think:false`: 16 s cold, 8.19 tok/s warm → **default model**.
- Config: `OLLAMA_MODEL=qwen3:1.7b`, `OLLAMA_THINK=false`, `OLLAMA_KEEP_ALIVE=2m` (auto-unload to free RAM).
- Switch back to the stronger model when you have more RAM: set `OLLAMA_MODEL=qwen3:4b` in `backend/.env`.
- Endpoint `POST /system/unload-model` frees RAM immediately.

## Still pending (user action)
- **Gmail OAuth consent** — the only thing left, deferred by the user to the end:
  ```powershell
  cd C:\JARVIS\backend
  .\.venv\Scripts\python scripts\gmail_auth.py
  ```
  Needs `C:\JARVIS\credentials\credentials.json` (Google Cloud → OAuth 2.0 Desktop client → download JSON).
  Add `--send` for the `gmail.send` scope required to actually send an approved email.
- **n8n runtime** — n8n 2.46.7 OOM-crashes on this 8 GB host. The workflows are installed and JARVIS falls back to native execution after approval. Run n8n on a machine with more RAM (or via Docker) for true webhook execution.
- **Deliberate deviations** (documented, working alternatives in place): SQLite instead of PostgreSQL/pgvector + Alembic, deterministic router instead of LangGraph, local single-user mode instead of JWT/multi-user auth, no Redis/Celery, no permitted form-fill assistance (by design — JARVIS never submits applications for you).
- Everything else in the plan is implemented, tested and documented.

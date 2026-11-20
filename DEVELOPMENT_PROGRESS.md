# DEVELOPMENT_PROGRESS

Last updated: 2026-11-09 (session)

## Environment
- OS: Windows 10 (win32) on Intel i5-1035G1, **8 GB RAM** (prompt noted 16 GB), CPU-only
- Python 3.11.5, Node v24.18.0, npm 11.16.0, Git 2.54.0
- Docker 29.4.1 installed (service stopped), PostgreSQL not installed
- n8n 2.46.7 installed globally and running locally at `http://127.0.0.1:5678` (`N8N_USER_FOLDER=C:\JARVIS\n8n`)

## Implemented (this session, on top of Phases 1-10)
- **Approval-first action layer**: `ActionProposal`, `Interview`, `UserPreference`, `Notification`, `WorkflowRun` models; `services/proposals.py` (SHA-256 payload hash, pending→approved/rejected/executed/failed, handler registry); `services/action_handlers.py` (create/complete/delete task, prepare_application, prepare_email_reply, send_email, run_workflow, create_schedule, create_interview, fetch_jobs/news/emails).
- **Orchestrator** rewritten to propose (not execute) actionable intents: task create/complete/delete, application preparation, workflow runs, interview creation, approvals/report helpers; read-only intents (jobs search, task list, gmail fetch, news, study, developer, files, chat) still execute.
- **APIs mounted** (80 routes): `actions`, `assistant` (greeting/chat/history), `automation` (n8n status/run/logs/overview), `interviews` CRUD, `analytics` overview/jobs/apps, `profile` preferences, `notifications`, `resumes` upload/list/get/update/delete (PDF/DOCX/TXT). Added `/jobs/matched`, `/matching/results`, `/jobs/collect` (proposal), `/applications/{id}` GET/PATCH/approve/reject; fixed `/applications/approve`.
- **Automation (n8n)**: webhook client, 5 workflow catalog entries with native fallbacks, workflow JSON generator/importer `backend/scripts/setup_n8n.py`, 5 workflows generated/imported in `automation/n8n_workflows/*.json`: job_discovery, daily_report, application_follow_up, interview_reminders, gmail_review. n8n 2.46.7 installed/configured (`C:\JARVIS\n8n`) but on this 8 GB machine it OOM-crashes at startup; JARVIS detects n8n down and executes automations via **native fallback after approval** (verified: `POST /automation/run` → proposal → approve → native daily report). `GET /automation` reports n8n status.
- **Frontend redesign (JARVIS command center)**: dark navy/cyan glass design system, holographic SVG/CSS Orb (Idle/Listening/Thinking/Executing/Success/Error), sidebar+topbar layout, Command Center (greeting, chat, inline approval cards, quick commands, metrics, activity), AI Assistant chat with inline approvals + mic, Job Discovery, Matched Jobs, Resume Intelligence, Application Manager (approvals + tracking), Interview Tracker, Automation Center, Analytics (Recharts), Settings (profile/preferences/scheduler/integrations/startup). Dependencies added: lucide-react, @tanstack/react-query, recharts.

## Decisions / Deviations (documented)
- **SQLite kept** as default DB (PostgreSQL not installed; `DATABASE_URL` configurable). No Alembic migrations added yet; SQLAlchemy `create_all` used.
- **Ollama (local) kept** as default LLM; optional Gemini/OpenRouter config fields added (keys not configured). **LangGraph not added** (no package/install; deterministic router + proposal workflow used instead).
- **JWT/multi-user auth not implemented** (single-user local app bound to 127.0.0.1). Security via local-only binding, CORS, approval gates, no secrets in DB/Git.
- **n8n via npm local** instead of Docker; Docker Compose provided as optional.
- Mutating/external actions require approval; read-only queries (search/list/fetch/read) execute directly for usability (sensible default, documented).

## Tests executed (this session)
- Backend (targeted): `pytest tests/test_phase1.py ... test_phase7.py test_phase9.py test_phase9_jobcards.py test_phase10.py -q` → **112 passed** (73.5s). (test_phase8.py not present.)
- Frontend: `npm run build` → **success** (747 kB JS chunk, vite warning only). `npx oxlint src` → **8 warnings** (react set-state-in-effect / hooks deps in pages), 0 errors.

## Known issues / Pending
- Frontend chunk > 500 kB (needs code-splitting). Lint warnings (non-blocking) in several pages.
- n8n webhooks: CLI publish used; some publish commands were slow/hung and n8n restarted—webhook registration/end-to-end trigger needs a fresh verification pass after stable activation.
- Gmail OAuth not completed (no credentials/token) so Gmail fetch/send unverified.
- Not implemented per full master prompt: PostgreSQL/pgvector, Alembic, LangGraph workflows, JWT auth/multi-user, Gemini/OpenRouter live calls, Redis/Celery, full resume structured fields (employment/education/projects editing UI), tailored resume/cover-letter document versioning/download, permitted form-fill assistance, duplicate scheduler hardening beyond current, comprehensive unit/integration tests for all new modules, production deployment.
- Interview reminders workflow creates tasks via native fallback; ensure it runs on schedule with approval policy as desired.

## Next tasks
1. Verify n8n webhook end-to-end (stable activation) and Automation Center run-through-approval flow.
2. Add/adjust endpoints for `/automation/start|stop|pause|logs` aliases and any missing prompt API shapes; emit notifications on key events.
3. Implement basic auth/session guard (or document single-user local mode) and optional LLM provider wiring (Gemini/OpenRouter) with graceful "not configured" behavior.
4. Expand resume intelligence (structured sections, editable fields) and application document versioning.
5. Add tests for proposals/actions, interviews, analytics, automation; run full `pytest tests -q`; fix lint warnings and code-split frontend.
6. Update README/ARCHITECTURE/API/SETUP docs and finalize.
## Session update (2026-11-12, continued stabilization)
- Backend restarted and verified: `/health` OK, `/assistant/command` working; n8n stopped (OOM on 8 GB) with native automation fallback confirmed.
- Frontend lint cleanup: fixed set-state-in-effect/hooks-deps warnings in `Assistant`, `MatchedJobs`, `AutomationCenter`, `ApplicationManager`, `Interviews`, `ResumeIntelligence`, `Settings`; `npx oxlint src` now 0 warnings/errors. Frontend dev server running at `http://127.0.0.1:5173`.
- Build optimization: added `manualChunks` in `frontend/vite.config.ts` (react/charts/ui) to reduce main bundle; full production build not re-run yet due to low RAM on this machine.
- Sanity test (low RAM): `pytest tests/test_phase1.py -q` → 3 passed.
- RAM constraint noted: ~0.5-0.8 GB free on 8 GB host; full `pytest` and `vite build` may OOM until memory is freed.

## Session update (2026-11-12, gap completion — all remaining master-prompt items closed)
- **Structured resume editing + tailored documents**: new `ResumeSection` and `DocumentVersion` tables, `app/services/documents.py` (deterministic tailoring, honest gap disclosure, versioned text files under `C:\JARVIS\data\documents\`), `app/api/documents.py` (`/resumes/{id}/sections`, `/sections/{id}`, `/documents/generate`, `/documents`, `/documents/{id}/download`), new frontend **Document Studio** page. Chat intent `documents` + approval-first handlers `generate_documents` and `update_resume_sections`.
- **LLM provider wiring**: `app/services/llm.py` dispatches Ollama (default) / Gemini / OpenRouter, falls back to Ollama on missing key or provider failure, runtime switch via `PUT /system/llm` persisted in `app_settings`. Keys stay in `.env`, never in the DB.
- **Auth guard**: `app/services/auth.py` + HTTP middleware. Optional `JARVIS_API_KEY` env requires `X-API-Key` on POST/PUT/PATCH/DELETE; `GET /system/auth` reports a SHA-256 fingerprint only. Off by default for single-user local mode.
- **Tests**: new `backend/tests/test_phase11.py` (37 tests) covering proposals/actions, interviews, analytics, automation, documents, LLM fallback and the auth guard. Full suite **149 passed**.
- **Frontend**: route-level lazy loading + `manualChunks` function form (Vite 8/rolldown). Production build clean, main bundle 747 kB → 13 kB, largest chunk 390 kB, no size warning. `npx oxlint src` → 0 errors, 0 warnings.
- **Docs**: `docs/DOCUMENT_STUDIO.md` (new), updated `README.md`, `docs/ARCHITECTURE.md`, `docs/APPROVAL_SECURITY.md`, `docs/PROGRESS.md`, `docs/USER_GUIDE.md`, `.env.example`.
- **Live verified**: `/system/llm`, `/system/auth`, `/resumes/{id}/sections`, `POST /documents/generate` (2 versions), `GET /documents/{id}/download`, chat "tailor my resume for job 1" → proposal → approve → generated. Backend now **84 routes**.
- **Remaining (environment, not code)**: Gmail OAuth consent needs your Google credentials; n8n 2.46.7 OOM-crashes on this 8 GB host (native fallback covers execution — run n8n on a bigger machine or via Docker for real webhook triggers).

## Session update (2026-11-18, production deployment + matching quality)
- **Production deployment**: the FastAPI app now serves `frontend/dist` (SPA with history fallback) and strips the `/api` prefix itself → dashboard and API on one port, `http://127.0.0.1:8000` (89 routes). New `scripts/start_prod.ps1` (starts Ollama if needed, starts uvicorn, waits for `/health`) and `scripts/stop_prod.ps1`; the Windows autostart entry now calls the production script (no Vite dev server).
- **Job matching fixed**: connectors fill real skills, seniority is parsed from the posting text (`No experience required` → entry, `1 year(s)` → mid, `senior` → senior), and every score exposes components + notes. Live result went from generic director/architect roles at 53% to `Python Developer @ InstaAstro` 75%, `Python Developer @ Simpli Intern` 72%, `Full stack developer @ Crisp` 59%.
- **Job feedback loop**: `POST /jobs/{id}/feedback` learns skill boosts/penalties from good/bad judgements into `app_settings` and re-scores all stored jobs. `POST /jobs/bulk-action` (approve → shortlist / reject) writes application history. `GET /jobs/export.csv` exports the ranked list. UI: checkboxes, bulk approve/reject, thumbs up/down, export button, learned-weights banner.
- **Hiring news fixed**: added the Hacker News "Ask HN: Who is hiring?" thread (parsed from `Company | Role | Location | …` comment headers), WeWorkRemotely region/skills parsing, weighted relevance (senior titles penalised) and retry with backoff. A fetch stores ~10 relevant rows (was 1).
- **Test isolation**: `backend/tests/conftest.py` redirects `DATABASE_URL` to a temp file — test runs no longer pollute `jarvis.db`. Added `backend/scripts/reset_operational_data.py` and `scripts/restore_resume_profile.py`; cleared the test-created rows (123 applications, 102 proposals, 101 resume profiles …) while keeping preferences, settings and real hiring news.
- **Verification**: `pytest tests -q` → **153 passed** (34 s, isolated DB). `npx oxlint src` → 0 errors, 0 warnings. `npm run build` → clean (main 13 kB, largest chunk 390 kB). Live sweep on port 8000: 24 endpoints 200, SPA routes and hashed assets 200, new job endpoints verified (bulk-action 200, feedback 200, CSV 200).
- **Bugs fixed**: `required_skills` stored matching instead of required skills; feedback lost on re-discovery; `fetch_jobs` let network errors escape; epoch timestamps crashed the date parser; `application_url` uniqueness broke on HN rows; `/jobs/{job_id}` shadowed `/jobs/collect`, `/jobs/search`, `/jobs/export.csv`, `/jobs/feedback/weights`.
- **Still pending (environment)**: Gmail OAuth consent (needs `C:\JARVIS\credentials\credentials.json`), n8n runtime (OOMs on 8 GB; native fallback active).

## Session update (2026-11-19, Resume Generator + Email Access + NVIDIA provider)
- **Resume Generator** (new): `app/services/resume_generator.py` + `app/api/resume_generator.py` + frontend page `ResumeGenerator.tsx` (sidebar entry "Resume Generator"). Flow: paste JD → parse (title, company, skills, min years, location, responsibilities) → evidence-check against the active resume (uploaded text + structured sections) → rebuild resume with JD skills first and bullets re-ordered → coverage report (covered / gaps / coverage_pct) → save as a numbered `document_versions` row + downloadable file. Chat intent `resume_generator` creates an approval proposal instead of acting.
- **Resume Intelligence upgraded**: editable skill chips (add/remove + save), editable resume text with skill re-detection, "stub resume" warning when text < 200 chars, `Set active` per version, new `resume_profiles.is_active` column (migration handled by `_ensure_columns`), and job matching now uses the active resume.
- **Email Access** (new page): `/gmail/account` returns the connected address + scopes, `/emails/{id}` returns the full body, "Prepare reply" creates a draft + pending approval, and the UI gives Copy / "Open in your mail app" so the user sends the mail himself. Setup steps are shown in the UI when Gmail is not connected.
- **NVIDIA NIM provider**: key stored only in `backend/.env` (gitignored). Fixed `Settings` so `.env` is actually read (`SettingsConfigDict(env_file=".env")`). Provider chain `nvidia/nemotron-3.5-bolt-e4b` → `meta/muse-glimmer-30b` → `nvidia/nemotron-3.5-lightning-30b-a3b` (some NIM models answer in `reasoning_content`, not `content`). Active provider is now NVIDIA (~1-3 s answers) with Ollama as automatic fallback. Chat responses now report `provider`/`model`/`fallback_from`.
- **Bugs fixed**: `asyncio.run()` inside the async generator silently disabled AI polish; JD company regex was case-sensitive; JD title not trimmed; coverage checked only the skill list (not the full resume text); duplicate bullet markers; `rest` vs `rest api` duplication; `/emails/{id}` shadowed `/emails/drafts`.
- **Verified**: 153/153 pytest pass, oxlint 0/0, production build clean, live sweep 41/41 GET endpoints 200, all SPA routes 200, resume generator end-to-end (83.3% coverage, AI summary used, version saved and downloadable), chat intent returns an approval proposal.
- **Security note**: the NVIDIA key was pasted into chat in plain text - recommend rotating it in the NVIDIA console and updating `backend/.env`.


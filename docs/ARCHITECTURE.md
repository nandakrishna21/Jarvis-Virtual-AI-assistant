# Architecture (JARVIS)

## Overview
Local-first personal assistant: **React (Vite) frontend** ↔ **FastAPI backend** ↔ **SQLite** + **Ollama (local LLM)** + **n8n (local automation)**. Single-user, bound to `127.0.0.1`.

```
Browser -> http://127.0.0.1:8000
              |
              +-- /assets/* and /*            -> built React SPA (frontend/dist, history fallback)
              +-- /api/*                     -> stripped to the API routes below
              v
FastAPI (8000, 89 routes)
  ├─ api/            (actions, assistant, automation, documents, interviews, analytics, profile, notifications, resumes)
  ├─ orchestrator/   (intent routing: read-only execute, mutating -> ActionProposal)
  ├─ services/       (proposals+handlers, profile, backup, startup, ollama, llm, documents, auth, job_actions)
  ├─ agents/         (job_discovery(+feedback), job_application, gmail, hiring_news, government_exam, task_manager, developer, file_manager, voice, automation, interview)
  ├─ integrations/   (n8n webhooks, gmail client)
  ├─ scheduler/      (lightweight async schedules, pause/resume)
  └─ database/       (SQLAlchemy models, SQLite session)
        |\
        | \-> Ollama 127.0.0.1:11434 (qwen3:1.7b default)
        \--> n8n 127.0.0.1:5678 (webhook workflows, native fallback)
```

**Two run modes, one bundle.** In development Vite serves the SPA on 5173 and proxies `/api` to 8000. In production the FastAPI app serves `frontend/dist` itself and rewrites `/api/*` internally, so the same build runs on a single port with a single process (lowest RAM use on this 8 GB host).

## Approval-first execution
- Mutating/external chat requests create an **ActionProposal** (type, title, plan, payload, SHA-256 hash, pending).
- User approves/rejects via `/actions/{id}/approve|reject` (or UI). Handlers run only on approval; results/errors recorded. Legacy application/email approvals remain supported.
- Read-only operations (search/list/fetch/analyze) may execute directly.
- Registered handlers: `create_task`, `complete_task`, `delete_task`, `prepare_application`, `prepare_email_reply`, `send_email`, `run_workflow`, `create_schedule`, `create_interview`, `fetch_jobs`, `fetch_news`, `fetch_emails`, `generate_documents`, `update_resume_sections`.

## Data
- SQLite file `backend/jarvis.db` (SQLAlchemy `create_all` + idempotent `_ensure_columns` ALTER TABLE helper). Key tables: jobs, job_matches, applications(+history, approvals), resumes, resume_sections, document_versions, emails(+drafts/approvals), tasks/reminders/schedules, interviews, action_proposals, notifications, workflow_runs, agent_runs, user_preferences, app_settings, study/hiring_news tables.
- Backups via `services/backup.py` + `/system/backup*` and CLI.
- Tests never touch this file: `backend/tests/conftest.py` redirects `DATABASE_URL` to a throwaway database in `%TEMP%`.

## Job matching
- Connectors read only key-free public APIs (Remotive, Arbeitnow, RemoteOK, Himalayas) and public listing pages (Internshala, Wellfound, Hirist). No auth or CAPTCHA bypass.
- `agents/job_discovery/scoring.py` scores skills 35 / experience 25 / responsibilities 20 / location 10 / education 10 from the posting itself and returns the component values and notes with every score.
- `agents/job_discovery/feedback.py` turns good/bad judgements into skill boosts and penalties stored in `app_settings`; every stored job is re-scored after a change.
- `services/job_actions.py` records bulk approve/reject decisions in the application history and exports the ranked list as CSV.

## Automation
- n8n workflows (webhook triggers) call JARVIS APIs; if n8n unavailable, catalog-defined **native fallback** runs in-process. Runs logged to `workflow_runs`.

## AI
- `services/llm.py` is the single chat entry point. Default: local Ollama (`qwen3:1.7b`, think off, 2m keep-alive, 1 concurrent job).
- Optional `gemini` / `openrouter` providers are switchable at runtime via `PUT /system/llm` (persisted in `app_settings`). Missing key or provider failure falls back to Ollama automatically.

## Documents
- `services/documents.py` builds tailored resumes and cover letters from `resume_sections` + extracted skills + the job match record. Every generation is stored as a numbered `document_versions` row plus a text file under `C:\JARVIS\data\documents\`.
- Generation is deterministic and refuses to invent facts; drafts only, never submitted.

## Security
- Bound to localhost, CORS restricted, file access limited to `C:\JARVIS`, no secrets in DB/Git/logs, no auto-submit/send, CAPTCHA/MFA/ToS respected.
- Optional API-key guard (`JARVIS_API_KEY` env) requires an `X-API-Key` header on POST/PUT/PATCH/DELETE. Off by default for single-user local mode; `GET /system/auth` reports status without revealing the key.

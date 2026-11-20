# Automation (n8n + Scheduler)

## Overview
JARVIS automations can run via **local n8n workflows** (webhook-triggered) with a **native fallback** in the backend when n8n is unavailable. **Every automation run requested by the user requires explicit approval** before execution.

## n8n (local)
- URL: `http://127.0.0.1:5678`
- Installed: npm global `n8n@2.46.7`
- Data/home: `C:\JARVIS\n8n` (`N8N_USER_FOLDER`)
- User management disabled for local single-user mode.

> **Low-RAM note (8 GB systems):** n8n 2.x can consume significant memory and may fail to start/stay up (OOM) on memory-constrained laptops. JARVIS handles this gracefully by using **native fallback execution** when n8n is unreachable. On higher-memory machines n8n webhooks work normally.

### Setup
```powershell
# Start n8n (example)
$env:N8N_USER_FOLDER='C:\JARVIS\n8n'
$env:N8N_HOST='127.0.0.1'; $env:N8N_PORT='5678'; $env:N8N_PROTOCOL='http'
$env:N8N_USER_MANAGEMENT_DISABLED='true'
n8n start

# Generate + import + activate workflows
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\setup_n8n.py
```

Workflow JSONs: `C:\JARVIS\automation\n8n_workflows\`

### Workflows
| Workflow | Webhook | JARVIS API called | Purpose |
|---|---|---|---|
| Job Discovery | `/webhook/jarvis/job-discovery` (POST) | `POST /jobs/search` | Collect and score new listings |
| Daily Report | `/webhook/jarvis/daily-report` (GET) | `GET /analytics/overview` | Daily job-search summary |
| Application Follow-up | `/webhook/jarvis/application-follow-up` (GET) | `GET /applications` | Identify follow-ups (drafts only) |
| Interview Reminders | `/webhook/jarvis/interview-reminders` (GET) | `GET /interviews` | Upcoming interviews/reminders |
| Gmail Review | `/webhook/jarvis/gmail-review` (POST) | `POST /emails/fetch` | Fetch recruiter/interview emails |

## Approval-before-execution
- User asks to run automation (chat/UI/API `POST /automation/run`) -> JARVIS creates an `ActionProposal` (`run_workflow`) with the plan.
- User approves in Assistant/Approvals -> backend executes via n8n webhook if healthy, else native fallback.
- Runs recorded in `workflow_runs` and visible in Automation Center (`GET /automation`, `/automation/logs`).

## Scheduler controls
- Lightweight async scheduler in `app/scheduler/scheduler.py`.
- Pause/resume/stop/start: `/automation/pause|resume|start|stop` and `/schedules/pause|resume`.
- Schedules disabled by default; no duplicate scheduler instances.

## Safety
- No emails/applications sent automatically.
- Automations never bypass CAPTCHA/MFA/site rules.
- All automation stays local.

# Approval & Security Model

## What it does
Defines exactly what JARVIS may do on its own, what needs your explicit approval, and what it will never do.

## Why
JARVIS holds your private email, files and job applications. Automation without a safety net could send a wrong email or submit a false application. The approval system makes every external action visible before it happens.

## Three categories

### Category A - Safe automatic (no approval needed)
- Public job discovery and resume analysis
- Job matching, scoring and ranking
- Reading and summarising email (read-only OAuth)
- Hiring news collection and summarising
- Study plans, quizzes, progress reports
- Local reports, task queries, file listing inside `C:\JARVIS`

### Category B - Approval required
| Action | Where you approve | What happens without approval |
|---|---|---|
| Send an email | Approvals page | Draft is created, nothing is sent |
| Submit a job application | Approvals page | Materials are prepared, nothing is submitted |
| Generate tailored resume / cover letter | Assistant or Approvals page | Nothing is written; no version is created |
| Edit resume sections | Document Studio (explicit save) | Existing sections untouched |
| Create / complete / delete a task | Approvals page | Nothing changes in the task list |
| Run an automation workflow | Automation Center / Approvals page | Workflow does not start |
| Schedule an interview | Approvals page | No interview record, no reminder task |
| Collect jobs / hiring news / mail | Approvals page | No fetching happens |
| Upload / share a document | Never automated | Not supported |
| Delete or overwrite a file | Not automated | Not supported |
| Change account settings | Not automated | Not supported |
| Destructive shell commands | Never automated | Detected and reported only |

### Category C - Prohibited - JARVIS never does these
- Bypass CAPTCHA or MFA
- Steal or expose credentials, tokens or keys
- Submit false job applications or fabricate qualifications
- Send an email without approval
- Make purchases
- Run unknown scripts blindly
- Upload private data to public AI services
- Act against a website's terms of service

## How an approval works
1. You ask for an action (prepare application, prepare email reply).
2. JARVIS creates the content and stores a **snapshot** - the exact recipient, subject, body, attachments and a SHA-256 hash.
3. A pending approval record appears on the Approvals page showing that exact content.
4. You click Approve or Reject.
5. **Approve** marks it approved. **Reject** cancels it. Either way the decision is recorded.
6. Decisions are **one-time**. A second approve is refused.

### Email sending needs two independent gates
1. A pending approval for that exact draft, and
2. A token that holds the `gmail.send` scope.

If the draft text changed after the approval was requested, sending is refused. If the scope is missing, JARVIS tells you to run `scripts/gmail_auth.py --send`.

### Job applications are never auto-submitted
Approval moves the application to `Approved` and stops there. JARVIS shows the original link so **you** submit on the employer's site. This keeps you out of CAPTCHA, MFA and site-terms problems, and guarantees the content is genuinely yours.

## Privacy controls
- Backend binds to `127.0.0.1` only - not reachable from your network or the internet.
- CORS allows only `http://127.0.0.1:5173` and `http://localhost:5173`.
- File access is restricted to `C:\JARVIS` (`JARVIS_FILE_ROOT` can widen it deliberately).
- OAuth tokens live in `C:\JARVIS\credentials\`, outside the database.
- `.gitignore` excludes `.env`, `credentials.json`, `token.json`, `*.db`, `resumes/`, `logs/`, `backups/`.
- Logs never contain tokens or message bodies.
- All AI inference is local by default. No request text leaves your machine.
- Optional cloud providers (Gemini/OpenRouter) are off unless you set a key yourself; JARVIS never sends your data to them without your explicit configuration.

## Optional API-key guard
By default JARVIS runs in single-user local mode with no authentication. To
require a key on every mutating request, set `JARVIS_API_KEY` in
`backend/.env` and restart the backend:

```powershell
JARVIS_API_KEY=choose-a-long-random-string
```

Clients must then send `X-API-Key: choose-a-long-random-string` on
POST/PUT/PATCH/DELETE. Read endpoints stay open so the UI can still load.
`GET /system/auth` reports whether the guard is active and shows only a
non-reversible SHA-256 fingerprint of the key - never the key itself.

## Test the approval system
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python -m pytest tests\test_phase3.py tests\test_phase4.py tests\test_phase10.py tests\test_phase11.py -v
```
These cover: reject cancels, approve does not auto-submit, a decision cannot be repeated, email reject blocks sending, send is refused without the scope, changed content is refused, a chat request creates a proposal without executing, and the API-key guard blocks and allows mutating requests correctly.

## Verify manually
1. Prepare an application on the Jobs page.
2. Open Approvals - the exact content is shown.
3. Click Reject - the application becomes `Withdrawn`.
4. Prepare it again and Approve - it becomes `Approved` and the response says `NOT auto-submitted`.

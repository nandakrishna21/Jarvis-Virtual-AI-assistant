# Gmail Setup (Phase 4)

## What it does
Reads your Gmail via the official API, categorises messages (recruiter / interview / assessment / job_alert / spam / other), extracts company, role and dates, creates drafts, and only sends after your approval of the exact message.

## Why required
Gmail API needs your explicit OAuth consent. JARVIS starts read-only and never sends silently.

## Safety
- Token stored at `C:\JARVIS\credentials\token.json` (never in SQLite, never in Git).
- `credentials.json` and `token.json` are in `.gitignore`.
- Send requires BOTH: your approval of the exact draft AND a token with `gmail.send` scope. If the draft text changed after approval, sending is refused.

## Step 1 — Google Cloud Console
1. Open https://console.cloud.google.com and create a project (e.g. `JARVIS Personal`).
2. Enable **Gmail API** (APIs & Services → Library → Gmail API → Enable).
3. OAuth consent screen → External → add your Google account → add scope `https://www.googleapis.com/auth/gmail.readonly`.
4. Credentials → Create Credentials → OAuth client ID → **Desktop app**.
5. Download JSON and rename to `credentials.json`.
6. Put it in `C:\JARVIS\credentials\credentials.json`.

## Step 2 — Authenticate (PowerShell, from C:\JARVIS\backend)
```powershell
.\.venv\Scripts\python scripts\gmail_auth.py
```
A URL opens; paste the code, press Enter. Token saved to `C:\JARVIS\credentials\token.json`.
For sending later (separate consent): `.\.venv\Scripts\python scripts\gmail_auth.py --send`

## Step 3 — Test
```powershell
curl http://127.0.0.1:8000/gmail/status
curl -X POST http://127.0.0.1:8000/emails/fetch -H "Content-Type: application/json" -d '{"max_results":10}'
curl "http://127.0.0.1:8000/emails?category=recruiter"
```

## Drafts and sending
```powershell
curl -X POST http://127.0.0.1:8000/emails/draft -H "Content-Type: application/json" -d '{"email_id":1}'
curl -X POST http://127.0.0.1:8000/emails/approve-send?approval_id=1
```

## Common errors
- `credentials.json` missing → re-download from Cloud Console, rename correctly
- `Access blocked` / app unverified → expected for personal use; add your account as a test user on the consent screen
- `token lacks gmail.send scope` → run `gmail_auth.py --send` and re-approve
- `draft changed since approval request` → create a new draft/approval after editing

## Verify
`GET /gmail/status` should show `credentials_present: true` and `token_present: true`, and `GET /emails` should list fetched messages.

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

## Rotating the OAuth client secret (recommended after any leak)

Rotating does **not** delete your Gmail data or the OAuth consent screen. You only replace the client secret, then re-run the local browser consent once.

1. Google Cloud Console → your project → **APIs & Services → Credentials**.
2. Click your **Desktop app** OAuth client → **Download JSON** (or "Reset client secret", then download).
3. Replace `C:\JARVIS\credentials\credentials.json` with the new file. Keep the filename exactly `credentials.json`.
4. Re-consent (browser window opens, you approve the Gmail scopes):
   ```powershell
   cd C:\JARVIS\backend
   .\.venv\Scripts\python scripts\gmail_auth.py --send
   ```
5. Restart JARVIS and confirm:
   ```powershell
   cd C:\JARVIS
   .\scripts\stop_prod.ps1
   .\scripts\start_prod.ps1
   Invoke-RestMethod http://127.0.0.1:8000/gmail/account
   ```
   Expected: `connected: True`, `can_send: True`.

Keep the same client if you like — it keeps working until you reset it. Never commit `credentials.json` or `token.json`; both are ignored by Git.

## Gmail autopilot behaviour
- Inbox scans are proposals (`fetch_emails`). Approve the proposal before JARVIS fetches.
- Draft replies are created with a pending send approval. Nothing is ever sent without your explicit approval of that exact message.
- A changed draft is refused by design (`draft changed since approval request`).


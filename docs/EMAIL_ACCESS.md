# Email Access (Gmail)

## What it does
Connects your Gmail inbox to JARVIS so recruiter emails, interview invites and job alerts land in the dashboard. JARVIS reads and classifies them, and it can prepare a reply for you to send. **You press send.** JARVIS never sends mail on its own, and even the send path requires an explicit approval of the exact message.

## One-time setup
1. In [Google Cloud Console](https://console.cloud.google.com/) create a project and enable the **Gmail API**.
2. Create an **OAuth 2.0 Desktop client** (Credentials → OAuth client ID → Desktop app).
3. Download the JSON and save it as `C:\JARVIS\credentials\credentials.json`.
4. Authorise JARVIS:
   ```powershell
   cd C:\JARVIS\backend
   .\.venv\Scripts\python scripts\gmail_auth.py
   ```
   A browser opens, you sign in and grant **read-only** access. The token is stored in `C:\JARVIS\credentials\token.json`.
5. Open **Email Access** in the dashboard - your address appears once connected.

Add `--send` to the command only if you ever want JARVIS to be able to send after approving the exact message. Without it, JARVIS can read and draft but never send.

## The Email Access page
- **Connection card** - shows the linked address, mailbox size and which scope is active (`read-only` vs `read + send`).
- **Fetch inbox** - pulls recent messages with a Gmail query (`newer_than:30d` by default) and classifies them as recruiter, interview, assessment, job_alert or other.
- **Inbox list** - filter by category, open a message to read the body.
- **Prepare reply** - creates a reply draft plus a pending approval record. You then get **Copy text** and **Open in your mail app** buttons so you can send it yourself from Gmail/Outlook.
- **Saved drafts** - every draft with its status (pending / approved / rejected / sent).

## Email categories
| Category | Trigger examples |
|---|---|
| `recruiter` | hiring, your application, resume review, talent acquisition |
| `interview` | interview, schedule, availability, technical round |
| `assessment` | assessment, coding test, HackerRank, OA link |
| `job_alert` | new job, jobs for you, recommended job |
| `other` | everything else |
| `spam` | lottery, crypto giveaway, wire transfer - kept but never surfaced as recruiter mail |

Company name, role and dates are extracted from the subject and body when they are written there.

## Endpoints
- `GET /gmail/status` - whether credentials and a token exist.
- `GET /gmail/account` - the connected address, mailbox totals and scopes.
- `GET /emails?category=&limit=` - stored messages.
- `GET /emails/{id}` - one message with its body.
- `POST /emails/fetch` - pull from Gmail and store.
- `POST /emails/draft` - prepare a reply (creates a pending approval).
- `GET /emails/drafts` - drafts with status.
- `POST /emails/approve-send` / `POST /emails/approve-reject` - approve or cancel a send (only meaningful with the `gmail.send` scope).

## Security notes
- The token never goes into the database, the logs or git - it lives only in `C:\JARVIS\credentials\token.json`.
- Sending requires the `gmail.send` scope *and* an approval of the exact message; if the draft changed after the approval request, the send is refused.
- Revoke access any time from your Google account security page.

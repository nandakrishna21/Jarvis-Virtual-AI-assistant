# JARVIS User Guide

## What it does
How to use your personal assistant day to day, from starting it to the everyday workflows.

## Why
JARVIS has many modules. This guide shows the fastest path through each one.

## Starting JARVIS

**Production mode (recommended)** - one process serves both the API and the dashboard:
```powershell
powershell -ExecutionPolicy Bypass -File C:\JARVIS\scripts\start_prod.ps1
```
Then open **http://127.0.0.1:8000**. Stop it with `C:\JARVIS\scripts\stop_prod.ps1`.

**On your phone** (same Wi-Fi): set `JARVIS_API_KEY` in `backend\.env`, then start with `-Lan` to get the phone URL:
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\set_api_key.py
powershell -ExecutionPolicy Bypass -File C:\JARVIS\scripts\start_prod.ps1 -Lan
```
Open the printed `http://192.168.x.x:8000` on the phone, unlock it with the key, and use the browser menu - **Install app / Add to Home Screen**. See `docs/MOBILE_APP.md`.

**Development mode** - open two PowerShell windows:
```powershell
# window 1 - backend
cd C:\JARVIS\backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
```powershell
# window 2 - dashboard
cd C:\JARVIS\frontend
npm run dev
```
Then open **http://127.0.0.1:5173**.

**Auto-start** - Settings page -> "Start JARVIS when I log in". JARVIS then starts with Windows using the production script.

## The dashboard
| Card | What it shows |
|---|---|
| Pending tasks / Overdue | your task load right now |
| Top job matches | the five highest scoring jobs |
| Study accuracy | percentage across practised topics |
| Today's tasks / Top job matches / Important emails / Hiring updates | quick view of each module |

The top bar always shows CPU %, RAM %, free RAM and whether Ollama is running.

## Talking to JARVIS
Open **AI Assistant** (or hold the Voice button). Write or say a request in plain English. The orchestrator picks the right agent:

| Say | You get |
|---|---|
| "Find Python Backend Developer jobs in India" | live job search, ranked, with links |
| "Show my pending tasks" | your task list with overdue flags |
| "Add task call the recruiter tomorrow" | an approval card - nothing happens until you approve |
| "Complete task 12" / "Delete task 12" | an approval card for that exact task |
| "Check my Gmail for recruiter emails" | recruiter and interview messages |
| "Show today's hiring news" | recent hiring announcements |
| "Start my SSC CGL preparation" | today's plan plus a lesson |
| "Tailor my resume for job 3" | an approval card to generate a tailored resume + cover letter |
| "Run daily report workflow" | an approval card to start the automation |
| "Schedule interview with Acme on 2026-11-20 at 10:00" | an approval card to create the interview + reminder |
| "Show pending approvals" | everything waiting on you |
| "Explain this Python error" | a mentor-style answer with code |
| "Summarise this file" | a bullet summary of a document |
| anything else | a general chat answer from the local model |

Replies take 20-60 seconds because the model runs on your CPU. That is normal.

**Approval cards:** any request that changes something shows an inline card with
the exact plan. Click **Approve & Execute** to run it or **Reject** to cancel.
You can also manage them later in the **Application Manager** page.

## Jobs workflow
1. **Job Discovery** page -> type a role and location -> **Search**.
2. Results show title, company, location, match %, matching skills and gaps.
3. Every result carries the original link. Open it to confirm the job is live - JARVIS marks scraped items `unverified` until you do.
4. **Prepare application** creates a tailored cover letter draft, answers, and a pending approval.
5. Go to **Approvals**, read the exact content, then Approve or Reject.
6. Even after approval JARVIS does **not** submit. You submit on the original site, so CAPTCHA, MFA and site rules stay in your hands.

**Resume matching:** upload your PDF on the **Resume Intelligence** page. JARVIS extracts skills, frameworks, databases and project keywords, then scores every job: skills 35%, experience 25%, responsibilities 20%, location 10%, education 10%. Each score shows its breakdown and the reason behind every component (for example "senior role - above your target level").

**Deciding on matches (Matched Jobs page):**
- Tick the checkboxes of several jobs, then **Approve selected** (they become shortlisted applications) or **Reject selected**.
- Use the thumbs up / thumbs down buttons on a single job to teach the ranking. Skills from jobs you like get boosted, skills from rejected jobs get penalised, and every match is re-scored right away. The learned weights are shown above the list.
- **Export CSV** downloads the ranked list with score, matching skills, gaps, status and URL for your own tracking.

## Document Studio (tailored resumes and cover letters)
1. Open **Document Studio** in the sidebar.
2. Pick your resume, then add **structured sections** (summary, experience, education, projects). This is what the documents are built from - only facts you enter.
3. Pick the target job (optional) and click **Generate**. You get a tailored resume and a cover letter.
4. Click **View** to read it or the download icon to save the text file.
5. Every generation is a new **version**, so nothing is overwritten.
6. You can also just ask JARVIS: *"tailor my resume for job 3"* and approve the card.

Full details in `docs/DOCUMENT_STUDIO.md`.

## Resume Generator (paste a JD, get a targeted resume)
1. Open **Resume Generator** in the sidebar.
2. Paste the whole job posting into the text box.
3. Optionally fill in the target role and company - JARVIS also reads them from the posting.
4. Press **Preview resume**. You get the rebuilt resume plus a **coverage analysis**: which JD skills are proven by your resume, and which requirements you still lack.
5. Press **Save version** to store it, then download the text file from the **Saved versions** tab.
6. The same thing works from chat: *"generate resume from this job description: <paste JD>"* - that path shows an approval card first.

Only your own facts are used. Requirements you cannot show evidence for are listed as gaps and never written into the resume. Details in `docs/RESUME_GENERATOR.md`.

## Email Access (read your inbox, send the mail yourself)
1. Open **Email Access** in the sidebar.
2. If Gmail is not connected, the page lists the exact setup steps. Short version: enable the Gmail API in Google Cloud, save the desktop-client JSON as `C:\JARVIS\credentials\credentials.json`, then run `cd C:\JARVIS\backend; .\.venv\Scripts\python scripts\gmail_auth.py`.
3. Once connected your address appears at the top. Press **Fetch inbox** to pull recent mail.
4. Open a message to read it, then press **Prepare reply**. JARVIS writes the reply and saves it as an approval item.
5. You send it: press **Copy text** and paste it into Gmail, or use **Open in your mail app**.

JARVIS never sends mail on its own, and sending is blocked unless you explicitly approve the exact message. Details in `docs/EMAIL_ACCESS.md`.

## Gmail workflow
1. One-time setup: follow `docs/GMAIL_SETUP.md`.
2. **Gmail** page -> check the connection badges -> **Fetch recent emails**.
3. Messages are sorted into recruiter, interview, assessment, job_alert, spam and other.
4. **Prepare reply draft** creates a draft plus an approval request.
5. On **Approvals** you see the recipient, subject and full body. Approve to send (needs the `gmail.send` scope) or Reject to cancel.
6. JARVIS never sends anything on its own.

## Exam mentor workflow
1. **Exam Mentor** -> pick an exam -> **Start today's plan**.
2. You get three topics (weakest first) and a lesson on the focus topic.
3. Click **Practise** for a question, answer it, and read the explanation.
4. Mastery is updated automatically; weak topics rise to the top of the **Weak topics** list.

## Tasks workflow
- Add a task with natural language: *"Study SQL at 7 PM"*, *"Call recruiter tomorrow"*, *"Submit assignment today at 9 PM"*.
- Categories: general, study, job, follow-up.
- **Complete** marks it done. **Delete** asks for confirmation first.
- **Tasks & Reminders** shows pending, due today, overdue and completed counts.

## Voice workflow
### Voice Agent (recommended on a phone)
1. Open **Voice Agent** and allow microphone access.
2. Press **Start talking**. Speak naturally - JARVIS transcribes, routes the request, and answers out loud.
3. After the answer it listens again, so you can say "show my top matches" and then "what are the gaps in the first one?" as one conversation.
4. Barge in by speaking while JARVIS is talking, and it stops immediately. Turn on "Only answer when I say JARVIS" to keep it listening without reacting to every word.
5. Every chat intent works here (jobs, tasks, Gmail, hiring news, study, approvals, resume generation). Actions that change data still ask for approval.

### Push-to-talk voice
1. Open **Voice Assistant** and allow microphone access.
2. Hold **Hold to talk**, speak, release.
3. The clip is transcribed locally (Whisper on your CPU), routed, and the answer is spoken back.
4. The microphone is only live while you hold the button. The red badge shows when it is active.

Speech never bypasses approvals.

## Developer assistant
Paste code or give a path, then **Analyze** (static checks: functions, imports, syntax errors, dangerous calls) or **Explain with AI** (a beginner-friendly walkthrough). The **Project snapshot** card summarises the backend.

## Files
Browse inside `C:\JARVIS` only. **Open** previews text, **Summarise** produces AI bullets. JARVIS never deletes, moves or overwrites your files.

## Automations (Settings)
Create a schedule (morning report, job discovery, Gmail review, study reminders) with a time, then enable it and **Resume all**. **Pause all** stops everything immediately. Each run is logged with its result.

The **Automation Center** page lists every workflow, shows whether n8n is connected, and gives you a **Run** button. Running a workflow still asks for approval first, and it falls back to JARVIS's own native execution when n8n is not running.

## AI provider and security (Settings)
- **AI Provider** shows which model is answering and lets you switch between Ollama (local, default), Gemini and OpenRouter. Providers without a key are shown as unavailable. If a provider fails, JARVIS falls back to Ollama automatically.
- **Security** shows whether the optional API-key guard is on. See `docs/APPROVAL_SECURITY.md`.

## Interviews
The **Interview Tracker** page stores company, role, date, time, mode and status. Upcoming interviews inside 24 hours automatically become reminder tasks (never duplicated). You can also create one by asking JARVIS.

## Analytics
The **Analytics** page charts jobs discovered, match scores, applications by status, interview counts, task load by category, automation runs and recent status history. Every number is computed from the database.

## Approvals page
Everything waiting for you, with the exact content and the recorded decision. Job approvals move an application to `Approved`; email approvals send the message; action proposals run their handler. Rejections cancel the action.

## System Monitor
CPU, RAM, available RAM, active model, loaded models, and an **Unload model** button that frees RAM immediately.

## Daily routine
| When | Do this |
|---|---|
| Morning | open the Dashboard, read the morning report, check the plan |
| During the day | ask for recruiter emails and new jobs |
| Evening | practise exam questions, complete today's tasks |
| Weekly | review Applications, update statuses, back up the database |

## Back up your data
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\backup.py create weekly
.\.venv\Scripts\python scripts\backup.py list
```
Or use `POST /system/backup` from the API. Restores keep a safety copy first.

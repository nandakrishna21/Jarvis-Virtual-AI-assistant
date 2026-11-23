import re

from app.services.llm import chat as ollama_chat
from app.services import proposals

INTENTS = [
    ("tasks", ["show my task", "my task", "pending task", "remind me", "add task", "to do list",
               "overdue", "productivity report", "what should i complete", "my schedule"]),
    ("gmail", ["gmail", "email", "emails", "recruiter mail", "inbox", "unread mail"]),
    ("news", ["hiring news", "hiring update", "company news", "news about hiring", "freshers hiring",
              "walk-in", "walk in", "hiring drive"]),
    ("study", ["start today", "preparation", "study plan", "prepare for", "ssc cgl", "ssc chsl",
               "rbi assistant", "ibps", "sbi exam", "quiz me", "mock test", "revision"]),
    ("developer", ["explain this", "debug this", "code review", "write a test", "architecture",
                   "create a postgresql", "fix this error", "explain this fastapi", "git command"]),
    ("files", ["summarise this file", "summarize this file", "analyse this file", "analyze this file",
               "read this pdf", "find file", "search my files", "compare document"]),
    ("automation", ["run workflow", "run the workflow", "automation", "run job discovery",
                    "daily report", "morning report", "generate today's report", "weekly report",
                    "follow up applications", "interview reminder"]),
    ("interview", ["schedule interview", "interview on", "add interview", "log interview",
                   "interview scheduled"]),
    ("approvals", ["pending approval", "show approval", "my approval", "what needs approval"]),
    ("documents", ["tailor my resume", "tailored resume", "generate cover letter",
                   "cover letter for", "tailor resume", "customise resume", "customize resume",
                   "resume for job", "document version"]),
    ("resume_generator", ["generate resume from jd", "resume from job description",
                          "create resume from jd", "build resume for this jd",
                          "resume generator", "resume from this description",
                          "generate resume from this job description"]),
    ("resume", ["analyze my resume", "analyse my resume", "my resume", "resume analysis",
                "upload resume", "update resume"]),
    ("report", ["how many applications", "this week", "weekly report", "statistics", "stats",
                "analytics", "show report"]),
]
JOB_VERBS = ["find", "search", "look for", "show me", "get me", "list", "give me", "show", "apply"]
JOB_NOUNS = ["job", "jobs", "vacancy", "vacancies", "opening", "openings", "role", "roles"]

EXAM_NAMES = ["ssc cgl", "ssc chsl", "rbi assistant", "ibps po", "ibps clerk", "sbi po", "appsc", "tspsc"]

ROLE_HINTS = ["python backend developer", "python developer", "django developer", "fastapi developer",
              "full stack python developer", "ai agent engineer", "generative ai developer",
              "ai automation engineer", "api integration engineer", "backend software engineer",
              "junior software engineer", "python", "backend", "software engineer", "developer"]

ROLE_DISPLAY = {
    "python backend developer": "Python Backend Developer",
    "python developer": "Python Developer",
    "django developer": "Django Developer",
    "fastapi developer": "FastAPI Developer",
    "full stack python developer": "Full Stack Python Developer",
    "ai agent engineer": "AI Agent Engineer",
    "generative ai developer": "Generative AI Developer",
    "ai automation engineer": "AI Automation Engineer",
    "api integration engineer": "API Integration Engineer",
    "backend software engineer": "Backend Software Engineer",
    "junior software engineer": "Junior Software Engineer",
    "python": "Python Developer",
    "backend": "Backend Developer",
    "software engineer": "Software Engineer",
    "developer": "Developer",
}

LOCATION_HINTS = ["india", "remote", "hybrid", "worldwide", "bangalore", "bengaluru", "hyderabad",
                  "pune", "mumbai", "chennai", "delhi", "noida", "gurugram", "kolkata"]

WORKFLOW_HINTS = {
    "job_discovery": ["job discovery", "discover jobs", "find jobs", "collect jobs", "job search"],
    "daily_report": ["daily report", "morning report", "today's report", "todays report", "summary report"],
    "application_follow_up": ["follow up", "follow-up", "followup applications"],
    "interview_reminders": ["interview reminder", "interview reminders"],
    "gmail_review": ["gmail review", "email review", "review gmail"],
}

ADD_TASK_PREFIXES = [
    "add a task", "add task", "create a task", "create task", "new task",
    "remind me to", "remind me", "set a reminder", "set reminder", "schedule a task",
    "i need to", "todo ", "to do ",
]

COMPLETE_PREFIXES = ["complete task", "mark task", "finish task", "mark as done", "complete the task"]
DELETE_PREFIXES = ["delete task", "remove task", "delete the task", "remove the task"]


def detect_intent(message: str) -> str:
    low = message.lower().strip()
    if _is_task_action(low):
        return "task_action"
    if _is_application_action(low):
        return "application"
    if _is_open_site(low):
        return "open_site"
    if _is_weather(low):
        return "weather"
    for name, keys in INTENTS:
        if any(k in low for k in keys):
            return name
    if any(e in low for e in EXAM_NAMES):
        return "study"
    if _is_job_search(low):
        return "jobs"
    return "chat"


OPEN_VERBS = ["open", "launch", "browse", "go to", "goto", "play", "take me to", "navigate to", "visit", "search on", "search youtube"]
WEATHER_KEYS = ["weather", "temperature", "forecast", "humidity", "how hot", "is it raining", "rain today", "wind speed"]


def _is_open_site(low: str) -> bool:
    from app.services import sites

    if not any(v in low for v in OPEN_VERBS):
        return False
    return sites.extract(low) is not None


def _is_weather(low: str) -> bool:
    return any(k in low for k in WEATHER_KEYS)


def _extract_city(message: str) -> str:
    low = message.lower()
    patterns = [
        r"weather\s+(?:in|at|for)\s+([a-z0-9\s,]+)",
        r"(?:temperature|forecast)\s+(?:in|at|for)\s+([a-z0-9\s,]+)",
    ]
    for p in patterns:
        m = re.search(p, low)
        if m:
            city = m.group(1).strip(" .?!,")
            for stop in ["today", "now", "tomorrow", "please", "right now", "currently"]:
                city = re.sub(rf"\b{stop}\b", "", city).strip(" .?!,")
            if city:
                return city.title()
    return "Hyderabad"


def _is_job_search(low: str) -> bool:
    if "application" in low or "resume" in low:
        return False
    has_verb = any(re.search(rf"\b{re.escape(v)}\b", low) for v in JOB_VERBS)
    has_noun = any(re.search(rf"\b{re.escape(n)}\b", low) for n in JOB_NOUNS)
    return has_verb and has_noun


def _is_task_action(low: str) -> bool:
    if any(p in low for p in DELETE_PREFIXES):
        return True
    if any(p in low for p in COMPLETE_PREFIXES):
        return True
    if any(low.startswith(p) for p in ADD_TASK_PREFIXES):
        return True
    if re.search(r"\b(add|create)\s+(a\s+)?(new\s+)?task\b", low):
        return True
    if re.search(r"\b(complete|finish|delete|remove)\s+(the\s+)?task\b", low):
        return True
    return False


def _is_application_action(low: str) -> bool:
    if "application" not in low:
        return False
    verbs = ["prepare", "apply", "draft", "create", "start", "submit"]
    return any(v in low for v in verbs)


def _extract_job_params(message: str) -> tuple[str, str]:
    low = message.lower()
    role = "Python Backend Developer"
    for hint in ROLE_HINTS:
        if hint in low:
            role = ROLE_DISPLAY.get(hint, hint.title())
            break
    location = "India"
    for hint in LOCATION_HINTS:
        if hint in low:
            location = hint.capitalize()
            break
    return role, location


def _extract_task_payload(message: str) -> dict:
    low = message.lower().strip()
    original = message.strip()

    for prefix in DELETE_PREFIXES:
        if low.startswith(prefix):
            task_id = _first_int(original)
            return {"mode": "delete", "task_id": task_id, "title": original}
    for prefix in COMPLETE_PREFIXES:
        if low.startswith(prefix):
            task_id = _first_int(original)
            return {"mode": "complete", "task_id": task_id, "title": original}

    title = original
    for prefix in ADD_TASK_PREFIXES:
        if low.startswith(prefix):
            title = original[len(prefix):].strip(" :,-")
            break
    title = title or original
    category = "general"
    if any(k in low for k in ("study", "revise", "practice", "exam", "quiz")):
        category = "study"
    elif any(k in low for k in ("job", "apply", "application", "resume", "interview")):
        category = "job"
    elif any(k in low for k in ("call", "follow up", "follow-up", "email", "reply")):
        category = "follow-up"
    return {"mode": "create", "title": title, "category": category, "raw": original}


def _first_int(text: str) -> int | None:
    m = re.search(r"\b(\d+)\b", text)
    return int(m.group(1)) if m else None


def _extract_workflow(message: str) -> str | None:
    low = message.lower()
    for name, keys in WORKFLOW_HINTS.items():
        if any(k in low for k in keys):
            return name
    return None


def _extract_job_id(message: str) -> int | None:
    m = re.search(r"\bjob\s*#?\s*(\d+)\b", message.lower())
    return int(m.group(1)) if m else None


def _extract_application_id(message: str) -> int | None:
    m = re.search(r"\bapplication\s*#?\s*(\d+)\b", message.lower())
    return int(m.group(1)) if m else None


def _handle_open_site(message: str) -> dict:
    """Return a link for the user to click. JARVIS never navigates on its own."""
    from app.services import sites

    target = sites.extract(message)
    if not target:
        return {
            "ok": False,
            "intent": "open_site",
            "error": "I did not recognise that site. Try: open YouTube, open Google, open LinkedIn.",
        }
    label = target["site"].title()
    query = f" for '{target['query']}'" if target.get("query") else ""
    return {
        "ok": True,
        "intent": "open_site",
        "response": f"Ready to open {label}{query}. Click the button below to open it - I will not open anything without your click.",
        "open_url": target["url"],
        "open_label": f"Open {label}",
        "requires_click": True,
    }


async def _handle_weather(message: str) -> dict:
    from app.services import weather as weather_service

    city = _extract_city(message)
    try:
        data = await weather_service.current(city)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "intent": "weather", "error": f"Weather lookup failed: {exc}"}
    if not data.get("ok"):
        return {"ok": False, "intent": "weather", "error": data.get("error", "Weather unavailable.")}
    return {
        "ok": True,
        "intent": "weather",
        "response": weather_service.summarize(data),
        "weather": data,
    }


async def handle(message: str, db=None) -> dict:
    intent = detect_intent(message)
    try:
        if intent == "task_action":
            return await _handle_task_action(message, db)
        if intent == "application":
            return await _handle_application_action(message, db)
        if intent == "open_site":
            return _handle_open_site(message)
        if intent == "weather":
            return await _handle_weather(message)
        if intent == "automation":
            return await _handle_automation_action(message, db)
        if intent == "interview":
            return await _handle_interview_action(message, db)
        if intent == "approvals":
            return _handle_approvals_query(db)
        if intent == "resume":
            return _handle_resume_query(db)
        if intent == "documents":
            return await _handle_document_action(message, db)
        if intent == "resume_generator":
            return await _handle_resume_generator(message, db)
        if intent == "report":
            return await _handle_report(message, db)
        if intent == "jobs":
            from app.agents.job_discovery.service import search_and_save
            from app.database.session import SessionLocal
            from app.database.models import ResumeProfile
            session = db or SessionLocal()
            close = db is None
            try:
                rp = session.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
                skills = rp.extracted_skills.split(",") if rp and rp.extracted_skills else []
            finally:
                if close:
                    session.close()
            role, location = _extract_job_params(message)
            jobs = await search_and_save(role, location, skills)
            lines = [f"Found {len(jobs)} job(s) for '{role}' ({location})."]
            for j in jobs:
                lines.append(
                    f"- {j['title']} at {j.get('company') or 'company not published'} "
                    f"(match {j['score']}%, {j.get('location') or 'location not published'})\n"
                    f"  {j['url']}\n"
                    f"  matching: {', '.join(j['matching_skills']) or 'none extracted'} | "
                    f"gaps: {', '.join(j['missing_skills']) or 'none'}"
                )
            return {"ok": True, "intent": intent, "response": "\n".join(lines), "jobs": jobs}

        if intent == "tasks":
            from app.agents.task_manager.service import list_tasks, productivity_report
            report = productivity_report()
            tasks = list_tasks(status="pending")
            pending = report.get("pending", 0)
            due_today = report.get("due_today", 0)
            overdue = report.get("overdue", 0)
            parts = [f"{pending} pending task{'s' if pending != 1 else ''}"]
            if due_today: parts.append(f"{due_today} due today")
            if overdue: parts.append(f"{overdue} overdue")
            summary = "Pending: " + ", ".join(parts) + "."
            if pending == 0:
                summary = "Pending: 0 tasks. You're all clear right now."
            lines = [summary]
            for t in tasks[:8]:
                due = f" due {t['due_date']}" if t.get("due_date") else ""
                if t.get("due_time"): due += f" {t['due_time']}"
                flag = " [OVERDUE]" if t.get("overdue") else ""
                lines.append(f"- {t['title']} ({t.get('category','task')}){due}{flag}")
            return {"ok": True, "intent": intent, "response": "\n".join(lines), "tasks": tasks[:15], "report": report}

        if intent == "gmail":
            from app.agents.gmail.service import fetch_and_store
            try:
                emails = await fetch_and_store(20, "newer_than:14d")
            except Exception as e:
                return {"ok": False, "intent": intent, "error": str(e),
                        "hint": "Gmail is not authenticated yet. Run scripts/gmail_auth.py (see docs/GMAIL_SETUP.md)."}
            recruiter = [e for e in emails if e.get("category") in ("recruiter", "interview", "assessment")]
            lines = [f"Fetched {len(emails)} messages. Recruiter/interview/assessment: {len(recruiter)}."]
            for e in recruiter[:10]:
                lines.append(f"- {e.get('category')}: {e.get('subject')} | {e.get('sender')} | {e.get('company') or ''} {e.get('job_role') or ''}")
            return {"ok": True, "intent": intent, "response": "\n".join(lines), "emails": emails}

        if intent == "news":
            from app.agents.hiring_news.service import fetch_and_store
            result = await fetch_and_store()
            from app.database.session import SessionLocal
            from app.database.models import HiringNews
            session = db or SessionLocal()
            close = db is None
            try:
                rows = session.query(HiringNews).filter(HiringNews.is_current.is_(True)).order_by(HiringNews.relevance.desc()).limit(10).all()
                items = [{"title": r.title, "company": r.company, "role": r.role, "location": r.location,
                          "posting_date": r.posting_date, "url": r.application_url, "relevance": r.relevance} for r in rows]
            finally:
                if close:
                    session.close()
            lines = [f"Hiring news: inserted {result['inserted']}, updated {result['updated']}."]
            for i in items:
                lines.append(f"- {i['title']} ({i['company'] or 'company n/a'}) - {i['role'] or 'role n/a'} - {i['posting_date'] or 'date n/a'}\n  {i['url'] or ''}")
            return {"ok": True, "intent": intent, "response": "\n".join(lines), "news": items}

        if intent == "study":
            from app.agents.government_exam.service import get_or_create_plan
            from app.agents.government_exam.syllabus import exam_names
            low = message.lower()
            exam = next((e for e in exam_names() if e.lower() in low), "SSC CGL")
            plan = get_or_create_plan(exam)
            topic = plan[0]["topic"] if plan else None
            teaching = await ollama_chat(
                f"Teach this {exam} topic briefly to a beginner: {topic}. 3 short bullets, then one practice question. "
                "Do not invent official exam dates or notifications.")
            lines = [f"{exam} plan today: " + ", ".join(p['topic'] for p in plan)]
            if teaching.get("ok"):
                lines.append(teaching.get("response", ""))
            else:
                lines.append(f"Teaching unavailable: {teaching.get('error')}")
            return {"ok": True, "intent": intent, "response": "\n".join(lines), "exam": exam,
                    "plan": plan, "teaching": teaching}

        if intent == "developer":
            res = await ollama_chat(
                "You are a senior Python backend mentor. Answer concisely with working code, "
                "the exact commands to run, and the common errors. Never suggest destructive commands "
                "without an explicit warning.\n\n" + message)
            return {"ok": res.get("ok", False), "intent": intent,
                    "response": res.get("response") or res.get("error", ""), "hint": res.get("hint")}

        if intent == "files":
            from app.agents.file_manager.service import list_files
            listing = list_files("")
            lines = [f"Files under C:\\JARVIS: {listing.get('count', 0)}"]
            for f in listing.get("files", [])[:30]:
                lines.append(f"- {f['path']}")
            return {"ok": True, "intent": intent, "response": "\n".join(lines)}
    except Exception as e:
        return {"ok": False, "intent": intent, "error": str(e)}

    res = await ollama_chat(message)
    return {"ok": res.get("ok", False), "intent": "chat",
            "response": res.get("response") or "",
            "error": res.get("error"),
            "hint": res.get("hint"), "elapsed": res.get("elapsed"),
            "provider": res.get("provider"),
            "model": res.get("model"),
            "fallback_from": res.get("fallback_from"),
            "tokens_per_second": res.get("tokens_per_second")}


# ---------- approval-first actions ----------

def _session(db):
    from app.database.session import SessionLocal

    if db is not None:
        return db, False
    return SessionLocal(), True


async def _handle_task_action(message: str, db) -> dict:
    payload = _extract_task_payload(message)
    mode = payload["mode"]
    session, close = _session(db)
    try:
        if mode == "create":
            title = payload["title"]
            from app.agents.task_manager.service import parse_when

            when = parse_when(title)
            proposal = proposals.create_proposal(
                session,
                action_type="create_task",
                title=f"Create task: {title}",
                reason=f'You asked: "{message.strip()}"',
                plan=[
                    f"Add a task titled '{title}'",
                    f"Category: {payload['category']}",
                    f"Due date: {when['due_date'] or 'not set'}",
                    f"Due time: {when['due_time'] or 'not set'}",
                ],
                payload={"title": title, "category": payload["category"],
                         "due_date": when["due_date"], "due_time": when["due_time"]},
            )
            return _proposal_response(proposal, intent="task_action")

        if mode == "complete":
            task_id = payload["task_id"]
            if not task_id:
                return {"ok": False, "intent": "task_action",
                        "error": "Tell me which task number to complete, for example 'complete task 12'."}
            title = _task_title(session, task_id)
            proposal = proposals.create_proposal(
                session,
                action_type="complete_task",
                title=f"Mark task #{task_id} as completed",
                reason=f'You asked: "{message.strip()}"',
                plan=[f"Mark '{title}' as completed", "Record the completion time"],
                payload={"task_id": task_id},
            )
            return _proposal_response(proposal, intent="task_action")

        task_id = payload["task_id"]
        if not task_id:
            return {"ok": False, "intent": "task_action",
                    "error": "Tell me which task number to delete, for example 'delete task 12'."}
        title = _task_title(session, task_id)
        proposal = proposals.create_proposal(
            session,
            action_type="delete_task",
            title=f"Delete task #{task_id}",
            reason=f'You asked: "{message.strip()}"',
            plan=[f"Permanently delete '{title}'", "Its reminders are removed too"],
            payload={"task_id": task_id},
        )
        return _proposal_response(proposal, intent="task_action")
    finally:
        if close:
            session.close()


async def _handle_application_action(message: str, db) -> dict:
    session, close = _session(db)
    try:
        from app.database.models import Application, Job

        job_id = _extract_job_id(message)
        app_id = _extract_application_id(message)
        if app_id:
            row = session.get(Application, app_id)
            if not row:
                return {"ok": False, "intent": "application", "error": f"application {app_id} not found"}
            job_id = row.job_id
        if not job_id:
            row = session.query(Application).order_by(Application.id.desc()).first()
            job_id = row.job_id if row else None
        if not job_id:
            return {"ok": False, "intent": "application",
                    "error": "No application found yet. Search for jobs first, then ask me to prepare one."}
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "intent": "application", "error": f"job {job_id} not found"}
        proposal = proposals.create_proposal(
            session,
            action_type="prepare_application",
            title=f"Prepare application: {job.title} at {job.company or 'company not published'}",
            reason=f'You asked: "{message.strip()}"',
            plan=[
                f"Build a tailored cover letter for '{job.title}'",
                "Draft the application answers from your verified resume",
                "Store the draft and ask you to review it",
                "Do not submit anything to the employer",
            ],
            payload={"job_id": job_id},
        )
        return _proposal_response(proposal, intent="application")
    finally:
        if close:
            session.close()


async def _handle_automation_action(message: str, db) -> dict:
    session, close = _session(db)
    try:
        from app.agents.automation import catalog

        name = _extract_workflow(message)
        if not name:
            options = ", ".join(w["name"] for w in catalog.WORKFLOWS)
            return {"ok": False, "intent": "automation",
                    "error": f"Which workflow should I run? Available: {options}."}
        wf = catalog.get(name)
        proposal = proposals.create_proposal(
            session,
            action_type="run_workflow",
            title=f"Run automation: {wf['title']}",
            reason=f'You asked: "{message.strip()}"',
            plan=wf["steps"],
            payload={"workflow": name},
        )
        return _proposal_response(proposal, intent="automation")
    finally:
        if close:
            session.close()


async def _handle_interview_action(message: str, db) -> dict:
    session, close = _session(db)
    try:
        company = _extract_company(message)
        if not company:
            return {"ok": False, "intent": "interview",
                    "error": "Which company is the interview with? For example 'schedule interview with Acme on 2026-11-20 at 10:00'."}
        interview_date = _extract_date(message)
        interview_time = _extract_time(message)
        proposal = proposals.create_proposal(
            session,
            action_type="create_interview",
            title=f"Schedule interview with {company}",
            reason=f'You asked: "{message.strip()}"',
            plan=[
                f"Company: {company}",
                f"Date: {interview_date or 'not set'}",
                f"Time: {interview_time or 'not set'}",
                "Create a reminder task before the interview",
            ],
            payload={"company": company, "interview_date": interview_date,
                     "interview_time": interview_time},
        )
        return _proposal_response(proposal, intent="interview")
    finally:
        if close:
            session.close()


def _handle_approvals_query(db) -> dict:
    from app.database.models import Approval, EmailApproval

    session, close = _session(db)
    try:
        action_rows = proposals.list_proposals(session, "pending")
        legacy = session.query(Approval).filter(Approval.status == "pending").all()
        email_rows = session.query(EmailApproval).filter(EmailApproval.status == "pending").all()
        lines = [f"Pending action proposals: {len(action_rows)}",
                 f"Pending application approvals: {len(legacy)}",
                 f"Pending email approvals: {len(email_rows)}"]
        for p in action_rows[:10]:
            lines.append(f"- #{p['id']} {p['title']} (source: {p['source']})")
        return {"ok": True, "intent": "approvals", "response": "\n".join(lines),
                "proposals": action_rows, "count": len(action_rows) + len(legacy) + len(email_rows)}
    finally:
        if close:
            session.close()


def _handle_resume_query(db) -> dict:
    from app.database.models import ResumeProfile
    from app.services import profile as profile_service

    session, close = _session(db)
    try:
        rp = session.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        prefs = profile_service.get_preferences(session)
        if not rp:
            return {"ok": False, "intent": "resume",
                    "error": "No resume uploaded yet. Open Resume Intelligence and upload your PDF or DOCX."}
        skills = [s.strip() for s in (rp.extracted_skills or "").split(",") if s.strip()]
        lines = [f"Active resume: {rp.file_path}",
                 f"Extracted skills ({len(skills)}): {', '.join(skills) or 'none detected'}",
                 f"Target location: {prefs.get('location')}"]
        return {"ok": True, "intent": "resume", "response": "\n".join(lines),
                "resume": {"id": rp.id, "file_path": rp.file_path, "skills": skills,
                           "created_at": rp.created_at.isoformat() if rp.created_at else None},
                "preferences": prefs}
    finally:
        if close:
            session.close()


async def _handle_report(message: str, db) -> dict:
    from app.agents.task_manager.service import productivity_report
    from app.database.models import Application, Interview, Job, JobMatch

    session, close = _session(db)
    try:
        report = productivity_report()
        jobs = session.query(Job).count()
        matches = session.query(JobMatch).count()
        high = session.query(JobMatch).filter(JobMatch.score >= 80).count()
        apps = session.query(Application).count()
        submitted = session.query(Application).filter(
            Application.status.in_(["Applied", "Interview", "Offer"])).count()
        interviews = session.query(Interview).filter(Interview.status == "scheduled").count()
        pending = proposals.pending_count(session)
        lines = [
            "Job-search report",
            f"- Jobs discovered: {jobs}",
            f"- Matches scored: {matches} ({high} above 80%)",
            f"- Applications: {apps} ({submitted} submitted)",
            f"- Interviews scheduled: {interviews}",
            f"- Pending approvals: {pending}",
            f"- Tasks: {report['pending']} pending, {report['overdue']} overdue",
        ]
        return {"ok": True, "intent": "report", "response": "\n".join(lines), "report": report}
    finally:
        if close:
            session.close()


def _task_title(session, task_id: int) -> str:
    from app.database.models import Task

    row = session.get(Task, task_id)
    return row.title if row else f"task {task_id}"


async def _handle_document_action(message: str, db) -> dict:
    session, close = _session(db)
    try:
        from app.database.models import Job, ResumeProfile

        rp = session.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            return {"ok": False, "intent": "documents",
                    "error": "No resume uploaded yet. Open Resume Intelligence and upload your file first."}

        job_id = _extract_job_id(message)
        job = session.get(Job, job_id) if job_id else None
        if job_id and not job:
            return {"ok": False, "intent": "documents", "error": f"job {job_id} not found"}

        types = ["resume"]
        low = message.lower()
        if "cover letter" in low or "cover-letter" in low:
            types.append("cover_letter")
        elif "resume" not in low:
            types.append("cover_letter")

        if job:
            title = f"Tailored documents for {job.title} at {job.company or 'company not published'}"
        else:
            title = "Generate tailored resume and cover letter"

        proposal = proposals.create_proposal(
            session,
            action_type="generate_documents",
            title=title,
            reason=f'You asked: "{message.strip()}"',
            plan=[
                "Read your structured resume sections and extracted skills",
                "Reorder skills to match the job requirements first",
                f"Build {', '.join(types)} from your verified details only",
                "Store them as a new version you can download and review",
                "Do not submit anything to the employer",
            ],
            payload={"resume_id": rp.id, "job_id": job_id, "types": types},
        )
        return _proposal_response(proposal, intent="documents")
    finally:
        if close:
            session.close()


def _extract_jd(message: str) -> str:
    """Pull the job description out of a chat message."""
    text = (message or "").strip()
    triggers = [
        "generate resume from this job description",
        "generate resume from jd",
        "create resume from jd",
        "build resume for this jd",
        "resume from this description",
        "resume generator",
    ]
    low = text.lower()
    for trigger in triggers:
        idx = low.find(trigger)
        if idx != -1:
            return text[idx + len(trigger):].strip(" :-\n\t")
    marker = re.search(r"(?:job description|job posting|description)\s*[:\-]\s*(.+)", text, re.I | re.S)
    if marker:
        return marker.group(1).strip()
    return text


async def _handle_resume_generator(message: str, db) -> dict:
    session, close = _session(db)
    try:
        from app.database.models import ResumeProfile

        rp = session.query(ResumeProfile).filter(ResumeProfile.is_active.is_(True)).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            rp = session.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            return {"ok": False, "intent": "resume_generator",
                    "error": "No resume uploaded yet. Open Resume Intelligence and upload your file first."}

        jd = _extract_jd(message)
        if len(jd) < 40:
            return {"ok": False, "intent": "resume_generator",
                    "error": "Paste the full job description after your request (or use the Resume Generator page)."}

        proposal = proposals.create_proposal(
            session,
            action_type="generate_resume_from_jd",
            title="Generate a targeted resume from this job description",
            reason=f'You asked: "{message.strip()[:120]}"',
            plan=[
                "Read your uploaded resume text, skills and structured sections",
                "Parse the job description for title, company and required skills",
                "Reorder your skills and bullets around those requirements",
                "List any requirement you cannot show evidence for as a gap, not as a claim",
                "Store the result as a new version you can download and review",
                "Do not submit anything to the employer",
            ],
            payload={"resume_id": rp.id, "jd": jd[:12000]},
        )
        return _proposal_response(proposal, intent="resume_generator")
    finally:
        if close:
            session.close()


def _extract_company(message: str) -> str | None:
    m = re.search(r"(?:with|at|for)\s+([A-Za-z0-9&.\- ]{2,40}?)(?:\s+on\b|\s+at\b|$)", message, re.IGNORECASE)
    if m:
        return m.group(1).strip(" .,-")
    m = re.search(r"interview\s+with\s+([A-Za-z0-9&.\- ]{2,40})", message, re.IGNORECASE)
    return m.group(1).strip(" .,-") if m else None


def _extract_date(message: str) -> str | None:
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", message)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", message)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    low = message.lower()
    if "tomorrow" in low:
        from datetime import date, timedelta

        return (date.today() + timedelta(days=1)).isoformat()
    if "today" in low:
        from datetime import date

        return date.today().isoformat()
    return None


def _extract_time(message: str) -> str | None:
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", message)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", message, re.IGNORECASE)
    if m:
        hour = int(m.group(1)) % 12
        if m.group(2).lower() == "pm":
            hour += 12
        return f"{hour:02d}:00"
    return None


def _proposal_response(proposal: dict, intent: str) -> dict:
    return {
        "ok": True,
        "intent": intent,
        "response": (
            f"I need your approval before I do this.\n\n{proposal['title']}\n\n"
            + "\n".join(f"{i}. {step}" for i, step in enumerate(proposal.get("plan", []), 1))
            + "\n\nReview it on the Approvals panel and choose Approve or Reject."
        ),
        "requires_approval": True,
        "proposal": proposal,
    }

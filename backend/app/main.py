from fastapi import FastAPI, Depends, File, UploadFile, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.orm import Session
import psutil, os
from pathlib import Path
from app.config import settings
from app.services.ollama import health as ollama_health, running_models, unload_model
from app.services.llm import chat as ollama_chat
from app.orchestrator.router import handle
from app.database.session import get_db
from app.database.models import Job, JobMatch, ResumeProfile, Application, Approval, Email, EmailDraft, EmailApproval
from app.agents.job_discovery import resume as resume_module
from app.agents.job_discovery.service import search_and_save
from app.agents.job_application import service as app_service
from app.agents.gmail import service as gmail_service
from app.integrations import gmail_client
from app.database.models import HiringNews
from app.agents.hiring_news import service as news_service
from app.database.models import StudyPlan, StudyTopic, QuizResult
from app.agents.government_exam import service as exam_service
from app.agents.government_exam.syllabus import exam_names, topics_for
from app.database.models import Task, Reminder, Schedule, AgentRun
from app.agents.task_manager import service as task_service
from app.agents.developer import service as dev_service
from app.agents.file_manager import service as file_service
from app.scheduler import scheduler
from app.agents.voice import service as voice_service
from app.services import startup as startup_service
from app.services import backup as backup_service
from app.services import auth as auth_service
from app.services import documents as documents_service
from app.services import llm as llm_service
from app.services import job_actions as job_actions_service
from app.agents.job_discovery import feedback as job_feedback_service
from app.agents.job_discovery.service import search_and_save
from app.agents.job_discovery import feedback as job_feedback_service
from app.agents.job_discovery.service import rescore_stored
from app.utils.logging_setup import get_logger
import json
from app.api import actions as actions_api
from app.api import analytics as analytics_api
from app.api import assistant as assistant_api
from app.api import automation as automation_api
from app.api import documents as documents_api
from app.api import interviews as interviews_api
from app.api import notifications as notifications_api
from app.api import profile as profile_api
from app.api import resumes as resumes_api
from app.api import resume_generator as resume_generator_api

logger = get_logger("jarvis.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    llm_service.load_persisted_provider()
    logger.info("JARVIS backend started (llm provider: %s)", settings.llm_provider)
    yield
    scheduler.stop()
    logger.info("JARVIS backend stopped")

app = FastAPI(title="JARVIS", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def api_prefix_stripper(request, call_next):
    """Serve the built SPA and the API from one origin in production.

    The frontend always calls `/api/...`. In development Vite strips that
    prefix; here the same rewrite happens inside the app so one built bundle
    works in both modes.
    """
    path = request.scope.get("path", "")
    if path.startswith("/api/"):
        request.scope["path"] = path[4:]
        raw = request.scope.get("raw_path")
        if raw and raw.startswith(b"/api/"):
            request.scope["raw_path"] = raw[4:]
        request.scope["jarvis_api_path"] = True
    return await call_next(request)


@app.middleware("http")
async def api_key_guard(request, call_next):
    """Require the local API key for mutating requests when one is configured.

    In LAN mode the server is reachable from other devices, so every API call
    (reads included) needs the key. The app shell and static files stay open
    so the phone can load the unlock screen first.
    """
    lan = bool(getattr(settings, "jarvis_lan_mode", False))
    path = request.scope.get("path", "")
    is_api = path.startswith("/api/") or path.startswith("/api")
    mutating = request.method in ("POST", "PUT", "PATCH", "DELETE")
    if auth_service.enabled() and (mutating or (lan and is_api)):
        provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if not auth_service.check(provided):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={
                    "error": "api key required",
                    "hint": "Send the JARVIS_API_KEY value in the X-API-Key header.",
                },
            )
    if lan and not auth_service.enabled():
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={
                "error": "LAN mode needs an API key",
                "hint": "Set JARVIS_API_KEY in backend\\.env, then restart JARVIS.",
            },
        )
    return await call_next(request)


app.include_router(actions_api.router)
app.include_router(analytics_api.router)
app.include_router(assistant_api.router)
app.include_router(automation_api.router)
app.include_router(documents_api.router)
app.include_router(interviews_api.router)
app.include_router(notifications_api.router)
app.include_router(profile_api.router)
app.include_router(resumes_api.router)
app.include_router(resume_generator_api.router)

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}

@app.get("/system/status")
async def status():
    vm = psutil.virtual_memory()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_percent": vm.percent,
        "ram_free_gb": round(vm.available / 1024**3, 2),
        "ollama": await ollama_health(),
        "model": settings.ollama_model,
        "loaded_models": await running_models(),
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    return await handle(req.message)

@app.get("/system/metrics")
async def metrics():
    return await status()

@app.get("/system/auth")
async def system_auth():
    status = auth_service.status()
    status["lan_mode"] = bool(getattr(settings, "jarvis_lan_mode", False))
    status["lan_note"] = (
        "LAN mode is on: every API call needs the API key."
        if status["lan_mode"]
        else "Local-only mode: the server is not reachable from other devices."
    )
    return status

@app.get("/system/llm")
async def system_llm():
    return llm_service.provider_status()

class LlmProviderReq(BaseModel):
    provider: str

@app.put("/system/llm")
async def system_llm_set(req: LlmProviderReq):
    return llm_service.set_provider(req.provider)

@app.post("/system/unload-model")
async def unload():
    return await unload_model()

class JobSearch(BaseModel):
    query: str = "Python Backend Developer"
    location: str = "India (Remote acceptable)"

@app.post("/jobs/search")
async def jobs_search(req: JobSearch, db: Session = Depends(get_db)):
    rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
    skills = rp.extracted_skills.split(",") if rp and rp.extracted_skills else []
    return await search_and_save(req.query, req.location, skills)

@app.get("/jobs")
async def jobs_list(db: Session = Depends(get_db)):
    rows = db.query(Job).limit(50).all()
    return [{"id": r.id, "title": r.title, "company": r.company, "location": r.location,
             "url": r.url, "source": r.source, "verified": r.verified} for r in rows]

@app.get("/jobs/top-matches")
async def top_matches(db: Session = Depends(get_db)):
    rows = db.query(JobMatch).order_by(JobMatch.score.desc()).limit(5).all()
    out = []
    for m in rows:
        j = db.get(Job, m.job_id)
        if j:
            out.append({"job_id": j.id, "title": j.title, "company": j.company, "url": j.url,
                        "score": m.score, "matching": m.matching_skills, "missing": m.missing_skills})
    return out

@app.get("/jobs/matched")
async def jobs_matched(min_score: float = 0, limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(JobMatch).filter(JobMatch.score >= min_score).order_by(JobMatch.score.desc()).limit(min(limit, 100)).all()
    out = []
    for m in rows:
        j = db.get(Job, m.job_id)
        if j:
            app_row = db.query(Application).filter(Application.job_id == j.id).order_by(Application.id.desc()).first()
            out.append({
                "job_id": j.id, "title": j.title, "company": j.company, "url": j.url,
                "location": j.location, "score": m.score, "matching": m.matching_skills,
                "missing": m.missing_skills, "source": j.source, "seniority": j.seniority,
                "salary": j.salary, "feedback": j.feedback,
                "status": app_row.status if app_row else None,
                "components": json.loads(m.components) if m.components else {},
                "notes": json.loads(m.notes) if m.notes else {},
            })
    return out

@app.get("/matching/results")
async def matching_results(min_score: float = 0, limit: int = 50, db: Session = Depends(get_db)):
    return await jobs_matched(min_score, limit, db)

@app.post("/jobs/collect")
async def jobs_collect(req: JobSearch, db: Session = Depends(get_db)):
    """Run discovery through the approval flow instead of acting immediately."""
    from app.services import proposals
    proposal = proposals.create_proposal(
        db,
        action_type="fetch_jobs",
        title=f"Collect jobs for '{req.query}' in {req.location}",
        reason="Job collection was requested from the API.",
        plan=[
            f"Search '{req.query}' in {req.location}",
            "Normalise and deduplicate the results",
            "Score every job against your active resume",
            "Save the matches for ranking",
        ],
        payload={"query": req.query, "location": req.location},
    )
    return {"requires_approval": True, "proposal": proposal}

@app.post("/jobs/match-resume")
async def match_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    os.makedirs("C:/JARVIS/data/resumes", exist_ok=True)
    path = f"C:/JARVIS/data/resumes/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    text = resume_module.extract_text_from_pdf(path)
    skills = resume_module.extract_skills(text)
    rp = ResumeProfile(file_path=path, raw_text=text[:5000], extracted_skills=",".join(skills))
    db.add(rp)
    db.commit()
    return {"skills": skills, "text_len": len(text)}


@app.get("/jobs/feedback/weights")
async def job_feedback_weights(db: Session = Depends(get_db)):
    return job_feedback_service.get_weights(db)


class BulkJobActionReq(BaseModel):
    job_ids: list[int]
    action: str


@app.post("/jobs/bulk-action")
async def jobs_bulk_action(req: BulkJobActionReq, db: Session = Depends(get_db)):
    """Approve or reject several jobs at once."""
    try:
        result = job_actions_service.bulk_decision(db, req.job_ids, req.action)
    except ValueError as e:
        return {"error": str(e)}
    job_feedback_service.learn_weights(db)
    rescore_stored(db=db)
    return result


@app.get("/jobs/export.csv")
async def jobs_export_csv(min_score: float = 0, limit: int = 500, db: Session = Depends(get_db)):
    csv_text = job_actions_service.export_csv(db, min_score=min_score, limit=limit)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="jarvis-job-matches.csv"'},
    )


@app.get("/jobs/{job_id}")
async def job_detail(job_id: int, db: Session = Depends(get_db)):
    r = db.get(Job, job_id)
    if not r:
        return {"error": "not found"}
    m = db.query(JobMatch).filter(JobMatch.job_id == job_id).order_by(JobMatch.score.desc()).first()
    app_row = db.query(Application).filter(Application.job_id == job_id).order_by(Application.id.desc()).first()
    return {"job": {"title": r.title, "company": r.company, "url": r.url, "location": r.location,
                    "salary": r.salary, "verified": r.verified, "seniority": r.seniority,
                    "feedback": r.feedback, "required_skills": r.required_skills},
            "status": app_row.status if app_row else None,
            "match": {"score": m.score, "matching": m.matching_skills, "missing": m.missing_skills} if m else None}


class JobFeedbackReq(BaseModel):
    feedback: str


@app.post("/jobs/{job_id}/feedback")
async def job_feedback(job_id: int, req: JobFeedbackReq, db: Session = Depends(get_db)):
    """Mark a job good or bad so ranking learns from your judgement."""
    job = db.get(Job, job_id)
    if not job:
        return {"error": "not found"}
    try:
        result = job_feedback_service.record_feedback(db, job, req.feedback)
    except ValueError as e:
        return {"error": str(e)}
    ranked = rescore_stored(db=db)
    result["top_scores"] = [{"title": j["title"], "score": j["score"]} for j in ranked[:5]]
    return result

class PrepareReq(BaseModel):
    job_id: int

class StatusReq(BaseModel):
    status: str
    notes: str | None = None

@app.post("/applications/prepare")
async def applications_prepare(req: PrepareReq):
    return app_service.prepare(req.job_id)

@app.post("/applications/approve")
async def applications_approve(approval_id: int):
    return app_service.decide(approval_id, True)

@app.get("/applications")
async def applications_list(db: Session = Depends(get_db)):
    rows = db.query(Application).order_by(Application.id.desc()).limit(50).all()
    return [{"id": r.id, "job_id": r.job_id, "status": r.status, "created_at": str(r.created_at)} for r in rows]

@app.get("/applications/{app_id}")
async def application_detail(app_id: int, db: Session = Depends(get_db)):
    from app.database.models import ApplicationHistory, Job
    row = db.get(Application, app_id)
    if not row:
        return {"error": "application not found"}
    job = db.get(Job, row.job_id)
    history = db.query(ApplicationHistory).filter(ApplicationHistory.application_id == app_id).order_by(ApplicationHistory.id).all()
    approval = db.query(Approval).filter(Approval.application_id == app_id).order_by(Approval.id.desc()).first()
    return {
        "id": row.id,
        "job_id": row.job_id,
        "status": row.status,
        "job": {"title": job.title, "company": job.company, "url": job.url, "location": job.location} if job else None,
        "resume_version": row.resume_version,
        "cover_letter": row.cover_letter,
        "answers": row.answers,
        "notes": row.notes,
        "approval_status": approval.status if approval else None,
        "submission_status": "NOT auto-submitted",
        "created_at": str(row.created_at),
        "updated_at": str(row.updated_at),
        "history": [{"from": h.from_status, "to": h.to_status, "note": h.note, "at": str(h.created_at)} for h in history],
    }

@app.patch("/applications/{app_id}")
async def application_patch(app_id: int, req: StatusReq):
    result = app_service.set_status(app_id, req.status)
    if req.notes:
        db = None
        from app.database.session import SessionLocal
        from app.database.models import Application
        db = SessionLocal()
        try:
            row = db.get(Application, app_id)
            if row:
                row.notes = req.notes
                db.commit()
        finally:
            db.close()
        result["notes"] = req.notes
    return result

@app.post("/applications/{app_id}/approve")
async def application_approve(app_id: int):
    from app.database.session import SessionLocal
    from app.database.models import Approval
    db = SessionLocal()
    try:
        row = db.query(Approval).filter(Approval.application_id == app_id, Approval.status == "pending").first()
        if not row:
            return {"error": "no pending approval for this application"}
        approval_id = row.id
    finally:
        db.close()
    result = app_service.decide(approval_id, True)
    result["application_id"] = app_id
    return result

@app.post("/applications/{app_id}/reject")
async def application_reject(app_id: int):
    from app.database.session import SessionLocal
    from app.database.models import Approval
    db = SessionLocal()
    try:
        row = db.query(Approval).filter(Approval.application_id == app_id, Approval.status == "pending").first()
        if not row:
            return {"error": "no pending approval for this application"}
        approval_id = row.id
    finally:
        db.close()
    result = app_service.decide(approval_id, False)
    result["application_id"] = app_id
    return result

@app.post("/applications/{app_id}/status")
async def application_status(app_id: int, req: StatusReq):
    return app_service.set_status(app_id, req.status)

@app.get("/approvals")
async def approvals_list(db: Session = Depends(get_db)):
    rows = db.query(Approval).order_by(Approval.id.desc()).limit(50).all()
    email_rows = db.query(EmailApproval).order_by(EmailApproval.id.desc()).limit(50).all()
    out = [{"id": r.id, "application_id": r.application_id, "action": r.action, "status": r.status,
            "snapshot": r.content_snapshot, "created_at": str(r.created_at)} for r in rows]
    out += [{"id": r.id, "draft_id": r.draft_id, "application_id": None, "action": r.action,
             "status": r.status, "snapshot": r.content_snapshot, "created_at": str(r.created_at)}
            for r in email_rows]
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out

@app.post("/approvals/{approval_id}/approve")
async def approval_approve(approval_id: int):
    return app_service.decide(approval_id, True)

@app.post("/approvals/{approval_id}/reject")
async def approval_reject(approval_id: int):
    return app_service.decide(approval_id, False)

class EmailFetch(BaseModel):
    max_results: int = 25
    query: str = "newer_than:14d"

class DraftReq(BaseModel):
    email_id: int
    reply_body: str | None = None

@app.get("/gmail/status")
async def gmail_status():
    return {"credentials_present": gmail_client.credentials_exist(),
            "token_present": gmail_client.token_exists(),
            "readonly_scope": "https://www.googleapis.com/auth/gmail.readonly"}


@app.get("/gmail/account")
async def gmail_account():
    """The connected Gmail address, so the UI can show which inbox is linked."""
    if not gmail_client.token_exists():
        return {"connected": False, "email": None,
                "hint": "Run scripts/gmail_auth.py (read-only) - see docs/GMAIL_SETUP.md"}
    try:
        service = gmail_client.build_service(gmail_client.SCOPES_READONLY)
        profile = service.users().getProfile(userId="me").execute()
    except Exception as exc:  # noqa: BLE001
        return {"connected": False, "email": None, "error": str(exc)}
    creds = gmail_client.load_credentials(gmail_client.SCOPES_READONLY)
    scopes = list(creds.scopes or []) if creds else []
    return {
        "connected": True,
        "email": profile.get("emailAddress"),
        "messages_total": profile.get("messagesTotal"),
        "threads_total": profile.get("threadsTotal"),
        "scopes": scopes,
        "can_send": "https://www.googleapis.com/auth/gmail.send" in scopes,
    }


@app.get("/emails")
async def emails_list(db: Session = Depends(get_db), category: str | None = None, limit: int = 50):
    q = db.query(Email)
    if category:
        q = q.filter(Email.category == category)
    rows = q.order_by(Email.id.desc()).limit(min(limit, 100)).all()
    return [{"id": r.id, "sender": r.sender, "company": r.company, "subject": r.subject,
             "received_at": r.received_at, "job_role": r.job_role, "category": r.category,
             "important_details": r.important_details, "snippet": r.snippet} for r in rows]

@app.post("/emails/fetch")
async def emails_fetch(req: EmailFetch):
    try:
        return await gmail_service.fetch_and_store(req.max_results, req.query)
    except Exception as e:
        return {"error": str(e), "hint": "Run scripts/gmail_auth.py (read-only) first; see docs/GMAIL_SETUP.md"}

@app.post("/emails/draft")
async def emails_draft(req: DraftReq):
    return gmail_service.create_draft(req.email_id, req.reply_body)

@app.post("/emails/approve-send")
async def emails_approve_send(approval_id: int):
    return gmail_service.approve_send(approval_id)

@app.post("/emails/approve-reject")
async def emails_approve_reject(approval_id: int):
    return gmail_service.reject_send(approval_id)

@app.get("/emails/drafts")
async def email_drafts(db: Session = Depends(get_db)):
    rows = db.query(EmailDraft).order_by(EmailDraft.id.desc()).limit(50).all()
    return [{"id": r.id, "email_id": r.email_id, "recipient": r.recipient, "subject": r.subject,
             "body": r.body, "status": r.status} for r in rows]


@app.get("/emails/{email_id}")
async def email_detail(email_id: int, db: Session = Depends(get_db)):
    row = db.get(Email, email_id)
    if not row:
        return {"error": "email not found"}
    return {"id": row.id, "sender": row.sender, "company": row.company, "subject": row.subject,
            "received_at": row.received_at, "job_role": row.job_role, "category": row.category,
            "important_details": row.important_details, "snippet": row.snippet,
            "body": (row.body or "")[:8000]}

@app.post("/hiring-news/fetch")
async def hiring_news_fetch():
    return await news_service.fetch_and_store()

@app.get("/hiring-news")
async def hiring_news_list(db: Session = Depends(get_db), current_only: bool = False, limit: int = 50):
    q = db.query(HiringNews)
    if current_only:
        q = q.filter(HiringNews.is_current.is_(True))
    rows = q.order_by(HiringNews.relevance.desc(), HiringNews.id.desc()).limit(min(limit, 100)).all()
    return [{"id": r.id, "company": r.company, "role": r.role, "location": r.location,
             "experience": r.experience, "salary": r.salary, "posting_date": r.posting_date,
             "source": r.source, "official_source": r.official_source,
             "application_url": r.application_url, "relevance": r.relevance,
             "is_current": r.is_current, "title": r.title} for r in rows]

class StudyReq(BaseModel):
    exam: str = "SSC CGL"
    date: str | None = None
    topic: str | None = None

class AnswerReq(BaseModel):
    exam: str = "SSC CGL"
    topic: str
    answer: str

@app.get("/study/exams")
async def study_exams():
    exam_service.seed_syllabus()
    return {"exams": exam_names()}

@app.post("/study/seed")
async def study_seed():
    return exam_service.seed_syllabus()

@app.post("/study/start")
async def study_start(req: StudyReq):
    if req.exam not in exam_names():
        return {"error": f"unsupported exam. available: {exam_names()}"}
    plan = exam_service.get_or_create_plan(req.exam, req.date)
    topic = req.topic or (plan[0]["topic"] if plan else None)
    teaching = None
    if topic:
        teaching = await ollama_chat(
            f"Teach this {req.exam} topic briefly and clearly to a beginner: {topic}. "
            "Use simple language, 3 short bullet points, then one practice question. "
            "Do not invent official exam dates or notifications.")
    return {"exam": req.exam, "date": req.date or "today", "plan": plan, "focus_topic": topic,
            "teaching": teaching}

@app.get("/study/question")
async def study_question(topic: str):
    q = exam_service.get_question(topic)
    if not q:
        return {"error": f"no practice question stored for topic '{topic}' yet"}
    return {"topic": topic, "question": q["q"], "options": q["options"]}

@app.post("/study/answer")
async def study_answer(req: AnswerReq):
    q = exam_service.get_question(req.topic)
    if not q:
        return {"error": f"no practice question stored for topic '{req.topic}' yet"}
    return exam_service.record_answer(req.exam, req.topic, q, req.answer)

@app.get("/study/progress")
async def study_progress(exam: str | None = None):
    return exam_service.progress(exam)

@app.get("/study/topics")
async def study_topics(exam: str):
    return {"exam": exam, "topics": topics_for(exam)}

class TaskReq(BaseModel):
    title: str
    notes: str = ""
    category: str = "general"
    priority: int = 2
    due_date: str | None = None
    due_time: str | None = None
    remind_at: str | None = None

@app.post("/tasks")
async def tasks_create(req: TaskReq):
    return task_service.add_task(req.title, req.notes, req.category, req.priority,
                                  req.due_date, req.due_time, req.remind_at)

@app.get("/tasks")
async def tasks_list(status: str | None = None, due: str | None = None):
    return task_service.list_tasks(status, due)

@app.post("/tasks/{task_id}/complete")
async def tasks_complete(task_id: int):
    return task_service.complete_task(task_id)

@app.delete("/tasks/{task_id}")
async def tasks_delete(task_id: int, confirmed: bool = False):
    return task_service.delete_task(task_id, confirmed)

@app.get("/tasks/productivity")
async def tasks_productivity():
    return task_service.productivity_report()

@app.get("/reminders/due")
async def reminders_due():
    return {"due": task_service.due_reminders()}

@app.get("/schedules")
async def schedules_list():
    return scheduler.status()

class ScheduleReq(BaseModel):
    name: str
    job_type: str
    time_of_day: str | None = None
    interval_minutes: int | None = None
    enabled: bool = False

@app.post("/schedules")
async def schedules_set(req: ScheduleReq):
    return task_service.set_schedule(req.name, req.job_type, req.time_of_day,
                                      req.interval_minutes, req.enabled)

@app.post("/schedules/pause")
async def schedules_pause():
    return scheduler.pause()

@app.post("/schedules/resume")
async def schedules_resume():
    return scheduler.resume()

@app.post("/schedules/run/{job_type}")
async def schedules_run(job_type: str):
    return await scheduler.run_now(job_type)

class CodeReq(BaseModel):
    path: str | None = None
    code: str | None = None

@app.post("/developer/analyze")
async def developer_analyze(req: CodeReq):
    if req.code:
        return dev_service.analyze_code(req.code, req.path or "")
    if not req.path:
        return {"error": "provide path or code"}
    data = file_service.read_text(req.path)
    if "error" in data:
        return data
    return dev_service.analyze_code(data["content"], req.path)

@app.post("/developer/explain")
async def developer_explain(req: CodeReq):
    if req.code:
        return await dev_service.explain_code(req.code, req.path or "")
    if not req.path:
        return {"error": "provide path or code"}
    data = file_service.read_text(req.path)
    if "error" in data:
        return data
    return await dev_service.explain_code(data["content"], req.path)

@app.get("/developer/project")
async def developer_project(root: str | None = None):
    return dev_service.summarize_project(root)

@app.get("/files")
async def files_list(subdir: str = "", limit: int = 200):
    return file_service.list_files(subdir, limit)

@app.get("/files/read")
async def files_read(path: str):
    if Path(path).suffix.lower() == ".pdf":
        return file_service.read_pdf(path)
    return file_service.read_text(path)

@app.post("/files/summarize")
async def files_summarize(req: CodeReq):
    if req.path and Path(req.path).suffix.lower() == ".pdf":
        data = file_service.read_pdf(req.path)
    elif req.path:
        data = file_service.read_text(req.path)
    elif req.code:
        data = {"content": req.code, "path": "inline"}
    else:
        return {"error": "provide path or code"}
    if "error" in data:
        return data
    content = data.get("content") or data.get("text") or ""
    res = await ollama_chat(
        "Summarise this document for a busy professional. Give: 1) three bullet key points, "
        "2) important dates or numbers, 3) any action items. If the document is empty say so. "
        "Do not invent information.\n\n" + content[:12000])
    return {"path": data.get("path"), "summary": res}

@app.get("/voice/status")
async def voice_status():
    return voice_service.status()

@app.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    data = await audio.read()
    return voice_service.transcribe(data, audio.filename or "clip.webm")

class TtsReq(BaseModel):
    text: str

@app.post("/voice/tts")
async def voice_tts(req: TtsReq):
    return voice_service.speak(req.text)

@app.post("/voice/unload")
async def voice_unload():
    return voice_service.unload()


class VoiceAgentReq(BaseModel):
    message: str = ""
    history: list[dict] | None = None


@app.post("/voice/agent")
async def voice_agent(req: VoiceAgentReq):
    """One conversational turn: spoken request in, spoken answer out."""
    return await voice_service.agent_reply(req.message, req.history)


@app.get("/voice/agent/help")
async def voice_agent_help():
    """Things JARVIS can do by voice, in a form that is pleasant to read aloud."""
    return {
        "examples": [
            "Find Python backend developer jobs in India",
            "Show my pending tasks",
            "Show today's hiring news",
            "What are my top job matches",
            "Read my latest recruiter email",
            "Generate a resume from this job description",
            "Start my SSC CGL preparation",
            "Show pending approvals",
            "Run the daily report workflow",
            "Open the analytics overview",
        ],
        "notes": [
            "Anything that changes data still asks for your approval.",
            "Say stop to interrupt a spoken answer.",
        ],
    }

@app.get("/system/startup")
async def startup_status():
    return startup_service.status()

@app.post("/system/startup/enable")
async def startup_enable():
    return startup_service.enable()

@app.post("/system/startup/disable")
async def startup_disable():
    return startup_service.disable()

@app.post("/system/startup/start-backend")
async def startup_start_backend():
    return startup_service.open_backend()

@app.post("/system/backup")
async def system_backup(label: str = ""):
    result = backup_service.create_backup(label)
    logger.info("backup: %s", result.get("name", result.get("error")))
    return result

@app.get("/system/backups")
async def system_backups():
    return {"backups": backup_service.list_backups()}

@app.post("/system/restore")
async def system_restore(name: str):
    result = backup_service.restore_backup(name)
    logger.info("restore %s -> %s", name, result.get("ok", result.get("error")))
    return result


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse, JSONResponse

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str, request: Request):
        """Serve the built single page app with history fallback."""
        if request.scope.get("jarvis_api_path"):
            return JSONResponse(status_code=404, content={"error": "not found", "path": full_path})
        if full_path:
            candidate = (FRONTEND_DIST / full_path).resolve()
            try:
                candidate.relative_to(FRONTEND_DIST.resolve())
            except ValueError:
                candidate = None
            if candidate and candidate.is_file():
                return FileResponse(str(candidate))
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse(status_code=404, content={"error": "frontend build not found"})

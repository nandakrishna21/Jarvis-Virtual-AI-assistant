from fastapi import FastAPI, Depends, File, UploadFile, Request
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import asyncio, psutil, os
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
from app.services import rate_limit as rate_limit_service
from app.services import demo as demo_service
from app.services import job_actions as job_actions_service
from app.agents.job_discovery import feedback as job_feedback_service
from app.agents.job_discovery.service import search_and_save
from app.agents.job_discovery import feedback as job_feedback_service
from app.agents.job_discovery.service import rescore_stored, save_ranked_jobs
from app.agents.job_discovery import quality as job_quality
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
from app.api import weather as weather_api
from app.api import youtube as youtube_api
from app.api import openjarvis as openjarvis_api

logger = get_logger("jarvis.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    llm_service.load_persisted_provider()
    logger.info("JARVIS backend started (llm provider: %s)", settings.llm_provider)
    yield
    scheduler.stop()
    logger.info("JARVIS backend stopped")

def _cors_origins() -> list[str]:
    raw = (settings.cors_origins or "").strip()
    if not raw or raw == "*":
        return ["*"]
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="JARVIS", version="0.2.0", lifespan=lifespan)
_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False if "*" in _origins else True,
)


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


_PUBLIC_PATHS = {"/health"}
# Frontend routes that also exist as API paths. A browser navigation to them
# must still load the app shell; the data calls behind them stay key-protected.
_SPA_PATHS = {
    "/", "/assistant", "/jobs", "/jobs/all", "/matched", "/resume", "/resume-generator",
    "/voice", "/emails", "/documents", "/applications", "/applications/legacy",
    "/interviews", "/automation", "/analytics", "/settings",
}
_api_prefixes: list[tuple[str, str]] = []
# Built frontend files are public; the HTML shell cannot load without them.
_STATIC_PREFIXES = ("/assets/", "/static/")
_STATIC_FILES = {
    "/sw.js", "/manifest.webmanifest", "/favicon.svg", "/favicon.ico",
    "/icons.svg", "/apple-touch-icon.png", "/icon-192.png", "/icon-512.png",
    "/icon-maskable-512.png", "/robots.txt",
}


def _refresh_api_prefixes() -> None:
    """Track every registered API route so direct (non /api) calls are protected too."""
    global _api_prefixes
    entries: list[tuple[str, str]] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path or path == "/":
            continue
        if path in _PUBLIC_PATHS:
            continue
        if path in _STATIC_FILES or path.startswith(_STATIC_PREFIXES):
            continue
        if path.startswith("/{") and "{" in path:
            static = path.split("{")[0].rstrip("/")
            if not static:
                continue
            entries.append((path, static + "/"))
        else:
            entries.append((path, path + "/"))
    _api_prefixes = entries


def _is_api_path(path: str) -> bool:
    if path in _STATIC_FILES or path.startswith(_STATIC_PREFIXES):
        return False
    if path.startswith("/api/") or path == "/api":
        return True
    for exact, prefix in _api_prefixes:
        if path == exact or path.startswith(prefix):
            return True
    return False


_CHAT_PATHS = {"/chat", "/assistant/chat", "/assistant/command"}


def _rate_bucket(clean: str, method: str) -> tuple[str, int] | None:
    if method == "GET":
        return None
    if clean.startswith("/voice/"):
        return "voice", settings.rate_limit_voice_per_minute
    if clean in _CHAT_PATHS:
        return "chat", settings.rate_limit_chat_per_minute
    return "api", settings.rate_limit_api_per_minute


@app.middleware("http")
async def api_key_guard(request, call_next):
    """Protect the API, throttle abuse and fence off the public demo.

    The app shell and static files stay open so the unlock screen can load.
    Every API route needs the key when one is configured (important when the
    app is exposed through LAN, Tailscale or a public URL). In public demo mode
    a safe read-only allowlist replaces the key and all expensive routes are
    rate limited per client IP.
    """
    path = request.scope.get("path", "")
    clean = demo_service.normalize(path)
    is_api = _is_api_path(path)
    mutating = request.method in ("POST", "PUT", "PATCH", "DELETE")
    spa_navigation = (
        not mutating
        and clean in _SPA_PATHS
        and "text/html" in (request.headers.get("accept") or "")
    )
    if spa_navigation:
        is_api = False

    if is_api or mutating:
        if demo_service.is_blocked(path, request.method):
            return JSONResponse(
                status_code=403,
                content={"error": "This action is disabled in the public demo."},
            )
        bucket = _rate_bucket(clean, request.method)
        if bucket:
            name, limit = bucket
            allowed, retry_after = rate_limit_service.allow(
                name, rate_limit_service.client_ip(request), limit
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests. Please wait a moment and try again.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

    if auth_service.enabled() and not demo_service.enabled() and (is_api or mutating):
        provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if not auth_service.check(provided):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "api key required",
                    "hint": "Send the JARVIS_API_KEY value in the X-API-Key header.",
                },
            )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request, call_next):
    """Add conservative browser hardening headers to every response."""
    response = await call_next(request)
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; font-src 'self' data:; media-src 'self' blob:; "
        "worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    if proto == "https":
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


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
app.include_router(weather_api.router)
app.include_router(youtube_api.router)
app.include_router(openjarvis_api.router)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "demo": demo_service.enabled(),
    }

@app.get("/system/status")
async def status():
    from app.services import cache as cache_service

    async def build():
        vm = await run_in_threadpool(psutil.virtual_memory)
        cpu = await run_in_threadpool(psutil.cpu_percent, None)
        oll, loaded = await asyncio.gather(ollama_health(), running_models())
        llm = llm_service.provider_status()
        return {
            "cpu_percent": cpu,
            "ram_percent": vm.percent,
            "ram_free_gb": round(vm.available / 1024**3, 2),
            "demo": demo_service.enabled(),
            "ollama": oll,
            "llm": llm,
            "ai_ok": bool(oll.get("ok") or llm["available"].get(llm.get("active", ""))),
            "model": llm.get("models", {}).get(llm.get("active", "")) or settings.ollama_model,
            "loaded_models": loaded,
        }

    return await cache_service.get_or_set("system:status", 5, build)

@app.post("/chat")
async def chat(req: ChatRequest):
    return await handle(req.message)

@app.get("/system/metrics")
async def metrics():
    return await status()

@app.get("/system/diagnostics")
async def system_diagnostics_endpoint(include_openjarvis: bool = False):
    from app.services import system_diagnostics

    scan = await run_in_threadpool(system_diagnostics.quick_scan, include_openjarvis)
    scan["summary"] = system_diagnostics.summarize(scan)
    return scan

@app.get("/system/auth")
async def system_auth():
    status = auth_service.status()
    status["demo_mode"] = demo_service.enabled()
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


class ApifyJobSearch(BaseModel):
    query: str = Field("Python Backend Developer", min_length=1, max_length=200)
    location: str = Field("Hyderabad, India", max_length=200)
    limit: int = Field(20, ge=1, le=50)


@app.get("/jobs/apify/status")
def jobs_apify_status():
    from app.services import apify as apify_service

    return {
        "enabled": apify_service.enabled(),
        "actor": apify_service.actor_name(),
        "country": apify_service.country_for(settings.user_location),
        "max_items": settings.apify_max_items,
    }


@app.post("/jobs/apify")
async def jobs_apify(req: ApifyJobSearch, request: Request, db: Session = Depends(get_db)):
    """Paid deep search via Apify. Adds to the board without clearing it."""
    from app.services import apify as apify_service

    if not apify_service.enabled():
        return {"ok": False, "error": "Apify is not configured. Set APIFY_API_KEY in backend/.env."}
    allowed, retry_after = rate_limit_service.allow(
        "apify", rate_limit_service.client_ip(request), settings.apify_per_minute
    )
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "error": "Apify search rate limit reached. Try again in a minute.",
                "retry_after": retry_after,
            },
        )
    try:
        jobs = await apify_service.search_jobs(req.query, req.location, req.limit)
    except apify_service.ApifyError as exc:
        return {"ok": False, "error": str(exc)}
    if not jobs:
        return {"ok": True, "source": "apify", "count": 0, "jobs": []}
    rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
    skills = rp.extracted_skills.split(",") if rp and rp.extracted_skills else []
    ranked = save_ranked_jobs(jobs, req.query, req.location, skills, replace=False)
    return {"ok": True, "source": "apify", "count": len(jobs), "jobs": ranked}

@app.get("/jobs")
async def jobs_list(db: Session = Depends(get_db)):
    rows = db.query(Job).limit(50).all()
    return [{"id": r.id, "title": r.title, "company": r.company, "location": r.location,
             "url": r.url, "source": r.source, "verified": r.verified} for r in rows]

@app.get("/jobs/top-matches")
def top_matches(db: Session = Depends(get_db)):
    rows = db.query(JobMatch).order_by(JobMatch.score.desc()).limit(5).all()
    out = []
    for m in rows:
        j = db.get(Job, m.job_id)
        if j:
            out.append({"job_id": j.id, "title": j.title, "company": j.company, "url": j.url,
                        "score": m.score, "matching": m.matching_skills, "missing": m.missing_skills})
    return out

@app.get("/jobs/matched")
async def jobs_matched(
    min_score: float = 0,
    limit: int = 50,
    offset: int = 0,
    q: str = "",
    source: str = "",
    sort: str = "score",
    remote_only: bool = False,
    hide_irrelevant: bool = True,
    db: Session = Depends(get_db),
):
    """Professional match board: filtered, searchable, paginated and scored."""
    from app.services import profile as profile_service

    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    prefs = profile_service.get_preferences(db)
    rp = db.query(ResumeProfile).filter(ResumeProfile.is_active.is_(True)).order_by(ResumeProfile.id.desc()).first()
    if not rp:
        rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
    skills = [s.strip() for s in (rp.extracted_skills or "").split(",") if s.strip()] if rp else []

    statuses: dict[int, str] = {}
    for app_row in db.query(Application).order_by(Application.id.asc()).all():
        statuses[app_row.job_id] = app_row.status

    rows = db.query(JobMatch).order_by(JobMatch.score.desc()).limit(1000).all()
    board: list[dict] = []
    hidden = 0
    for match in rows:
        job = db.get(Job, match.job_id)
        if not job:
            continue
        if hide_irrelevant and not job_quality.is_relevant(job, skills, prefs):
            hidden += 1
            continue
        if hide_irrelevant and not job_quality.location_ok(job, prefs):
            hidden += 1
            continue
        components = json.loads(match.components) if match.components else {}
        notes = json.loads(match.notes) if match.notes else {}
        board.append({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "location": job.location,
            "job_type": job.job_type,
            "employment_type": job.employment_type,
            "score": match.score,
            "matching": match.matching_skills or "",
            "missing": match.missing_skills or "",
            "matching_skills": [s for s in (match.matching_skills or "").split(",") if s],
            "missing_skills": [s for s in (match.missing_skills or "").split(",") if s],
            "required_skills": [s for s in (job.required_skills or "").split(",") if s],
            "tags": [t for t in (job.tags or "").split(",") if t],
            "description": (job.description or "")[:700],
            "source": job.source,
            "seniority": job.seniority,
            "salary": job.salary,
            "feedback": job.feedback,
            "status": statuses.get(job.id),
            "components": components,
            "notes": notes,
            "_newest": job.created_at.isoformat() if job.created_at else "",
        })

    stats = {
        "total": len(board),
        "strong": sum(1 for j in board if (j["score"] or 0) >= 80),
        "good": sum(1 for j in board if 60 <= (j["score"] or 0) < 80),
        "applied": sum(1 for j in board if j["status"]),
        "hidden": hidden,
    }
    sources = sorted({j["source"] for j in board if j["source"]})

    filtered = [j for j in board if (j["score"] or 0) >= min_score]
    needle = q.strip().lower()
    if needle:
        filtered = [
            j for j in filtered
            if needle in " ".join(
                str(j.get(key) or "") for key in ("title", "company", "location", "description")
            ).lower()
            or needle in " ".join(j.get("tags") or []).lower()
        ]
    if source:
        filtered = [j for j in filtered if j["source"] == source]
    if remote_only:
        filtered = [
            j for j in filtered
            if j["job_type"] == "remote" or "remote" in (j["location"] or "").lower()
        ]

    if sort == "company":
        filtered.sort(key=lambda j: (j["company"] or "~").lower())
    elif sort == "newest":
        filtered.sort(key=lambda j: j["_newest"], reverse=True)
    else:
        filtered.sort(key=lambda j: j["score"] or 0, reverse=True)

    page = filtered[offset:offset + limit]
    for job in page:
        job.pop("_newest", None)
    return {
        "jobs": page,
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "stats": stats,
        "sources": sources,
    }


@app.get("/matching/results")
async def matching_results(min_score: float = 0, limit: int = 50, db: Session = Depends(get_db)):
    result = await jobs_matched(min_score=min_score, limit=limit, db=db)
    return result["jobs"]

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
    max_results: int = Field(25, ge=1, le=500)
    query: str = "newer_than:30d"

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
    from app.services import cache as cache_service

    async def build():
        if not gmail_client.token_exists():
            return {"connected": False, "email": None,
                    "hint": "Run scripts/gmail_auth.py (read-only) - see docs/GMAIL_SETUP.md"}

        def _read_profile():
            creds = gmail_client.load_credentials(gmail_client.SCOPES_SEND)
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            profile = service.users().getProfile(userId="me").execute()
            return creds, profile

        try:
            creds, profile = await run_in_threadpool(_read_profile)
        except Exception as exc:  # noqa: BLE001
            return {"connected": False, "email": None, "error": str(exc)}
        scopes = list(creds.scopes or []) if creds else []
        return {
            "connected": True,
            "email": profile.get("emailAddress"),
            "messages_total": profile.get("messagesTotal"),
            "threads_total": profile.get("threadsTotal"),
            "scopes": scopes,
            "can_send": "https://www.googleapis.com/auth/gmail.send" in scopes,
        }

    return await cache_service.get_or_set("gmail:account", 60, build)


@app.get("/emails")
async def emails_list(db: Session = Depends(get_db), category: str | None = None, limit: int = 50, q: str = ""):
    query = db.query(Email)
    if category and category != "all":
        query = query.filter(Email.category == category)
    if q.strip():
        needle = f"%{q.strip()}%"
        query = query.filter((Email.subject.ilike(needle)) | (Email.sender.ilike(needle)) | (Email.snippet.ilike(needle)) | (Email.company.ilike(needle)))
    rows = query.order_by(Email.id.desc()).limit(max(1, min(limit, 200))).all()
    return [{"id": r.id, "sender": r.sender, "company": r.company, "subject": r.subject,
             "received_at": r.received_at, "job_role": r.job_role, "category": r.category,
             "important_details": r.important_details, "snippet": r.snippet} for r in rows]

@app.post("/emails/fetch")
async def emails_fetch(req: EmailFetch):
    try:
        return await asyncio.to_thread(gmail_service.fetch_and_store, req.max_results, req.query)
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
def tasks_productivity():
    return task_service.productivity_report()

@app.get("/productivity")
def productivity_alias():
    """Compatibility alias used by the dashboard."""
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
    message: str = Field(default="", max_length=4000)
    history: list[dict] | None = Field(default=None, max_length=20)


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
            "Run a quick system scan: RAM, storage and CPU",
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
                headers = {}
                if full_path.startswith("assets/"):
                    headers["Cache-Control"] = "public, max-age=31536000, immutable"
                else:
                    headers["Cache-Control"] = "public, max-age=3600"
                return FileResponse(str(candidate), headers=headers)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index), headers={"Cache-Control": "no-cache"})
        return JSONResponse(status_code=404, content={"error": "frontend build not found"})

_refresh_api_prefixes()

"""Executable action handlers.

Each handler is the *only* code path that performs a mutating or external
action. They are registered with the proposal service and run exclusively
after the user approves the matching proposal.
"""
import logging

from sqlalchemy.orm import Session

from app.services.proposals import handler

logger = logging.getLogger("jarvis.actions")


@handler("create_task")
async def create_task(payload: dict, db: Session) -> dict:
    from app.agents.task_manager import service as task_service

    title = (payload.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "task title is required"}
    result = task_service.add_task(
        title=title,
        notes=payload.get("notes", ""),
        category=payload.get("category", "general"),
        priority=int(payload.get("priority", 2)),
        due_date=payload.get("due_date"),
        due_time=payload.get("due_time"),
        remind_at=payload.get("remind_at"),
    )
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "message": f"Task created: {title}", **result}


@handler("complete_task")
async def complete_task(payload: dict, db: Session) -> dict:
    from app.agents.task_manager import service as task_service

    task_id = int(payload["task_id"])
    result = task_service.complete_task(task_id)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "message": f"Task {task_id} marked completed", **result}


@handler("delete_task")
async def delete_task(payload: dict, db: Session) -> dict:
    from app.agents.task_manager import service as task_service

    task_id = int(payload["task_id"])
    result = task_service.delete_task(task_id, confirmed=True)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "message": f"Task {task_id} deleted", **result}


@handler("prepare_application")
async def prepare_application(payload: dict, db: Session) -> dict:
    from app.agents.job_application import service as app_service

    job_id = int(payload["job_id"])
    result = app_service.prepare(job_id)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {
        "ok": True,
        "message": "Application materials prepared and sent for review. Nothing was submitted.",
        **result,
    }


@handler("prepare_email_reply")
async def prepare_email_reply(payload: dict, db: Session) -> dict:
    from app.agents.gmail import service as gmail_service

    email_id = int(payload["email_id"])
    result = gmail_service.create_draft(email_id, payload.get("reply_body"))
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {
        "ok": True,
        "message": "Reply draft prepared. Review it in Approvals before anything is sent.",
        **result,
    }


@handler("send_email")
async def send_email(payload: dict, db: Session) -> dict:
    from app.agents.gmail import service as gmail_service

    approval_id = int(payload["approval_id"])
    result = gmail_service.approve_send(approval_id)
    if "error" in result:
        return {"ok": False, "error": result["error"]}
    return {"ok": True, "message": "Email sent.", **result}


@handler("run_workflow")
async def run_workflow(payload: dict, db: Session) -> dict:
    from app.agents.automation import service as automation_service

    name = payload.get("workflow", "")
    result = await automation_service.run_workflow(name, payload.get("payload") or {}, db)
    return {
        "ok": bool(result.get("ok")),
        "message": f"Workflow '{name}' finished via {result.get('engine')}",
        **result,
    }


@handler("create_schedule")
async def create_schedule(payload: dict, db: Session) -> dict:
    from app.agents.task_manager import service as task_service

    name = payload.get("name") or payload.get("job_type", "schedule")
    result = task_service.set_schedule(
        name=name,
        job_type=payload.get("job_type", "morning_report"),
        time_of_day=payload.get("time_of_day"),
        interval_minutes=payload.get("interval_minutes"),
        enabled=bool(payload.get("enabled", False)),
    )
    return {"ok": True, "message": f"Schedule '{name}' saved.", **result}


@handler("create_interview")
async def create_interview(payload: dict, db: Session) -> dict:
    from app.agents.interview import service as interview_service

    company = payload.get("company", "")
    if not company:
        return {"ok": False, "error": "company is required"}
    result = interview_service.create(
        db,
        company=company,
        role=payload.get("role", ""),
        interview_date=payload.get("interview_date"),
        interview_time=payload.get("interview_time"),
        mode=payload.get("mode", "online"),
        interviewer=payload.get("interviewer", ""),
        notes=payload.get("notes", ""),
        application_id=payload.get("application_id"),
    )
    return {"ok": True, "message": f"Interview scheduled with {company}.", **result}


@handler("fetch_jobs")
async def fetch_jobs(payload: dict, db: Session) -> dict:
    from app.agents.job_discovery.service import search_and_save
    from app.database.models import ResumeProfile

    rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
    skills = rp.extracted_skills.split(",") if rp and rp.extracted_skills else []
    query = payload.get("query", "Python Backend Developer")
    location = payload.get("location", "India")
    jobs = await search_and_save(query, location, skills)
    return {"ok": True, "message": f"Found {len(jobs)} job(s) for '{query}' in {location}.", "jobs": jobs}


@handler("fetch_news")
async def fetch_news(payload: dict, db: Session) -> dict:
    from app.agents.hiring_news import service as news_service

    result = await news_service.fetch_and_store()
    return {"ok": True, "message": f"Hiring news updated ({result.get('inserted', 0)} new).", **result}


@handler("fetch_emails")
async def fetch_emails(payload: dict, db: Session) -> dict:
    from app.agents.gmail import service as gmail_service

    try:
        emails = gmail_service.fetch_and_store(int(payload.get("max_results", 25)))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    recruiter = [e for e in emails if e.get("category") in ("recruiter", "interview", "assessment")]
    return {
        "ok": True,
        "message": f"Fetched {len(emails)} emails, {len(recruiter)} recruiter/interview.",
        "emails": emails[:20],
    }


@handler("generate_documents")
async def generate_documents(payload: dict, db: Session) -> dict:
    from app.services import documents

    resume_id = payload.get("resume_id")
    if not resume_id:
        from app.database.models import ResumeProfile

        rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            return {"ok": False, "error": "no resume uploaded yet"}
        resume_id = rp.id
    job_id = payload.get("job_id")
    result = documents.generate(
        db,
        int(resume_id),
        int(job_id) if job_id else None,
        payload.get("application_id"),
        payload.get("types"),
    )
    if result.get("error"):
        return {"ok": False, "error": result["error"]}
    return {
        "ok": True,
        "message": f"Generated {result.get('count', 0)} tailored document version(s). Drafts only.",
        **result,
    }


@handler("generate_resume_from_jd")
async def generate_resume_from_jd(payload: dict, db: Session) -> dict:
    """Build a targeted resume from a pasted job description."""
    from app.services import documents, resume_generator

    jd = (payload.get("jd") or "").strip()
    if not jd:
        return {"ok": False, "error": "no job description was provided"}

    resume_id = payload.get("resume_id")
    if not resume_id:
        from app.database.models import ResumeProfile

        rp = db.query(ResumeProfile).filter(ResumeProfile.is_active.is_(True)).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            return {"ok": False, "error": "no resume uploaded yet"}
        resume_id = rp.id

    built = await resume_generator.build_resume_from_jd(
        db,
        int(resume_id),
        jd,
        payload.get("role"),
        payload.get("company"),
        bool(payload.get("polish_summary", True)),
    )
    if built.get("error"):
        return {"ok": False, "error": built["error"]}

    saved = documents.save_version(
        db,
        int(resume_id),
        "resume",
        None,
        built["content"],
        built.get("match_score"),
        built.get("highlights"),
    )
    analysis = built.get("analysis") or {}
    return {
        "ok": True,
        "message": (
            f"Generated a targeted resume ({analysis.get('coverage_pct', 0)}% JD skill coverage, "
            f"{len(analysis.get('gaps') or [])} requirement(s) still missing). Draft only."
        ),
        "document": saved,
        "analysis": analysis,
        "content": built["content"],
    }


@handler("update_resume_sections")
async def update_resume_sections(payload: dict, db: Session) -> dict:
    from app.services import documents

    resume_id = payload.get("resume_id")
    if not resume_id:
        from app.database.models import ResumeProfile

        rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        if not rp:
            return {"ok": False, "error": "no resume uploaded yet"}
        resume_id = rp.id
    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        return {"ok": False, "error": "sections must be a non-empty list"}
    saved = []
    for item in sections:
        if not isinstance(item, dict):
            continue
        if item.get("id"):
            saved.append(documents.update_section(db, int(item["id"]), item))
        else:
            saved.append(documents.add_section(db, int(resume_id), item))
    return {"ok": True, "message": f"Saved {len(saved)} resume section(s).", "sections": saved}

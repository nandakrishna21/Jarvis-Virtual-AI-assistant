"""Automation service.

Runs a catalog workflow through n8n when n8n is reachable, and falls back to
the in-process implementation when it is not. Every run is recorded so the
Automation Center can show a real history instead of a status guess.
"""
import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.automation import catalog
from app.database.models import WorkflowRun
from app.integrations import n8n_client

logger = logging.getLogger("jarvis.automation")


async def n8n_status() -> dict:
    if not n8n_client.health:
        return {"ok": False, "error": "n8n client unavailable"}
    return await n8n_client.health()


async def run_workflow(name: str, payload: dict | None = None, db: Session = None) -> dict:
    wf = catalog.get(name)
    if not wf:
        return {"ok": False, "error": f"unknown workflow '{name}'"}

    payload = payload or {}
    started = time.perf_counter()
    engine = "n8n"
    status = "success"
    detail = ""
    result: dict = {}

    health = await n8n_client.health()
    if health.get("ok"):
        res = await n8n_client.trigger(wf["webhook"], payload)
        if res.get("ok"):
            result = {"engine": "n8n", "workflow": name, "response": res.get("response")}
            detail = str(res.get("response"))[:500]
        else:
            # fallback to native if n8n webhook fails
            engine = "native-fallback"
            native = await _run_native(wf["native"], payload)
            status = "success" if native.get("ok", True) else "error"
            detail = f"n8n webhook failed ({res.get('error') or res.get('status_code')}), native fallback: {str(native)[:300]}"
            result = {"engine": engine, "workflow": name, "n8n_error": res.get("error") or res.get("status_code"), "native": native}
    else:
        engine = "native"
        result = await _run_native(wf["native"], payload)
        status = "success" if result.get("ok", True) else "error"
        detail = str(result)[:500]

    duration = int((time.perf_counter() - started) * 1000)
    if db is not None:
        db.add(
            WorkflowRun(
                workflow=name,
                engine=engine,
                status=status,
                detail=detail,
                duration_ms=duration,
            )
        )
        db.commit()
        from app.services.notifications import notify_safe

        notify_safe(
            db,
            f"Workflow '{name}' finished ({engine})",
            detail[:300],
            "success" if status == "success" else "error",
            "/automation",
        )
    logger.info("workflow %s ran via %s (%s, %sms)", name, engine, status, duration)
    return {"ok": status == "success", "engine": engine, "workflow": name, "detail": detail, "result": result}


async def _run_native(job_type: str, payload: dict) -> dict:
    from app.agents.hiring_news import service as news_service
    from app.agents.task_manager import service as task_service

    try:
        if job_type == "morning_report":
            return {"ok": True, "report": task_service.productivity_report()}
        if job_type == "job_discovery":
            return {"ok": True, "news": await news_service.fetch_and_store()}
        if job_type == "gmail_review":
            from app.agents.gmail import service as gmail_service
            try:
                emails = await gmail_service.fetch_and_store()
                return {"ok": True, "fetched": len(emails)}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "error": f"gmail not configured: {exc}"}
        if job_type == "application_follow_up":
            return {"ok": True, "note": "follow-up drafts require Gmail; use the Applications page"}
        if job_type == "interview_reminders":
            from app.agents.interview import service as interview_service
            return {"ok": True, "reminders": interview_service.create_upcoming_tasks()}
        return {"ok": False, "error": f"no native implementation for '{job_type}'"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def list_runs(db: Session, limit: int = 30) -> list[dict]:
    rows = db.query(WorkflowRun).order_by(WorkflowRun.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "workflow": r.workflow,
            "engine": r.engine,
            "status": r.status,
            "detail": (r.detail or "")[:300],
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def overview(db: Session) -> dict:
    from app.database.models import Schedule

    schedules = db.query(Schedule).all()
    return {
        "workflows": catalog.all_workflows(),
        "runs": list_runs(db),
        "schedules": [
            {
                "id": s.id,
                "name": s.name,
                "job_type": s.job_type,
                "time_of_day": s.time_of_day,
                "enabled": s.enabled,
                "last_run": s.last_run,
            }
            for s in schedules
        ],
        "n8n_url": n8n_client._base(),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }

"""Simple background scheduler - checks every 60s, fires due jobs.

Jobs never auto-execute external side effects. Due jobs create ActionProposals
that require explicit user approval before execution.
"""
import asyncio
from datetime import datetime

from app.database.models import ActionProposal, Schedule
from app.database.session import SessionLocal

_state = {
    "running": False,
    "paused": True,
    "resting": False,
    "rest_since": None,
    "task": None,
    "last_run": None,
    "runs": 0,
    "last_proposed": None,
    "proposals_created": 0,
}


def _has_pending_schedule_proposal(db, schedule_id: int, job_type: str) -> bool:
    rows = db.query(ActionProposal).filter(ActionProposal.status == "pending").all()
    for r in rows:
        payload = r.payload or {}
        if r.action_type == "run_schedule_job" and str(payload.get("schedule_id")) == str(schedule_id):
            return True
        if r.action_type == "run_schedule_job" and payload.get("job_type") == job_type and payload.get("schedule_id") in (None, "", schedule_id):
            return True
    return False


def _create_schedule_proposal(db, s: Schedule) -> bool:
    from app.services import proposals

    if _has_pending_schedule_proposal(db, s.id, s.job_type):
        return False
    proposals.create_proposal(
        db,
        action_type="run_schedule_job",
        title=f"Run scheduled job: {s.name or s.job_type}",
        reason=f"Scheduled job '{s.job_type}' is due at {s.time_of_day}. Approval required before execution.",
        plan=[
            f"Review scheduled job {s.job_type}",
            "Approve to execute this job now",
            "Reject to skip this scheduled run",
        ],
        payload={"schedule_id": s.id, "job_type": s.job_type, "schedule_name": s.name, "time_of_day": s.time_of_day},
        source="scheduler",
        dedupe=True,
    )
    _state["last_proposed"] = datetime.now().isoformat(timespec="minutes")
    _state["proposals_created"] += 1
    return True


async def _run_schedule(s: Schedule) -> None:
    from app.agents.task_manager import service as task_service

    started = datetime.now()
    detail = ""
    status = "success"
    try:
        if s.job_type == "morning_report":
            report = task_service.productivity_report()
            detail = str(report)
        elif s.job_type == "job_discovery":
            from app.agents.hiring_news import service as news_service

            detail = str(await news_service.fetch_and_store())
        elif s.job_type == "gmail_review":
            from app.agents.gmail import service as gmail_service

            try:
                emails = await gmail_service.fetch_and_store()
                detail = str({"fetched": len(emails)})
            except Exception as e:
                status = "skipped"
                detail = f"gmail not configured: {e}"
        elif s.job_type == "study_reminder":
            fired = task_service.fire_reminders()
            detail = str({"reminders_fired": len(fired)})
        else:
            status = "skipped"
            detail = f"unknown job type {s.job_type}"
    except Exception as e:
        status = "error"
        detail = str(e)
    duration = int((datetime.now() - started).total_seconds() * 1000)
    task_service.log_run("scheduler", s.job_type, status, detail, duration)
    db = SessionLocal()
    try:
        row = db.get(Schedule, s.id)
        if row:
            row.last_run = datetime.now().isoformat(timespec="minutes")
            db.commit()
    finally:
        db.close()
    _state["last_run"] = datetime.now().isoformat(timespec="minutes")
    _state["runs"] += 1


async def _loop() -> None:
    while _state["running"]:
        try:
            if not _state["paused"] and not _state["resting"]:
                db = SessionLocal()
                try:
                    schedules = db.query(Schedule).filter(Schedule.enabled.is_(True)).all()
                    now = datetime.now()
                    for s in schedules:
                        if not s.time_of_day:
                            continue
                        try:
                            hh, mm = [int(x) for x in s.time_of_day.split(":")]
                        except Exception:
                            continue
                        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                        last = s.last_run
                        if target <= now and (not last or last[:16] < target.isoformat()[:16]):
                            _create_schedule_proposal(db, s)
                finally:
                    db.close()
        except Exception:
            pass
        await asyncio.sleep(60)


def start() -> dict:
    if _state["running"]:
        return {"status": "already running", **status()}
    _state["running"] = True
    _state["paused"] = False
    _state["task"] = asyncio.create_task(_loop())
    return {"status": "started", **status()}


def pause() -> dict:
    _state["paused"] = True
    return {"status": "paused", **status()}


def resume() -> dict:
    _state["paused"] = False
    _state["resting"] = False
    _state["rest_since"] = None
    return {"status": "resumed", **status()}


def rest() -> dict:
    """Put JARVIS in rest mode: no scheduled automations run until wake()."""
    _state["resting"] = True
    _state["rest_since"] = datetime.now().isoformat(timespec="seconds")
    return {"status": "resting", **status()}


def wake() -> dict:
    """Wake JARVIS from rest mode and resume schedules."""
    _state["resting"] = False
    _state["rest_since"] = None
    _state["paused"] = False
    return {"status": "awake", **status()}


def stop() -> dict:
    _state["running"] = False
    _state["paused"] = True
    if _state["task"]:
        _state["task"].cancel()
        _state["task"] = None
    return {"status": "stopped", **status()}


def status() -> dict:
    from app.agents.task_manager import service as task_service

    return {
        "running": _state["running"],
        "paused": _state["paused"],
        "resting": _state["resting"],
        "rest_since": _state["rest_since"],
        "last_run": _state["last_run"],
        "last_proposed": _state["last_proposed"],
        "runs": _state["runs"],
        "proposals_created": _state["proposals_created"],
        "approval_gated": True,
        "schedules": task_service.list_schedules(),
    }


async def run_now(job_type: str) -> dict:
    if _state["resting"]:
        return {"error": "JARVIS is resting. Wake it first.", "resting": True}
    db = SessionLocal()
    try:
        s = db.query(Schedule).filter(Schedule.job_type == job_type).first()
        if not s:
            s = Schedule(name=job_type, job_type=job_type)
            db.add(s)
            db.commit()
            db.refresh(s)
    finally:
        db.close()
    await _run_schedule(s)
    return {"ran": job_type, "last_run": _state["last_run"]}

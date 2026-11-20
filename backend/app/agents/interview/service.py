"""Interview tracker.

Keeps a record of every interview attached to an application and turns
upcoming interviews into tasks. Nothing here contacts anyone.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.database.models import Application, Interview, Job, Task

STATUSES = ["scheduled", "completed", "cancelled", "no_response"]
MODES = ["online", "onsite", "phone"]


def create(db: Session, company: str, role: str = "", interview_date: str | None = None,
           interview_time: str | None = None, mode: str = "online",
           interviewer: str = "", notes: str = "", application_id: int | None = None) -> dict:
    if mode not in MODES:
        mode = "online"
    row = Interview(
        application_id=application_id,
        company=company,
        role=role,
        interview_date=interview_date,
        interview_time=interview_time,
        mode=mode,
        interviewer=interviewer,
        notes=notes,
        status="scheduled",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_dict(row)


def update(db: Session, interview_id: int, **fields) -> dict:
    row = db.get(Interview, interview_id)
    if not row:
        return {"error": "interview not found"}
    for key in ("company", "role", "interview_date", "interview_time", "mode",
                "interviewer", "notes", "status"):
        if key in fields and fields[key] is not None:
            value = fields[key]
            if key == "mode" and value not in MODES:
                value = "online"
            if key == "status" and value not in STATUSES:
                value = "scheduled"
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return to_dict(row)


def delete(db: Session, interview_id: int) -> dict:
    row = db.get(Interview, interview_id)
    if not row:
        return {"error": "interview not found"}
    db.delete(row)
    db.commit()
    return {"interview_id": interview_id, "deleted": True}


def list_all(db: Session, status: str | None = None) -> list[dict]:
    q = db.query(Interview)
    if status:
        q = q.filter(Interview.status == status)
    rows = q.order_by(Interview.interview_date.is_(None), Interview.interview_date,
                       Interview.interview_time).all()
    return [to_dict(r) for r in rows]


def upcoming(db: Session, days: int = 7) -> list[dict]:
    limit = (date.today() + timedelta(days=days)).isoformat()
    rows = (
        db.query(Interview)
        .filter(Interview.status == "scheduled")
        .filter(Interview.interview_date.isnot(None))
        .filter(Interview.interview_date <= limit)
        .order_by(Interview.interview_date, Interview.interview_time)
        .all()
    )
    return [to_dict(r) for r in rows]


def create_upcoming_tasks(db: Session) -> list[dict]:
    """One task per interview happening in the next 24 hours."""
    created = []
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    for item in upcoming(db, days=1):
        title = f"Interview: {item['company']} - {item['role'] or 'role not specified'}"
        existing = db.query(Task).filter(Task.title == title, Task.status == "pending").first()
        if existing:
            continue
        db.add(Task(title=title, category="job", due_date=item["interview_date"] or tomorrow,
                    due_time=item["interview_time"], notes=item["notes"] or ""))
        row = db.get(Interview, item["id"])
        if row:
            row.reminder_sent = True
        created.append({"interview_id": item["id"], "task": title})
    db.commit()
    if created:
        _notify(db, f"{len(created)} interview reminder(s) created",
                "\n".join(c["task"] for c in created), "info", "/interviews")
    return created


def _notify(db: Session, title: str, body: str, kind: str, link: str = "") -> None:
    from app.services.notifications import notify_safe

    notify_safe(db, title, body, kind, link)


def to_dict(row: Interview) -> dict:
    return {
        "id": row.id,
        "application_id": row.application_id,
        "company": row.company,
        "role": row.role,
        "interview_date": row.interview_date,
        "interview_time": row.interview_time,
        "mode": row.mode,
        "interviewer": row.interviewer,
        "notes": row.notes,
        "status": row.status,
        "reminder_sent": row.reminder_sent,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def stats(db: Session) -> dict:
    total = db.query(Interview).count()
    scheduled = db.query(Interview).filter(Interview.status == "scheduled").count()
    completed = db.query(Interview).filter(Interview.status == "completed").count()
    next_items = upcoming(db, days=14)
    return {
        "total": total,
        "scheduled": scheduled,
        "completed": completed,
        "next": next_items[:5],
        "next_interview": next_items[0] if next_items else None,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def link_from_application(db: Session, application_id: int, interview_date: str,
                          interview_time: str = "", mode: str = "online", notes: str = "") -> dict:
    app_row = db.get(Application, application_id)
    if not app_row:
        return {"error": "application not found"}
    job = db.get(Job, app_row.job_id)
    return create(
        db,
        company=(job.company if job else "") or "",
        role=(job.title if job else "") or "",
        interview_date=interview_date,
        interview_time=interview_time,
        mode=mode,
        notes=notes,
        application_id=application_id,
    )

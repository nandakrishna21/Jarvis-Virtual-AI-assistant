"""Bulk actions on discovered jobs plus CSV export.

Every job decision is recorded twice: on the job row (`feedback`) so ranking can
learn from it, and on the application pipeline so the Command Center shows the
decision history.
"""
import csv
import io

from app.database.models import Application, ApplicationHistory, Job, JobMatch

APPROVE_STATUS = "Shortlisted"
REJECT_STATUS = "Rejected"


def _history(db, application_id: int, from_status: str | None, to_status: str, note: str | None = None):
    db.add(ApplicationHistory(
        application_id=application_id,
        from_status=from_status,
        to_status=to_status,
        note=note,
    ))


def _application_for(db, job_id: int):
    app_row = db.query(Application).filter(Application.job_id == job_id).order_by(Application.id.desc()).first()
    return app_row


def bulk_decision(db, job_ids: list[int], action: str) -> dict:
    action = (action or "").strip().lower()
    if action not in ("approve", "reject"):
        raise ValueError("action must be 'approve' or 'reject'")
    if not job_ids:
        return {"updated": 0, "action": action, "jobs": []}

    updated, missing = [], []
    for job_id in job_ids:
        job = db.get(Job, job_id)
        if not job:
            missing.append(job_id)
            continue
        job.feedback = "good" if action == "approve" else "bad"
        app_row = _application_for(db, job_id)
        previous = app_row.status if app_row else None
        if app_row is None:
            app_row = Application(job_id=job_id, status=APPROVE_STATUS if action == "approve" else REJECT_STATUS)
            db.add(app_row)
            db.flush()
            _history(db, app_row.id, None, app_row.status, f"Bulk {action}")
        else:
            app_row.status = APPROVE_STATUS if action == "approve" else REJECT_STATUS
            _history(db, app_row.id, previous, app_row.status, f"Bulk {action}")
        updated.append({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "status": app_row.status,
            "feedback": job.feedback,
        })
    db.commit()
    return {"updated": len(updated), "action": action, "jobs": updated, "missing": missing}


def export_csv(db, min_score: float = 0.0, limit: int = 500) -> str:
    rows = (
        db.query(JobMatch)
        .filter(JobMatch.score >= min_score)
        .order_by(JobMatch.score.desc())
        .limit(min(limit, 2000))
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([
        "score", "title", "company", "location", "seniority", "employment_type",
        "matching_skills", "missing_skills", "salary", "source", "feedback",
        "status", "posting_date", "url",
    ])
    for match in rows:
        job = db.get(Job, match.job_id)
        if not job:
            continue
        app_row = _application_for(db, job.id)
        writer.writerow([
            round(match.score or 0, 1),
            job.title or "",
            job.company or "",
            job.location or "",
            job.seniority or "",
            job.employment_type or "",
            match.matching_skills or "",
            match.missing_skills or "",
            job.salary or "",
            job.source or "",
            job.feedback or "",
            app_row.status if app_row else "",
            job.posting_date or "",
            job.url or "",
        ])
    return buffer.getvalue()

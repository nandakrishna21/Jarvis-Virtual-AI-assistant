"""Analytics API - every number comes from the database."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import (
    Application,
    ApplicationHistory,
    Interview,
    Job,
    JobMatch,
    Task,
    WorkflowRun,
)

router = APIRouter(tags=["analytics"])


def _count_by(db, model, column, limit=8):
    rows = db.query(column, model.id).all()
    counts = {}
    for value, _ in rows:
        key = value or "unknown"
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return [{"label": k, "value": v} for k, v in ordered[:limit]]


@router.get("/analytics/overview")
async def analytics_overview(db: Session = Depends(get_db)):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    apps = db.query(Application).all()
    submitted_statuses = {"Applied", "Interview", "Offer", "Rejected"}
    submitted = [a for a in apps if a.status in submitted_statuses]
    this_week = [a for a in submitted if (a.created_at.date().isoformat() if a.created_at else "") >= week_ago]

    jobs = db.query(Job).all()
    matches = db.query(JobMatch).all()
    scores = [m.score for m in matches if m.score is not None]

    tasks = db.query(Task).all()
    pending_tasks = [t for t in tasks if t.status == "pending"]

    return {
        "jobs": {
            "total": len(jobs),
            "with_match": len(matches),
            "high_match": len([m for m in matches if (m.score or 0) >= 80]),
            "good_match": len([m for m in matches if 60 <= (m.score or 0) < 80]),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "top_sources": _count_by(db, Job, Job.source),
        },
        "applications": {
            "total": len(apps),
            "submitted": len(submitted),
            "this_week": len(this_week),
            "by_status": _count_by(db, Application, Application.status, limit=12),
        },
        "interviews": {
            "total": db.query(Interview).count(),
            "scheduled": db.query(Interview).filter(Interview.status == "scheduled").count(),
            "completed": db.query(Interview).filter(Interview.status == "completed").count(),
        },
        "tasks": {
            "total": len(tasks),
            "pending": len(pending_tasks),
            "completed": len([t for t in tasks if t.status == "completed"]),
            "by_category": _count_by(db, Task, Task.category),
        },
        "automations": {
            "runs": db.query(WorkflowRun).count(),
            "failed": db.query(WorkflowRun).filter(WorkflowRun.status == "error").count(),
        },
        "history_points": [
            {
                "id": h.id,
                "application_id": h.application_id,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "note": h.note,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in db.query(ApplicationHistory).order_by(ApplicationHistory.id.desc()).limit(20).all()
        ],
    }


@router.get("/analytics/jobs")
async def analytics_jobs(db: Session = Depends(get_db)):
    rows = (
        db.query(Job, JobMatch)
        .join(JobMatch, JobMatch.job_id == Job.id)
        .order_by(JobMatch.score.desc())
        .limit(25)
        .all()
    )
    return {
        "jobs": [
            {
                "job_id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "score": m.score,
                "matching": m.matching_skills,
                "missing": m.missing_skills,
                "source": j.source,
            }
            for j, m in rows
        ]
    }


@router.get("/analytics/applications")
async def analytics_applications(db: Session = Depends(get_db)):
    rows = db.query(Application).order_by(Application.id.desc()).limit(50).all()
    return {
        "applications": [
            {
                "id": a.id,
                "job_id": a.job_id,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in rows
        ]
    }

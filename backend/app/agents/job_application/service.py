import json, hashlib
from datetime import datetime
from app.database.session import SessionLocal
from app.database.models import Job, JobMatch, ResumeProfile, Application, ApplicationHistory, Approval
from app.agents.job_application.materials import build_materials, STATUSES

def prepare(job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return {"error": "job not found"}
        rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        skills = rp.extracted_skills.split(",") if rp and rp.extracted_skills else []
        m = db.query(JobMatch).filter(JobMatch.job_id==job_id).order_by(JobMatch.score.desc()).first()
        match = {"matching_skills": m.matching_skills, "missing_skills": m.missing_skills, "score": m.score} if m else None
        mats = build_materials({"title": job.title, "company": job.company, "location": job.location}, skills, match)
        app_row = Application(job_id=job_id, status="Ready for approval",
                              cover_letter=mats["cover_letter"], answers=mats["answers"],
                              resume_version=rp.file_path if rp else "none")
        db.add(app_row); db.flush()
        db.add(ApplicationHistory(application_id=app_row.id, to_status="Ready for approval", note="materials prepared"))
        snapshot = json.dumps({"job_id": job_id, "job_url": job.url, "cover_letter": mats["cover_letter"], "answers": mats["answers"], "hash": hashlib.sha256(mats["cover_letter"].encode()).hexdigest()[:12]})
        appr = Approval(application_id=app_row.id, action="submit_application", content_snapshot=snapshot)
        db.add(appr); db.commit()
        return {"application_id": app_row.id, "approval_id": appr.id, "status": app_row.status,
                "cover_letter": mats["cover_letter"], "answers": mats["answers_dict"],
                "snapshot_hash": json.loads(snapshot)["hash"], "warning": "Review all content. Nothing submitted yet."}
    finally:
        db.close()

def decide(approval_id: int, approve: bool) -> dict:
    db = SessionLocal()
    try:
        appr = db.get(Approval, approval_id)
        if not appr: return {"error": "approval not found"}
        if appr.status != "pending": return {"error": f"already {appr.status}"}
        appr.status = "approved" if approve else "rejected"
        appr.decided_at = datetime.utcnow()
        app_row = db.get(Application, appr.application_id)
        new_status = "Approved" if approve else "Withdrawn"
        db.add(ApplicationHistory(application_id=appr.application_id, from_status=app_row.status, to_status=new_status,
                                  note="approved" if approve else "rejected by user"))
        app_row.status = new_status
        db.commit()
        # On approval: NO auto-submit. Submission requires a separate permitted manual step.
        return {"approval_id": approval_id, "status": appr.status, "application_status": new_status,
                "submission": "NOT auto-submitted" if approve else "cancelled",
                "next": "Use the original job URL to submit manually" if approve else "none"}
    finally:
        db.close()

def set_status(app_id: int, status: str) -> dict:
    if status not in STATUSES: return {"error": f"invalid status, use one of {STATUSES}"}
    db = SessionLocal()
    try:
        row = db.get(Application, app_id)
        if not row: return {"error": "not found"}
        db.add(ApplicationHistory(application_id=app_id, from_status=row.status, to_status=status))
        row.status = status; db.commit()
        return {"application_id": app_id, "status": status}
    finally:
        db.close()

from app.database.session import SessionLocal
from app.database.models import Job, JobMatch, ResumeProfile
from app.agents.job_discovery.connectors import fetch_jobs
from app.agents.job_discovery.scoring import rank
import json


def _preferences():
    from app.services import profile as profile_service

    db = SessionLocal()
    try:
        return profile_service.get_preferences(db)
    finally:
        db.close()


def _learned_weights() -> dict:
    from app.agents.job_discovery import feedback as feedback_service

    db = SessionLocal()
    try:
        return feedback_service.get_weights(db)
    finally:
        db.close()


def _skills(db):
    row = db.query(ResumeProfile).filter(ResumeProfile.is_active.is_(True)).order_by(ResumeProfile.id.desc()).first()
    if not row:
        row = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
    if not row or not row.extracted_skills:
        return []
    return [s.strip() for s in row.extracted_skills.split(",") if s.strip()]


def _job_to_dict(row: Job) -> dict:
    return {
        "title": row.title,
        "company": row.company,
        "location": row.location,
        "job_type": row.job_type,
        "url": row.url,
        "description": row.description or "",
        "required_skills": row.required_skills or "",
        "salary": row.salary,
        "experience": row.experience or "",
        "posting_date": row.posting_date,
        "source": row.source,
        "verified": row.verified or "unverified",
        "seniority": row.seniority or "",
        "tags": [t for t in (row.tags or "").split(",") if t],
        "employment_type": row.employment_type or "",
    }


def rescore_stored(db=None, prefs: dict | None = None, query: str = "") -> list[dict]:
    """Re-score every stored job with the current profile and learned feedback."""
    from app.agents.job_discovery import feedback as feedback_service

    owns_db = db is None
    db = db or SessionLocal()
    try:
        prefs = prefs if prefs is not None else _preferences()
        learned = feedback_service.get_weights(db)
        resume_skills = _skills(db)
        rows = db.query(Job).all()
        jobs = [_job_to_dict(r) for r in rows]
        ranked = rank(jobs, resume_skills, prefs, query, learned)
        by_url = {r.url: r for r in rows}
        for scored in ranked:
            row = by_url.get(scored["url"])
            if not row:
                continue
            match = db.query(JobMatch).filter(JobMatch.job_id == row.id).first()
            if match is None:
                match = JobMatch(job_id=row.id)
                db.add(match)
            match.score = scored["score"]
            match.matching_skills = ",".join(scored.get("matching_skills") or [])
            match.missing_skills = ",".join(scored.get("missing_skills") or [])
            match.components = json.dumps(scored.get("components") or {})
            match.notes = json.dumps(scored.get("notes") or {})
            row.required_skills = ",".join(scored.get("required_skills") or [])
            row.seniority = scored.get("seniority") or row.seniority
            row.experience = row.experience or (scored.get("notes") or {}).get("experience", "")
        db.commit()
        return ranked
    finally:
        if owns_db:
            db.close()


async def search_and_save(query: str, location: str, resume_skills: list[str] | None = None,
                          prefs: dict | None = None) -> list[dict]:
    prefs = prefs if prefs is not None else _preferences()
    levels = [str(l).lower() for l in (prefs.get("experience_levels") or [])]
    require_entry = any(l in {"entry-level", "junior", "fresher", "graduate", "intern"}
                        for l in levels)

    jobs = await fetch_jobs(query, location, require_entry=require_entry)
    if resume_skills is None:
        db = SessionLocal()
        try:
            resume_skills = _skills(db)
        finally:
            db.close()
    if resume_skills is None:
        resume_skills = []

    ranked = rank(jobs, resume_skills, prefs, query, _learned_weights())
    db = SessionLocal()
    try:
        previous_feedback = {
            r.url: r.feedback for r in db.query(Job).all() if r.feedback
        }
        db.query(Job).delete()
        db.query(JobMatch).delete()
        for j in ranked:
            row = Job(
                title=j["title"],
                company=j.get("company"),
                location=j.get("location"),
                job_type=j.get("job_type"),
                url=j["url"],
                description=(j.get("description") or "")[:8000],
                required_skills=",".join(j.get("required_skills") or []),
                salary=j.get("salary"),
                experience=j.get("experience") or (j.get("notes") or {}).get("experience"),
                posting_date=j.get("posting_date"),
                source=j.get("source"),
                verified=j.get("verified", "unverified"),
                seniority=j.get("seniority"),
                tags=",".join((j.get("tags") or [])[:20]),
                employment_type=j.get("employment_type") or "",
                feedback=previous_feedback.get(j["url"]),
            )
            db.add(row)
            db.flush()
            db.add(JobMatch(
                job_id=row.id,
                score=j["score"],
                matching_skills=",".join(j.get("matching_skills") or []),
                missing_skills=",".join(j.get("missing_skills") or []),
                components=json.dumps(j.get("components") or {}),
                notes=json.dumps(j.get("notes") or {}),
            ))
        db.commit()
        _notify_matches(db, ranked, query, location)
    finally:
        db.close()
    return ranked[:5]


def _notify_matches(db, ranked: list[dict], query: str, location: str) -> None:
    from app.services.notifications import notify_safe

    strong = [j for j in ranked if (j.get("score") or 0) >= 60][:3]
    if not strong:
        return
    lines = [
        f"{j['title']} at {j.get('company') or 'company not published'} ({j['score']}% match)"
        for j in strong
    ]
    notify_safe(
        db,
        f"{len(strong)} strong job match(es) for '{query}'",
        "\n".join(lines),
        "success",
        "/matched",
    )

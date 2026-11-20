"""User profile and job-search preferences.

The defaults match the initial owner profile. Everything is editable from
Settings and stored in SQLite.
"""
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import UserPreference

DEFAULT_PREFERENCES = {
    "name": settings.user_name,
    "location": settings.user_location,
    "markets": ["India", "Remote worldwide"],
    "target_categories": [
        "Python Backend Developer",
        "Junior Python Developer",
        "AI Engineer",
        "Junior AI Application Developer",
        "Agentic AI Engineer",
        "LLM Engineer",
        "RAG Developer",
        "AI Automation Engineer",
        "AI Implementation Engineer",
        "Technical Support Engineer",
        "Application Support Engineer",
        "AI Operations Associate",
        "Associate Forward Deployed Engineer",
        "Junior Solutions Engineer",
    ],
    "salary": "Negotiable",
    "employment_types": ["Full-time", "Internship", "Contract"],
    "work_modes": ["Remote", "Hybrid", "On-site"],
    "experience_levels": ["Entry-level", "Junior", "1-3 years"],
    "search_interval_minutes": 240,
}

JSON_FIELDS = ("markets", "target_categories", "employment_types", "work_modes", "experience_levels")


def _loads(value, fallback):
    if not value:
        return list(fallback)
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else list(fallback)
    except (TypeError, ValueError):
        return list(fallback)


def get_preferences(db: Session) -> dict:
    row = db.query(UserPreference).order_by(UserPreference.id.desc()).first()
    if not row:
        return dict(DEFAULT_PREFERENCES)
    data = dict(DEFAULT_PREFERENCES)
    data.update(
        {
            "name": row.name or DEFAULT_PREFERENCES["name"],
            "location": row.location or DEFAULT_PREFERENCES["location"],
            "salary": row.salary or DEFAULT_PREFERENCES["salary"],
            "search_interval_minutes": row.search_interval_minutes or DEFAULT_PREFERENCES["search_interval_minutes"],
            "resume_path": row.resume_path or "",
        }
    )
    for field in JSON_FIELDS:
        data[field] = _loads(getattr(row, field), DEFAULT_PREFERENCES[field])
    return data


def update_preferences(db: Session, changes: dict) -> dict:
    row = db.query(UserPreference).order_by(UserPreference.id.desc()).first()
    if not row:
        row = UserPreference()
        db.add(row)
    for key in ("name", "location", "salary", "resume_path"):
        if changes.get(key) is not None:
            setattr(row, key, str(changes[key]))
    if changes.get("search_interval_minutes") is not None:
        row.search_interval_minutes = int(changes["search_interval_minutes"])
    for field in JSON_FIELDS:
        if changes.get(field) is not None:
            value = changes[field]
            setattr(row, field, json.dumps(value if isinstance(value, list) else [value]))
    row.updated_at = datetime.utcnow()
    db.commit()
    return get_preferences(db)


def resume_skills(db: Session) -> list[str]:
    from app.database.models import ResumeProfile

    rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
    if not rp or not rp.extracted_skills:
        return []
    return [s.strip() for s in rp.extracted_skills.split(",") if s.strip()]

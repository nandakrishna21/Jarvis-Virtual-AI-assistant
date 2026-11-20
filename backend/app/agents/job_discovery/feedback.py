"""Learning from job feedback.

When you mark a job as good or bad, the skills that show up in those postings
shift the skill component of the score. A skill that keeps appearing in the
roles you like gets boosted; one that keeps appearing in roles you reject gets
penalised. Nothing is invented: the weights come only from jobs you judged.
"""
import json

from app.database.models import AppSetting, Job

SETTING_KEY = "job_scoring_learned"


def _skills_of(job: Job) -> list[str]:
    raw = job.required_skills or ""
    if not raw:
        from app.agents.job_discovery.scoring import extract_skills
        raw = ",".join(extract_skills(f"{job.title or ''} {job.description or ''}"))
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


def learn_weights(db) -> dict:
    """Recompute skill boosts from every good/bad job marked so far."""
    good_counts: dict[str, int] = {}
    bad_counts: dict[str, int] = {}
    good_jobs = bad_jobs = 0
    for job in db.query(Job).all():
        if job.feedback == "good":
            good_jobs += 1
            for skill in _skills_of(job):
                good_counts[skill] = good_counts.get(skill, 0) + 1
        elif job.feedback == "bad":
            bad_jobs += 1
            for skill in _skills_of(job):
                bad_counts[skill] = bad_counts.get(skill, 0) + 1

    boost, penalize = {}, {}
    for skill in set(good_counts) | set(bad_counts):
        good = good_counts.get(skill, 0)
        bad = bad_counts.get(skill, 0)
        total = good + bad
        if total == 0:
            continue
        ratio = (good + 0.5) / (total + 1.0)
        delta = round((ratio - 0.5) * 2, 3)
        if delta > 0:
            boost[skill] = delta
        elif delta < 0:
            penalize[skill] = abs(delta)

    weights = {
        "boost": boost,
        "penalize": penalize,
        "good_jobs": good_jobs,
        "bad_jobs": bad_jobs,
        "samples": good_jobs + bad_jobs,
    }
    row = db.query(AppSetting).filter(AppSetting.key == SETTING_KEY).first()
    if row is None:
        db.add(AppSetting(key=SETTING_KEY, value=json.dumps(weights)))
    else:
        row.value = json.dumps(weights)
    db.commit()
    return weights


def get_weights(db) -> dict:
    row = db.query(AppSetting).filter(AppSetting.key == SETTING_KEY).first()
    if not row or not row.value:
        return {"boost": {}, "penalize": {}, "good_jobs": 0, "bad_jobs": 0, "samples": 0}
    try:
        data = json.loads(row.value)
    except Exception:
        return {"boost": {}, "penalize": {}, "good_jobs": 0, "bad_jobs": 0, "samples": 0}
    data.setdefault("boost", {})
    data.setdefault("penalize", {})
    data.setdefault("good_jobs", 0)
    data.setdefault("bad_jobs", 0)
    data.setdefault("samples", 0)
    return data


def record_feedback(db, job: Job, feedback: str) -> dict:
    feedback = (feedback or "").strip().lower()
    if feedback not in ("good", "bad"):
        raise ValueError("feedback must be 'good' or 'bad'")
    job.feedback = feedback
    db.commit()
    weights = learn_weights(db)
    return {"job_id": job.id, "feedback": feedback, "weights": weights}

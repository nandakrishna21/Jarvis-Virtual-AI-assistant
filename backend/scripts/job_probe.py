import asyncio

from app.agents.job_discovery.connectors import fetch_jobs
from app.agents.job_discovery.scoring import rank
from app.services import profile as ps
from app.database.session import SessionLocal
from app.database.models import ResumeProfile

db = SessionLocal()
rp = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
skills = [s.strip() for s in (rp.extracted_skills or "").split(",") if s.strip()]
prefs = ps.get_preferences(db)
db.close()

print("resume skills:", skills)
print("target categories:", (prefs.get("target_categories") or [])[:5])
print("experience levels:", prefs.get("experience_levels"))
print()

jobs = asyncio.run(fetch_jobs("Python Backend Developer", "India", max_results=8))
print("fetched:", len(jobs))
ranked = rank(jobs, skills, prefs, "Python Backend Developer")
for j in ranked:
    c = j["components"]
    title = (j["title"] or "")[:42]
    company = (j.get("company") or "")[:18]
    print(
        f"{j['score']:>5}  {title:<42} | {company:<18} | {j['source']:<10} "
        f"| sen={j.get('seniority'):<10} | skills={c['skills']:>5} exp={c['experience']:>5} "
        f"resp={c['responsibilities']:>5} loc={c['location']:>5}"
    )
    print(f"        match={j['matching_skills']}")
    print(f"        miss={j['missing_skills'][:8]} | {j['notes']['experience']}")

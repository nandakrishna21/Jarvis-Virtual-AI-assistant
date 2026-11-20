"""Job scoring.

Spec weights: skills 35 / experience 25 / responsibilities 20 / location 10 / education 10.

Every component is now measurable from the data we actually have (title,
description, tags, location, seniority, dates) and from your profile. Nothing
is invented: when a component cannot be measured it reports as neutral and
says so.

The previous version scored almost every job the same (~50) because the
connectors never filled `required_skills`. Skills are now read from the title,
tags and the full description.
"""
import re

TECH_TERMS = [
    "python", "django", "fastapi", "flask", "rest", "graphql", "api", "postgresql",
    "postgres", "sqlite", "mysql", "mongodb", "redis", "react", "javascript", "typescript",
    "html", "css", "git", "docker", "aws", "gcp", "azure", "linux", "sql", "pandas", "numpy",
    "tensorflow", "pytorch", "machine learning", "ml", "deep learning", "nlp", "llm",
    "rag", "langchain", "llamaindex", "openai", "ollama", "vector", "embedding", "faiss",
    "pinecone", "celery", "uvicorn", "nginx", "kafka", "airflow", "spark", "hadoop",
    "etl", "websockets", "oauth", "jwt", "pytest", "ci/cd", "terraform", "jenkins",
]

RESPONSIBILITY_TERMS = [
    "develop", "build", "design", "implement", "maintain", "deploy", "test", "debug",
    "optimi", "refactor", "integrate", "architect", "lead", "mentor", "review",
    "automate", "scale", "monitor", "analyz", "deliver", "collaborat", "research",
]

DEGREE_TERMS = {
    "b.tech": "b.tech", "btech": "b.tech", "b.e": "b.e", "bachelor": "bachelor",
    "b.sc": "b.sc", "bsc": "b.sc", "m.tech": "m.tech", "master": "master",
    "mca": "mca", "mba": "mba", "phd": "phd", "doctorate": "phd",
    "high school": "secondary", "higher secondary": "secondary", "hsc": "secondary",
    "ssc": "secondary", "intermediate": "secondary",
}

ENTRY_LEVELS = {"entry-level", "junior", "fresher", "graduate", "intern", "0-1 years"}
MID_LEVELS = {"1-3 years", "mid-level", "associate", "trainee"}


def _blob(job: dict) -> str:
    parts = [
        job.get("title") or "",
        job.get("description") or "",
        " ".join(job.get("tags") or []),
        job.get("required_skills") or "",
    ]
    return " ".join(p for p in parts if p).lower()


def extract_skills(text: str) -> list[str]:
    low = (text or "").lower()
    found = []
    for term in TECH_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", low):
            found.append(term)
    return found


def _skill_component(job: dict, resume_skills: list[str],
                     learned: dict | None = None) -> tuple[float, list[str], list[str], list[str]]:
    req = {s.lower() for s in (job.get("required_skills") or "").split(",") if s.strip()}
    if not req:
        req = set(extract_skills(_blob(job)))
    if not req:
        return 50.0, [], [], []
    have = {s.lower() for s in resume_skills}
    # resume skills may be phrased differently, match on containment too
    for s in list(have):
        for r in list(req):
            if s and r and (s in r or r in s):
                have.add(r)
    matching = sorted(req & have)
    missing = sorted(req - have)

    boost = (learned or {}).get("boost") or {}
    penalize = (learned or {}).get("penalize") or {}
    weighted_hit = weighted_total = 0.0
    for requirement in req:
        weight = 1.0 + 0.5 * float(boost.get(requirement, 0)) - 0.5 * float(penalize.get(requirement, 0))
        weight = max(0.2, min(2.0, weight))
        weighted_total += weight
        if requirement in have:
            weighted_hit += weight
    score = round(100 * weighted_hit / weighted_total, 1) if weighted_total else 50.0
    return score, matching, missing, sorted(req)


def _seniority_component(job: dict, prefs: dict | None) -> tuple[float, str]:
    levels = [str(l).lower() for l in ((prefs or {}).get("experience_levels") or [])]
    wants_entry = any(l in ENTRY_LEVELS for l in levels)
    wants_mid = any(l in MID_LEVELS for l in levels)
    job_seniority = (job.get("seniority") or "").lower()

    if job_seniority == "executive":
        return 0.0, "executive level - far above your target"
    if job_seniority == "senior":
        if wants_entry:
            return 20.0, "senior role - above your target level"
        return 55.0, "senior role"
    if job_seniority == "entry":
        if wants_entry:
            return 100.0, "entry level - matches your target"
        if wants_mid:
            return 85.0, "entry level - slightly below your target"
        return 75.0, "entry level"
    if job_seniority == "mid":
        if wants_entry:
            return 70.0, "mid-level role - slightly above your target"
        if wants_mid:
            return 95.0, "mid-level - matches your target"
        return 75.0, "mid-level role"

    blob = f"{job.get('title') or ''} {job.get('experience') or ''}".lower()
    if re.search(r"\b(\d+)\s*[-–]\s*(\d+)\s*years?\b", blob):
        low, high = re.search(r"\b(\d+)\s*[-–]\s*(\d+)\s*years?\b", blob).groups()
        low = int(low)
        if wants_entry and low > 4:
            return 20.0, f"{low}+ years required - above your target"
        if wants_entry and low <= 2:
            return 95.0, f"{low}-{high} years - fits your target"
        if wants_mid and low <= 3:
            return 90.0, f"{low}-{high} years - fits your target"
        return 70.0, f"{low}-{high} years experience"
    if re.search(r"\b\d+\+\s*years?\b", blob):
        return 30.0, "experienced role"
    if "no experience" in blob or "fresher" in blob:
        return 100.0, "no experience required - matches your target"
    return 60.0, "seniority not stated"


def _responsibility_component(job: dict, resume_skills: list[str]) -> tuple[float, list[str]]:
    desc = (job.get("description") or "").lower()
    if not desc:
        return 50.0, []
    hits = [t for t in RESPONSIBILITY_TERMS if t in desc]
    have = {s.lower() for s in resume_skills}
    skill_hits = [t for t in extract_skills(desc) if any(t in s or s in t for s in have)]
    score = min(100.0, 45.0 + len(hits) * 4.0 + len(skill_hits) * 6.0)
    return round(score, 1), sorted(set(skill_hits))[:8]


def _location_component(job: dict, prefs: dict | None) -> tuple[float, str]:
    loc = f"{job.get('location') or ''} {job.get('job_type') or ''}".lower()
    markets = [str(m).lower() for m in ((prefs or {}).get("markets") or [])]
    work_modes = [str(m).lower() for m in ((prefs or {}).get("work_modes") or [])]

    if job.get("job_type") == "remote" or "remote" in loc:
        if any("remote" in w for w in work_modes):
            return 100.0, "remote - matches your work modes"
        return 85.0, "remote (check if you want remote only)"
    if any(m and m in loc for m in markets if m != "remote worldwide"):
        return 95.0, "located in your target market"
    if "india" in loc:
        return 85.0, "India-based"
    if any(h in loc for h in ("hyderabad", "bangalore", "pune", "mumbai", "chennai", "delhi")):
        return 80.0, "Indian metro - check relocation"
    return 45.0, "outside your target markets"


def _education_component(job: dict, resume_skills: list[str]) -> tuple[float, str]:
    desc = (job.get("description") or "").lower()
    if not desc:
        return 50.0, "not stated in the posting"
    mentioned = {v for k, v in DEGREE_TERMS.items() if k in desc}
    if not mentioned:
        return 70.0, "no specific degree required"
    if any(m in ("b.tech", "b.e", "b.sc", "bachelor") for m in mentioned):
        return 90.0, "bachelor level - typical for your target roles"
    if any(m in ("m.tech", "master", "mca", "mba") for m in mentioned):
        return 65.0, "master's level preferred"
    return 70.0, f"mentions {', '.join(sorted(mentioned))}"


def score_job(resume_skills: list[str], job: dict, prefs: dict | None = None,
              query: str = "", learned: dict | None = None) -> dict:
    """Score one job. Returns the total plus every component for transparency."""
    skill_score, matching, missing, required = _skill_component(job, resume_skills, learned)
    exp_score, exp_note = _seniority_component(job, prefs)
    resp_score, skill_hits = _responsibility_component(job, resume_skills)
    loc_score, loc_note = _location_component(job, prefs)
    edu_score, edu_note = _education_component(job, resume_skills)

    role_score, role_note = _role_component(job, query, prefs)

    overall = round(
        skill_score * 0.35
        + exp_score * 0.25
        + resp_score * 0.20
        + loc_score * 0.10
        + edu_score * 0.10,
        1,
    )

    return {
        "score": overall,
        "skill_match": skill_score,
        "experience_match": exp_score,
        "responsibility_match": resp_score,
        "location_match": loc_score,
        "education_match": edu_score,
        "role_match": role_score,
        "matching_skills": matching,
        "missing_skills": missing,
        "required_skills": required,
        "skill_hits": skill_hits,
        "notes": {
            "experience": exp_note,
            "location": loc_note,
            "education": edu_note,
            "role": role_note,
        },
        "location_note": loc_note,
        "components": {
            "skills": skill_score,
            "experience": exp_score,
            "responsibilities": resp_score,
            "location": loc_score,
            "education": edu_score,
        },
    }


def _role_component(job: dict, query: str, prefs: dict | None) -> tuple[float, str]:
    title = (job.get("title") or "").lower()
    targets = [str(t).lower() for t in ((prefs or {}).get("target_categories") or [])]
    candidates = targets + ([query.lower()] if query else [])

    best = 0.0
    best_target = ""
    for target in candidates:
        if not target:
            continue
        t_tokens = [t for t in re.findall(r"[a-z0-9+#.]+", target) if len(t) > 2]
        if not t_tokens:
            continue
        hits = sum(1 for t in t_tokens if t in title)
        score = 100.0 * hits / len(t_tokens)
        if score > best:
            best = score
            best_target = target
    if best >= 90:
        return best, f"title matches '{best_target}'"
    if best > 0:
        return best, f"partial match on '{best_target}'"
    return 40.0, "title does not clearly match your target roles"


def rank(jobs: list[dict], resume_skills: list[str], prefs: dict | None = None,
         query: str = "", learned: dict | None = None) -> list[dict]:
    scored = []
    for j in jobs:
        s = score_job(resume_skills, j, prefs, query, learned)
        scored.append({**j, **s})
    return sorted(scored, key=lambda x: x["score"], reverse=True)

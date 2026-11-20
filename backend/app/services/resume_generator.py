"""Resume Generator: build a targeted resume from a pasted job description.

The rules that keep this honest:

* Every line of the generated resume comes from the user's own resume (the
  uploaded file text or the structured sections). Nothing is invented.
* The JD is used to decide what to lead with, which order the sections and
  bullets appear in, and which skills are listed first.
* Requirements the user cannot show evidence for are reported as gaps outside
  the resume body instead of being quietly added to it.
* An optional LLM pass can rewrite the summary, and its output is rejected if
  it mentions a technology that does not appear in the user's own resume.
"""
import re

from sqlalchemy.orm import Session

from app.agents.job_discovery.scoring import TECH_TERMS, extract_skills
from app.database.models import ResumeProfile, ResumeSection

BULLET_RE = re.compile(r"^\s*(?:[-*•‣▪◦]|\d+[.)])\s+")
CONTACT_RE = re.compile(r"([\w.+-]+@[\w.-]+\.\w+)|(\+?\d[\d\s().-]{7,}\d)|(https?://\S+)|((?:linkedin|github)\.com/\S*)", re.I)

EXTRA_TECH = [
    "rest api", "restful", "graphql", "pytest", "ci/cd", "terraform", "jenkins",
    "nginx", "kafka", "rabbitmq", "celery", "airflow", "spark", "hadoop", "etl",
    "websockets", "oauth", "jwt", "microservices", "unit testing", "code review",
    "agile", "jira", "figma", "power bi", "tableau", "excel", "sap",
]

TITLE_PATTERNS = [
    re.compile(r"(?:job\s*title|position|role|title)\s*[:\-]\s*(.+)", re.I),
    re.compile(r"^\s*(?:we are |we're )?(?:hiring|looking for)\s+(?:an?\s+)?(.+)$", re.I | re.M),
]
COMPANY_PATTERNS = [
    re.compile(r"(?:company|employer|organisation|organization)\s*[:\-]\s*(.+)", re.I),
    re.compile(r"\bat\s+([A-Z][\w&.\- ]{2,40}(?:Technologies|Systems|Labs|Solutions|Software|Services|AI|Infosys|TCS))"),
]
YEARS_RE = re.compile(r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?years?")


def _first_line(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", (value or "").strip())
    return value.strip(" .,-|:")


def _trim_title(value: str) -> str:
    """A title is a short noun phrase - cut it before the first clause."""
    value = _clean_value(value)
    value = re.split(r"\b(?:to|for|who|that|which|will|with)\b", value, maxsplit=1, flags=re.I)[0]
    words = value.split()
    if len(words) > 7:
        value = " ".join(words[:7])
    return _clean_value(value)


def _dedupe_terms(terms: list[str]) -> list[str]:
    """Drop a short term when a longer one already covers it (e.g. rest / rest api)."""
    ordered = sorted(terms, key=len, reverse=True)
    kept: list[str] = []
    for term in ordered:
        low = term.lower()
        if any(low != k and low in k for k in kept):
            continue
        kept.append(term)
    return sorted(kept)


def parse_jd(jd_text: str) -> dict:
    """Pull the useful parts out of a pasted job description."""
    text = (jd_text or "").strip()
    low = text.lower()
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    title = ""
    for pattern in TITLE_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = _trim_title(match.group(1))
            if candidate and len(candidate) <= 80:
                title = candidate
                break
    if not title and lines:
        first = lines[0]
        if len(first) < 90 and not first.lower().startswith(("we are", "job description", "about the role", "responsibilit", "requirement")):
            title = _trim_title(first)

    company = ""
    for pattern in COMPANY_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = _trim_title(match.group(1))
            if candidate and len(candidate) <= 80:
                company = candidate
                break

    skills = extract_skills(text)
    for term in EXTRA_TECH:
        if term in low and term not in skills:
            skills.append(term)
    skills = _dedupe_terms(skills)

    years = [int(m) for m in YEARS_RE.findall(low)]
    min_years = max(years) if years else 0

    location = ""
    loc_match = re.search(r"(?:location|based in|work location)\s*[:\-]\s*([^\n]{2,60})", text, re.I)
    if loc_match:
        location = _clean_value(loc_match.group(1))
    elif re.search(r"\bremote\b", low):
        location = "Remote"

    responsibilities = []
    for line in lines:
        if BULLET_RE.match(line) and len(line) > 25:
            responsibilities.append(BULLET_RE.sub("", line))

    return {
        "title": title,
        "company": company,
        "skills": sorted(set(skills)),
        "min_years": min_years,
        "location": location,
        "responsibilities": responsibilities[:20],
        "text": text,
        "word_count": len(text.split()),
    }


def render_profile_text(details: dict) -> str:
    """Render the structured details into the plain-text resume JARVIS reads."""
    lines: list[str] = []
    name = (details.get("name") or "").strip()
    if name:
        lines.append(name)
    contact_bits = [
        (details.get("email") or "").strip(),
        (details.get("phone") or "").strip(),
        (details.get("location") or "").strip(),
    ]
    for link in (details.get("links") or []):
        link = str(link).strip()
        if link:
            contact_bits.append(link)
    if contact_bits:
        lines.append(" | ".join([b for b in contact_bits if b]))

    summary = (details.get("summary") or "").strip()
    if summary:
        lines.append("")
        lines.append("SUMMARY")
        lines.append(summary)

    skills = [str(s).strip() for s in (details.get("skills") or []) if str(s).strip()]
    if skills:
        lines.append("")
        lines.append("SKILLS")
        lines.append(", ".join(skills))

    for key, label in (("experience", "EXPERIENCE"), ("projects", "PROJECTS"), ("education", "EDUCITION")):
        entries = details.get(key) or []
        if not entries:
            continue
        lines.append("")
        lines.append(label)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            header = " - ".join([p for p in [
                (entry.get("title") or "").strip(),
                (entry.get("organization") or "").strip(),
            ] if p])
            dates = " - ".join([p for p in [
                (entry.get("start_date") or "").strip(),
                (entry.get("end_date") or "").strip(),
            ] if p])
            if header and dates:
                header = f"{header} ({dates})"
            elif dates and not header:
                header = dates
            if header:
                lines.append(header)
            if entry.get("location"):
                lines.append(str(entry["location"]).strip())
            body = (entry.get("description") or "").strip()
            for body_line in [l.strip() for l in body.splitlines() if l.strip()]:
                lines.append(f"- {BULLET_RE.sub('', body_line)}")
            if not body and entry.get("bullets"):
                for bullet in entry["bullets"]:
                    bullet = str(bullet).strip()
                    if bullet:
                        lines.append(f"- {BULLET_RE.sub('', bullet)}")
    return "\n".join(lines).rstrip() + "\n"


def _resume_facts(db: Session, resume_id: int) -> dict:
    profile = db.get(ResumeProfile, resume_id)
    if not profile:
        return {}
    sections = (
        db.query(ResumeSection)
        .filter(ResumeSection.resume_id == resume_id)
        .order_by(ResumeSection.position, ResumeSection.id)
        .all()
    )
    text = profile.raw_text or ""
    skills = [s.strip() for s in (profile.extracted_skills or "").split(",") if s.strip()]
    for term in extract_skills(text):
        if term not in skills:
            skills.append(term)

    section_text = "\n".join((s.description or "") for s in sections)
    for term in extract_skills(section_text):
        if term not in skills:
            skills.append(term)
    for term in EXTRA_TECH:
        if term in section_text.lower() and term not in skills:
            skills.append(term)
    skills = _dedupe_terms(skills)

    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if BULLET_RE.match(stripped):
            bullets.append(BULLET_RE.sub("", stripped))

    section_lines: list[str] = []
    for s in sections:
        for line in (s.description or "").splitlines():
            stripped = line.strip()
            if stripped:
                section_lines.append(BULLET_RE.sub("", stripped))

    contact = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and CONTACT_RE.search(stripped) and len(stripped) < 160:
            contact.append(stripped)

    return {
        "profile": profile,
        "text": text,
        "full_text": "\n".join([text, section_text]).lower(),
        "skills": skills,
        "bullets": bullets or section_lines,
        "contact": contact,
        "sections": [
            {
                "section_type": s.section_type,
                "title": s.title or "",
                "organization": s.organization or "",
                "location": s.location or "",
                "start_date": s.start_date or "",
                "end_date": s.end_date or "",
                "description": s.description or "",
            }
            for s in sections
        ],
    }


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    low = (text or "").lower()
    return [k for k in keywords if k and k in low]


def _relevance_rank(text: str, keywords: list[str]) -> int:
    return len(_keyword_hits(text, keywords))


def _section_lines(section: dict, keywords: list[str]) -> list[str]:
    """Section body split into lines, most JD-relevant first."""
    body = section.get("description") or ""
    lines = [BULLET_RE.sub("", l.strip()) for l in body.splitlines() if l.strip()]
    if not lines:
        return []
    ordered = sorted(
        lines,
        key=lambda l: (_relevance_rank(l, keywords), -len(l)),
        reverse=True,
    )
    return ordered


def _experience_header(section: dict) -> str:
    header = section.get("title") or ""
    if section.get("organization"):
        header += f" - {section['organization']}"
    if section.get("start_date") or section.get("end_date"):
        header += f" ({section.get('start_date') or ''} - {section.get('end_date') or 'present'})"
    return header


async def build_resume_from_jd(db: Session, resume_id: int, jd_text: str,
                               role: str | None = None, company: str | None = None,
                               polish_summary: bool = True) -> dict:
    facts = _resume_facts(db, resume_id)
    if not facts:
        return {"error": "resume not found"}
    jd = parse_jd(jd_text)
    if not jd["text"]:
        return {"error": "paste a job description first"}

    target_role = (role or jd.get("title") or "").strip()
    target_company = (company or jd.get("company") or "").strip()
    jd_skills = jd["skills"]

    resume_skills = [s for s in facts["skills"]]
    resume_text = facts.get("full_text") or (facts.get("text") or "").lower()

    def _evidenced(term: str) -> bool:
        low = term.lower()
        if any(low == r.lower() or low in r.lower() or r.lower() in low for r in resume_skills):
            return True
        return bool(low) and low in resume_text

    covered = [s for s in jd_skills if _evidenced(s)]
    gaps = [s for s in jd_skills if s not in covered]

    keyword_pool = jd_skills + [k.lower() for k in jd["title"].lower().split() if len(k) > 3]

    ordered_skills = [s for s in jd_skills if s in covered]
    for s in resume_skills:
        if s not in ordered_skills:
            ordered_skills.append(s)
    ordered_skills = _dedupe_terms(ordered_skills)

    summary_section = next((s for s in facts["sections"] if s["section_type"] == "summary"), None)
    summary_text = (summary_section or {}).get("description", "").strip()
    if not summary_text:
        summary_text = _build_summary(facts, target_role, covered, jd)

    llm_summary = ""
    if polish_summary and covered:
        llm_summary = await _polish_summary(summary_text, target_role, target_company, covered, facts)

    lines: list[str] = []
    name_line = ""
    if facts["contact"]:
        name_line = facts["contact"][0]
        for line in facts["contact"]:
            if "@" in line or "+" in line:
                name_line = line
                break
    lines.append(name_line or "YOUR NAME")
    if target_role:
        lines.append(f"Target role: {target_role}")
    if target_company:
        lines.append(f"Company: {target_company}")
    if jd.get("location"):
        lines.append(f"Location: {jd['location']}")
    for contact in facts["contact"]:
        if contact != name_line:
            lines.append(contact)
    lines.append("")

    if llm_summary:
        lines.append("SUMMARY")
        lines.append(llm_summary)
        lines.append("")
    elif summary_text:
        lines.append("SUMMARY")
        lines.append(summary_text)
        lines.append("")

    if ordered_skills:
        lines.append("SKILLS")
        lines.append(", ".join(ordered_skills[:25]))
        lines.append("")

    for section in facts["sections"]:
        stype = section["section_type"]
        if stype in ("summary", "skills"):
            continue
        label = {"experience": "EXPERIENCE", "education": "EDUCATION",
                 "projects": "PROJECTS", "custom": (section["title"] or "DETAILS").upper()}.get(
            stype, stype.upper())
        lines.append(label)
        header = _experience_header(section)
        if header:
            lines.append(header)
        if section.get("location"):
            lines.append(section["location"])
        body_lines = _section_lines(section, keyword_pool)
        if body_lines:
            for body_line in body_lines:
                lines.append(f"- {body_line}")
        else:
            free_text = (section.get("description") or "").strip()
            if free_text:
                lines.append(free_text)
        lines.append("")

    if not facts["sections"]:
        for bullet in sorted(facts["bullets"], key=lambda b: _relevance_rank(b, keyword_pool), reverse=True)[:15]:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append("Generated locally by JARVIS from your own resume. Review every line before sending.")

    coverage_pct = round(100 * len(covered) / len(jd_skills), 1) if jd_skills else 0.0
    highlights = [
        f"{len(covered)} of {len(jd_skills)} JD skill(s) evidenced in your resume",
        f"{coverage_pct}% JD skill coverage",
    ]
    if gaps:
        highlights.append(f"{len(gaps)} JD requirement(s) not yet in your resume - listed as gaps, not added to it")
    if llm_summary:
        highlights.append("Summary rewritten by the configured AI provider (facts checked against your resume)")

    return {
        "doc_type": "resume",
        "content": "\n".join(lines).rstrip() + "\n",
        "match_score": coverage_pct,
        "highlights": highlights,
        "job": {
            "title": target_role,
            "company": target_company,
            "location": jd.get("location"),
            "required_skills": jd_skills,
            "matching": covered,
            "missing": gaps,
        },
        "analysis": {
            "jd_title": jd.get("title"),
            "jd_company": jd.get("company"),
            "jd_skills": jd_skills,
            "covered": covered,
            "gaps": gaps,
            "coverage_pct": coverage_pct,
            "min_years": jd.get("min_years"),
            "resume_skills_used": ordered_skills[:25],
            "responsibilities_in_jd": len(jd.get("responsibilities") or []),
            "source_resume_id": resume_id,
            "ai_summary_used": bool(llm_summary),
        },
    }


def _build_summary(facts: dict, role: str, covered: list[str], jd: dict) -> str:
    """Deterministic summary built only from facts found in the resume."""
    if not covered:
        return ""
    years = jd.get("min_years") or 0
    experience_note = f" with {years}+ year(s) of relevant experience" if years else ""
    role_text = f" for {role}" if role else ""
    return (
        f"Targeted {role_text}. Hands-on experience{experience_note} across "
        f"{', '.join(covered[:6])}. Every claim below comes from the uploaded resume."
    )


async def _polish_summary(summary: str, role: str, company: str, covered: list[str], facts: dict) -> str:
    """Optional AI rewrite. Rejected if it introduces unknown technologies."""
    from app.services import llm

    if not role and not covered:
        return ""
    known = {s.lower() for s in facts["skills"]}
    facts_text = "\n".join(facts["bullets"][:25]) or (facts.get("text") or "")[:1500]
    prompt = (
        "Rewrite the candidate summary below for the given job description.\n"
        "Rules: use only technologies and facts that appear in the candidate facts; "
        "do not invent employers, dates, metrics or skills; keep it 2-3 sentences; "
        "no bullet points, no headings.\n\n"
        f"Job role: {role or 'not specified'}\n"
        f"Company: {company or 'not specified'}\n"
        f"Target skills from the JD: {', '.join(covered)}\n\n"
        f"Candidate facts:\n{facts_text}\n\n"
        f"Candidate summary:\n{summary}"
    )
    try:
        result = await llm.chat(prompt, system="You are a precise resume editor.")
    except Exception:  # noqa: BLE001
        return ""
    if not result.get("ok"):
        return ""
    text = (result.get("response") or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    for term in TECH_TERMS + EXTRA_TECH:
        if term in lowered and not any(term in k or k in term for k in known):
            return ""
    return text

"""Tailored document generation with versioning.

Builds a job-specific resume and cover letter from the structured resume
sections plus the extracted skills, stores every generation as a numbered
version, and writes plain-text files that can be downloaded.

Nothing here submits anything to an employer. The documents are drafts for
the user to review.
"""
import json
import os
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models import DocumentVersion, Job, JobMatch, ResumeProfile, ResumeSection

DOC_DIR = "C:/JARVIS/data/documents"
SECTION_TYPES = ["summary", "experience", "education", "projects", "skills", "custom"]


def _safe_name(text: str, fallback: str = "document") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (text or "").strip())
    return (cleaned[:60] or fallback)


def list_sections(db: Session, resume_id: int) -> list[dict]:
    rows = (
        db.query(ResumeSection)
        .filter(ResumeSection.resume_id == resume_id)
        .order_by(ResumeSection.position, ResumeSection.id)
        .all()
    )
    return [section_to_dict(r) for r in rows]


def section_to_dict(row: ResumeSection) -> dict:
    return {
        "id": row.id,
        "resume_id": row.resume_id,
        "section_type": row.section_type,
        "title": row.title or "",
        "organization": row.organization or "",
        "location": row.location or "",
        "start_date": row.start_date or "",
        "end_date": row.end_date or "",
        "description": row.description or "",
        "position": row.position or 0,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def add_section(db: Session, resume_id: int, data: dict) -> dict:
    section_type = (data.get("section_type") or "custom").strip().lower()
    if section_type not in SECTION_TYPES:
        section_type = "custom"
    position = data.get("position")
    if position is None:
        position = db.query(ResumeSection).filter(ResumeSection.resume_id == resume_id).count()
    row = ResumeSection(
        resume_id=resume_id,
        section_type=section_type,
        title=(data.get("title") or "").strip(),
        organization=(data.get("organization") or "").strip(),
        location=(data.get("location") or "").strip(),
        start_date=(data.get("start_date") or "").strip(),
        end_date=(data.get("end_date") or "").strip(),
        description=(data.get("description") or "").strip(),
        position=int(position),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return section_to_dict(row)


def update_section(db: Session, section_id: int, data: dict) -> dict:
    row = db.get(ResumeSection, section_id)
    if not row:
        return {"error": "section not found"}
    if data.get("section_type"):
        value = str(data["section_type"]).strip().lower()
        row.section_type = value if value in SECTION_TYPES else "custom"
    for field in ("title", "organization", "location", "start_date", "end_date", "description"):
        if data.get(field) is not None:
            setattr(row, field, str(data[field]).strip())
    if data.get("position") is not None:
        row.position = int(data["position"])
    db.commit()
    db.refresh(row)
    return section_to_dict(row)


def delete_section(db: Session, section_id: int) -> dict:
    row = db.get(ResumeSection, section_id)
    if not row:
        return {"error": "section not found"}
    db.delete(row)
    db.commit()
    return {"id": section_id, "deleted": True}


def _skills(db: Session, resume_id: int) -> list[str]:
    rp = db.get(ResumeProfile, resume_id)
    if not rp or not rp.extracted_skills:
        return []
    return [s.strip() for s in rp.extracted_skills.split(",") if s.strip()]


def _job_info(db: Session, job_id: int | None) -> dict:
    if not job_id:
        return {}
    job = db.get(Job, job_id)
    if not job:
        return {}
    match = (
        db.query(JobMatch)
        .filter(JobMatch.job_id == job_id)
        .order_by(JobMatch.score.desc())
        .first()
    )
    required = [s.strip() for s in (job.required_skills or "").split(",") if s.strip()]
    return {
        "id": job.id,
        "title": job.title or "",
        "company": job.company or "",
        "location": job.location or "",
        "url": job.url or "",
        "description": job.description or "",
        "required_skills": required,
        "score": match.score if match else None,
        "matching": [s.strip() for s in (match.matching_skills or "").split(",") if s.strip()] if match else [],
        "missing": [s.strip() for s in (match.missing_skills or "").split(",") if s.strip()] if match else [],
    }


def _order_skills(skills: list[str], job: dict) -> list[str]:
    required = [s.lower() for s in job.get("required_skills", [])]
    matched = [s.lower() for s in job.get("matching", [])]
    priority = required + matched
    ordered = [s for s in skills if s.lower() in priority]
    rest = [s for s in skills if s.lower() not in priority]
    return ordered + rest


def build_resume(db: Session, resume_id: int, job_id: int | None = None) -> dict:
    rp = db.get(ResumeProfile, resume_id)
    if not rp:
        return {"error": "resume not found"}
    job = _job_info(db, job_id)
    sections = list_sections(db, resume_id)
    skills = _order_skills(_skills(db, resume_id), job)

    lines: list[str] = []
    headline = job.get("title") or "Professional"
    lines.append(headline.upper())
    lines.append("-" * len(headline))
    if job.get("company"):
        lines.append(f"Target role: {headline} at {job['company']}")
    if job.get("location"):
        lines.append(f"Location: {job['location']}")
    lines.append("")

    if skills:
        lines.append("SKILLS")
        lines.append(", ".join(skills))
        lines.append("")

    for section in sections:
        stype = section["section_type"]
        if stype == "summary":
            lines.append("SUMMARY")
            lines.append(section["description"])
            lines.append("")
            continue
        if stype == "skills":
            continue
        label = {"experience": "EXPERIENCE", "education": "EDUCATION",
                 "projects": "PROJECTS", "custom": section["title"].upper() or "DETAILS"}.get(
            stype, stype.upper())
        lines.append(label)
        header = section["title"]
        if section["organization"]:
            header += f" - {section['organization']}"
        if section["start_date"] or section["end_date"]:
            header += f" ({section['start_date'] or ''} - {section['end_date'] or 'present'})"
        if header:
            lines.append(header)
        if section["location"]:
            lines.append(section["location"])
        if section["description"]:
            lines.append(section["description"])
        lines.append("")

    if not sections:
        lines.append("EXPERIENCE")
        lines.append("Add structured sections in Resume Intelligence to fill this in.")
        lines.append("")

    if job:
        lines.append("TARGETED FOR THIS ROLE")
        if job.get("matching"):
            lines.append(f"Direct overlap: {', '.join(job['matching'])}")
        if job.get("missing"):
            lines.append(f"Gaps to close: {', '.join(job['missing'])}")
        lines.append("")

    lines.append("Generated locally by JARVIS. Review every line before submitting.")

    highlights = []
    if job.get("matching"):
        highlights.append(f"Highlights {len(job['matching'])} matching skill(s): {', '.join(job['matching'][:8])}")
    if job.get("score") is not None:
        highlights.append(f"Match score {job['score']}%")

    return {
        "doc_type": "resume",
        "content": "\n".join(lines).rstrip() + "\n",
        "match_score": job.get("score"),
        "highlights": highlights,
        "job": job,
    }


def build_cover_letter(db: Session, resume_id: int, job_id: int | None = None) -> dict:
    rp = db.get(ResumeProfile, resume_id)
    if not rp:
        return {"error": "resume not found"}
    job = _job_info(db, job_id)
    skills = _skills(db, resume_id)
    sections = list_sections(db, resume_id)
    experience = next((s for s in sections if s["section_type"] == "experience"), None)
    summary = next((s for s in sections if s["section_type"] == "summary"), None)

    lines: list[str] = []
    if job.get("title"):
        lines.append(f"Dear Hiring Manager for {job['title']},")
    else:
        lines.append("Dear Hiring Manager,")
    lines.append("")

    opening = (
        f"I am applying for the {job.get('title') or 'position'} role"
        f"{' at ' + job['company'] if job.get('company') else ''}."
    )
    lines.append(opening)
    if job.get("matching"):
        lines.append(
            "My work aligns with this role on "
            + ", ".join(job["matching"][:6])
            + ", which is exactly what the posting asks for."
        )
    elif skills:
        lines.append("My hands-on experience covers " + ", ".join(skills[:6]) + ".")
    lines.append("")

    if summary and summary["description"]:
        lines.append(summary["description"])
        lines.append("")

    if experience:
        lines.append(
            f"Most recently I worked as {experience['title']}"
            f"{' at ' + experience['organization'] if experience['organization'] else ''}."
        )
        if experience["description"]:
            lines.append(experience["description"])
        lines.append("")

    if job.get("missing"):
        lines.append(
            "I am actively strengthening "
            + ", ".join(job["missing"][:5])
            + ", and I would welcome the chance to discuss how my existing experience transfers."
        )
        lines.append("")

    lines.append("I would love the chance to discuss how I can help. Thank you for your time.")
    lines.append("")
    lines.append("Regards,")
    lines.append("(your name)")
    lines.append("")
    lines.append("Draft prepared locally by JARVIS. Review and edit before sending.")

    highlights = []
    if job.get("matching"):
        highlights.append(f"References {len(job['matching'])} job requirement(s) from the posting")
    if experience:
        highlights.append("Uses your latest experience entry")
    if job.get("missing"):
        highlights.append("Acknowledges gaps honestly instead of hiding them")

    return {
        "doc_type": "cover_letter",
        "content": "\n".join(lines).rstrip() + "\n",
        "match_score": job.get("score"),
        "highlights": highlights,
        "job": job,
    }


def save_version(db: Session, resume_id: int, doc_type: str, job_id: int | None,
                 content: str, match_score: float | None = None,
                 highlights: list[str] | None = None,
                 application_id: int | None = None) -> dict:
    q = db.query(DocumentVersion).filter(DocumentVersion.doc_type == doc_type)
    if resume_id:
        q = q.filter(DocumentVersion.resume_id == resume_id)
    if job_id:
        q = q.filter(DocumentVersion.job_id == job_id)
    last = q.order_by(DocumentVersion.version.desc()).first()
    version = (last.version + 1) if last else 1

    os.makedirs(DOC_DIR, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = _safe_name(f"{doc_type}_job{job_id or 'none'}_v{version}_{stamp}", doc_type)
    path = os.path.join(DOC_DIR, f"{base}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    row = DocumentVersion(
        resume_id=resume_id,
        job_id=job_id,
        application_id=application_id,
        doc_type=doc_type,
        version=version,
        content=content,
        file_path=path,
        match_score=match_score,
        highlights=json.dumps(highlights or []),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return version_to_dict(row)


def version_to_dict(row: DocumentVersion) -> dict:
    try:
        highlights = json.loads(row.highlights or "[]")
    except (TypeError, ValueError):
        highlights = []
    return {
        "id": row.id,
        "resume_id": row.resume_id,
        "job_id": row.job_id,
        "application_id": row.application_id,
        "doc_type": row.doc_type,
        "version": row.version,
        "content": row.content or "",
        "file_path": row.file_path or "",
        "match_score": row.match_score,
        "highlights": highlights,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_versions(db: Session, resume_id: int | None = None, job_id: int | None = None,
                  doc_type: str | None = None, limit: int = 50) -> list[dict]:
    q = db.query(DocumentVersion)
    if resume_id:
        q = q.filter(DocumentVersion.resume_id == resume_id)
    if job_id:
        q = q.filter(DocumentVersion.job_id == job_id)
    if doc_type:
        q = q.filter(DocumentVersion.doc_type == doc_type)
    rows = q.order_by(DocumentVersion.id.desc()).limit(min(limit, 200)).all()
    return [version_to_dict(r) for r in rows]


def get_version(db: Session, version_id: int) -> dict | None:
    row = db.get(DocumentVersion, version_id)
    return version_to_dict(row) if row else None


def generate(db: Session, resume_id: int, job_id: int | None = None,
             application_id: int | None = None, types: list[str] | None = None) -> dict:
    types = types or ["resume", "cover_letter"]
    out: dict = {"resume_id": resume_id, "job_id": job_id, "documents": []}
    builders = {"resume": build_resume, "cover_letter": build_cover_letter}
    for doc_type in types:
        builder = builders.get(doc_type)
        if not builder:
            continue
        built = builder(db, resume_id, job_id)
        if built.get("error"):
            return {"error": built["error"]}
        saved = save_version(
            db,
            resume_id,
            doc_type,
            job_id,
            built["content"],
            built.get("match_score"),
            built.get("highlights"),
            application_id,
        )
        out["documents"].append(saved)
    out["count"] = len(out["documents"])
    out["warning"] = "Drafts only. Nothing was submitted to the employer."
    return out

"""Resume intelligence API - upload, inspect and edit the parsed resume."""
import os

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.job_discovery import resume as resume_module
from app.database.models import ResumeProfile
from app.database.session import get_db

router = APIRouter(tags=["resumes"])

ALLOWED_SUFFIXES = (".pdf", ".docx", ".txt")
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
UPLOAD_DIR = "C:/JARVIS/data/resumes"


class ResumeUpdate(BaseModel):
    extracted_skills: str | None = None
    raw_text: str | None = None


class EntryReq(BaseModel):
    title: str = ""
    organization: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    bullets: list[str] | None = None


class ResumeDetailsReq(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[str] | None = None
    summary: str = ""
    skills: list[str] | None = None
    experience: list[EntryReq] | None = None
    education: list[EntryReq] | None = None
    projects: list[EntryReq] | None = None


def _to_dict(row: ResumeProfile) -> dict:
    skills = [s.strip() for s in (row.extracted_skills or "").split(",") if s.strip()]
    text = row.raw_text or ""
    return {
        "id": row.id,
        "file_path": row.file_path,
        "skills": skills,
        "skill_count": len(skills),
        "text_preview": text[:1200],
        "text_length": len(text),
        "is_active": bool(row.is_active),
        "looks_stub": len(text) < 200,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/resumes")
async def list_resumes(db: Session = Depends(get_db)):
    rows = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).limit(25).all()
    active = next((r for r in rows if r.is_active), rows[0] if rows else None)
    for row in rows:
        if active and row.id == active.id:
            row.is_active = True
    if active is not None:
        db.commit()
    return {"resumes": [_to_dict(r) for r in rows], "active_id": active.id if active else None}


@router.post("/resumes/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    name = os.path.basename(file.filename or "resume.pdf")
    suffix = os.path.splitext(name)[1].lower()
    if suffix not in ALLOWED_SUFFIXES:
        return {"error": f"unsupported file type '{suffix}'. allowed: {', '.join(ALLOWED_SUFFIXES)}"}
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        return {"error": "file larger than 8 MB"}

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(data)

    if suffix == ".pdf":
        text = resume_module.extract_text_from_pdf(path)
    elif suffix == ".docx":
        try:
            from docx import Document  # type: ignore

            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception as exc:  # noqa: BLE001
            return {"error": f"could not read DOCX: {exc}"}
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    skills = resume_module.extract_skills(text)
    db.query(ResumeProfile).update({"is_active": False})
    row = ResumeProfile(file_path=path, raw_text=text[:20000], extracted_skills=",".join(skills),
                        is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"resume": _to_dict(row), "skills": skills, "text_len": len(text)}


@router.post("/resumes/{resume_id}/activate")
async def activate_resume(resume_id: int, db: Session = Depends(get_db)):
    row = db.get(ResumeProfile, resume_id)
    if not row:
        return {"error": "resume not found"}
    db.query(ResumeProfile).update({"is_active": False})
    row.is_active = True
    db.commit()
    db.refresh(row)
    return _to_dict(row)


@router.put("/resumes/{resume_id}/details")
async def save_resume_details(resume_id: int, req: ResumeDetailsReq, db: Session = Depends(get_db)):
    """Save the structured details the user filled in and refresh the resume text.

    The rendered plain text replaces the stored resume text, the skills list is
    replaced, and the structured sections are rebuilt so the Resume Generator
    works from exactly what the user typed.
    """
    from app.services import resume_generator

    row = db.get(ResumeProfile, resume_id)
    if not row:
        return {"error": "resume not found"}

    payload = req.model_dump()
    for key in ("experience", "education", "projects"):
        payload[key] = [e for e in (payload.get(key) or []) if e.get("title") or e.get("description")]

    text = resume_generator.render_profile_text(payload)
    skills = [str(s).strip() for s in (payload.get("skills") or []) if str(s).strip()]

    row.raw_text = text[:20000]
    row.extracted_skills = ",".join(skills)

    db.query(ResumeSection).filter(ResumeSection.resume_id == resume_id).delete()
    position = 0

    def _add(section_type: str, title: str, entry: dict) -> None:
        nonlocal position
        db.add(ResumeSection(
            resume_id=resume_id,
            section_type=section_type,
            title=title,
            organization=(entry.get("organization") or "").strip(),
            location=(entry.get("location") or "").strip(),
            start_date=(entry.get("start_date") or "").strip(),
            end_date=(entry.get("end_date") or "").strip(),
            description=(entry.get("description") or "").strip(),
            position=position,
        ))
        position += 1

    if payload.get("summary"):
        _add("summary", "Summary", {"description": payload["summary"]})
    for entry in payload.get("experience") or []:
        _add("experience", entry.get("title") or "Experience", entry)
    for entry in payload.get("projects") or []:
        _add("projects", entry.get("title") or "Project", entry)
    for entry in payload.get("education") or []:
        _add("education", entry.get("title") or "Education", entry)

    db.commit()
    db.refresh(row)
    return {"resume": _to_dict(row), "rendered_text": text, "skills": skills}


@router.get("/resumes/{resume_id}/details")
async def get_resume_details(resume_id: int, db: Session = Depends(get_db)):
    """Return the structured details of a resume for the editor form."""
    row = db.get(ResumeProfile, resume_id)
    if not row:
        return {"error": "resume not found"}
    sections = (
        db.query(ResumeSection)
        .filter(ResumeSection.resume_id == resume_id)
        .order_by(ResumeSection.position, ResumeSection.id)
        .all()
    )
    details = {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "links": [],
        "summary": "",
        "skills": [s.strip() for s in (row.extracted_skills or "").split(",") if s.strip()],
        "experience": [],
        "education": [],
        "projects": [],
    }
    for line in (row.raw_text or "").splitlines():
        stripped = line.strip()
        if "@" in stripped and not details["email"]:
            details["email"] = stripped.split("|")[0].strip()
        elif stripped.startswith("http") or "linkedin.com" in stripped or "github.com" in stripped:
            for link in stripped.split("|"):
                link = link.strip()
                if link and link not in details["links"]:
                    details["links"].append(link)
    for section in sections:
        entry = {
            "title": section.title or "",
            "organization": section.organization or "",
            "location": section.location or "",
            "start_date": section.start_date or "",
            "end_date": section.end_date or "",
            "description": section.description or "",
        }
        if section.section_type == "summary":
            details["summary"] = section.description or ""
        elif section.section_type == "experience":
            details["experience"].append(entry)
        elif section.section_type == "projects":
            details["projects"].append(entry)
        elif section.section_type == "education":
            details["education"].append(entry)
    return {"resume_id": resume_id, "details": details, "text": row.raw_text or ""}


@router.get("/resumes/{resume_id}")
async def get_resume(resume_id: int, db: Session = Depends(get_db)):
    row = db.get(ResumeProfile, resume_id)
    if not row:
        return {"error": "resume not found"}
    return _to_dict(row)


@router.put("/resumes/{resume_id}")
async def update_resume(resume_id: int, req: ResumeUpdate, db: Session = Depends(get_db)):
    row = db.get(ResumeProfile, resume_id)
    if not row:
        return {"error": "resume not found"}
    if req.extracted_skills is not None:
        skills = [s.strip() for s in req.extracted_skills.split(",") if s.strip()]
        row.extracted_skills = ",".join(skills)
    elif req.raw_text is not None:
        row.extracted_skills = ",".join(resume_module.extract_skills(req.raw_text))
    if req.raw_text is not None:
        row.raw_text = req.raw_text[:20000]
    db.commit()
    db.refresh(row)
    return _to_dict(row)


@router.delete("/resumes/{resume_id}")
async def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    row = db.get(ResumeProfile, resume_id)
    if not row:
        return {"error": "resume not found"}
    db.delete(row)
    db.commit()
    return {"id": resume_id, "deleted": True}

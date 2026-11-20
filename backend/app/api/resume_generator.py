"""Resume Generator API: paste a job description, get a targeted resume."""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.models import ResumeProfile
from app.database.session import get_db
from app.services import documents, resume_generator

router = APIRouter(tags=["resume-generator"])


class JdResumeReq(BaseModel):
    jd: str = ""
    resume_id: int | None = None
    role: str | None = None
    company: str | None = None
    polish_summary: bool = True


class SaveReq(BaseModel):
    jd: str
    resume_id: int | None = None
    role: str | None = None
    company: str | None = None
    polish_summary: bool = True
    doc_type: str = "resume"


def _active_resume(db: Session) -> ResumeProfile | None:
    row = db.query(ResumeProfile).filter(ResumeProfile.is_active.is_(True)).order_by(ResumeProfile.id.desc()).first()
    if row:
        return row
    return db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()


@router.get("/resume-generator/jd")
async def analyse_jd(jd: str):
    """Parse a job description without generating anything."""
    parsed = resume_generator.parse_jd(jd)
    parsed.pop("text", None)
    return parsed


@router.post("/resume-generator/preview")
async def preview_resume(req: JdResumeReq, db: Session = Depends(get_db)):
    """Build the targeted resume and show it without saving a version."""
    profile = db.get(ResumeProfile, req.resume_id) if req.resume_id else _active_resume(db)
    if not profile:
        return {"error": "no resume found - upload your resume first"}
    built = await resume_generator.build_resume_from_jd(
        db, profile.id, req.jd, req.role, req.company, req.polish_summary
    )
    if built.get("error"):
        return built
    return {
        "resume_id": profile.id,
        "content": built["content"],
        "analysis": built["analysis"],
        "highlights": built["highlights"],
        "coverage_pct": built["analysis"]["coverage_pct"],
    }


@router.post("/resume-generator/save")
async def save_resume(req: SaveReq, db: Session = Depends(get_db)):
    """Generate and store a numbered version you can download."""
    profile = db.get(ResumeProfile, req.resume_id) if req.resume_id else _active_resume(db)
    if not profile:
        return {"error": "no resume found - upload your resume first"}
    built = await resume_generator.build_resume_from_jd(
        db, profile.id, req.jd, req.role, req.company, req.polish_summary
    )
    if built.get("error"):
        return built
    saved = documents.save_version(
        db,
        profile.id,
        req.doc_type,
        built["job"].get("id"),
        built["content"],
        built.get("match_score"),
        built.get("highlights"),
    )
    return {
        "document": saved,
        "analysis": built["analysis"],
        "highlights": built["highlights"],
        "warning": "Draft only. Review every line before you send it.",
    }


@router.get("/resume-generator/versions")
async def generator_versions(resume_id: int | None = None, limit: int = 30,
                             db: Session = Depends(get_db)):
    return {"documents": documents.list_versions(db, resume_id, None, "resume", limit)}


@router.get("/resume-generator/{document_id}/download")
async def download(document_id: int, db: Session = Depends(get_db)):
    row = documents.get_version(db, document_id)
    if not row:
        return {"error": "document not found"}
    path = row.get("file_path") or ""
    if not path:
        return {"error": "no file for this version"}
    try:
        return FileResponse(path, media_type="text/plain", filename=path.replace("\\", "/").split("/")[-1])
    except Exception as exc:  # noqa: BLE001
        return {"error": f"could not serve file: {exc}"}

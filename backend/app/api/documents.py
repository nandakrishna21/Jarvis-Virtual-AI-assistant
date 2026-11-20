"""Resume sections and tailored document versions API."""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import documents

router = APIRouter(tags=["documents"])


class SectionReq(BaseModel):
    section_type: str = "custom"
    title: str = ""
    organization: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    position: int | None = None


class GenerateReq(BaseModel):
    resume_id: int
    job_id: int | None = None
    application_id: int | None = None
    types: list[str] | None = None


@router.get("/resumes/{resume_id}/sections")
async def list_sections(resume_id: int, db: Session = Depends(get_db)):
    return {"sections": documents.list_sections(db, resume_id)}


@router.post("/resumes/{resume_id}/sections")
async def add_section(resume_id: int, req: SectionReq, db: Session = Depends(get_db)):
    return documents.add_section(db, resume_id, req.model_dump())


@router.patch("/sections/{section_id}")
async def update_section(section_id: int, req: SectionReq, db: Session = Depends(get_db)):
    payload = req.model_dump(exclude_none=True)
    return documents.update_section(db, section_id, payload)


@router.delete("/sections/{section_id}")
async def delete_section(section_id: int, db: Session = Depends(get_db)):
    return documents.delete_section(db, section_id)


@router.post("/documents/generate")
async def generate_documents(req: GenerateReq, db: Session = Depends(get_db)):
    return documents.generate(db, req.resume_id, req.job_id, req.application_id, req.types)


@router.get("/documents")
async def list_documents(resume_id: int | None = None, job_id: int | None = None,
                         doc_type: str | None = None, limit: int = 50,
                         db: Session = Depends(get_db)):
    return {"documents": documents.list_versions(db, resume_id, job_id, doc_type, limit)}


@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: Session = Depends(get_db)):
    row = documents.get_version(db, document_id)
    if not row:
        return {"error": "document not found"}
    return row


@router.get("/documents/{document_id}/download")
async def download_document(document_id: int, db: Session = Depends(get_db)):
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

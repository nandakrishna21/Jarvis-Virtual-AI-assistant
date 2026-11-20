"""Interview tracker API."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.interview import service as interview_service
from app.database.session import get_db

router = APIRouter(tags=["interviews"])


class InterviewRequest(BaseModel):
    company: str
    role: str = ""
    interview_date: str | None = None
    interview_time: str | None = None
    mode: str = "online"
    interviewer: str = ""
    notes: str = ""
    application_id: int | None = None


class InterviewUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    interview_date: str | None = None
    interview_time: str | None = None
    mode: str | None = None
    interviewer: str | None = None
    notes: str | None = None
    status: str | None = None


@router.get("/interviews")
async def list_interviews(status: str | None = None, db: Session = Depends(get_db)):
    return {"interviews": interview_service.list_all(db, status), "stats": interview_service.stats(db)}


@router.post("/interviews")
async def create_interview(req: InterviewRequest, db: Session = Depends(get_db)):
    return interview_service.create(
        db,
        company=req.company,
        role=req.role,
        interview_date=req.interview_date,
        interview_time=req.interview_time,
        mode=req.mode,
        interviewer=req.interviewer,
        notes=req.notes,
        application_id=req.application_id,
    )


@router.patch("/interviews/{interview_id}")
async def update_interview(interview_id: int, req: InterviewUpdate, db: Session = Depends(get_db)):
    return interview_service.update(db, interview_id, **req.model_dump(exclude_none=True))


@router.delete("/interviews/{interview_id}")
async def delete_interview(interview_id: int, db: Session = Depends(get_db)):
    return interview_service.delete(db, interview_id)

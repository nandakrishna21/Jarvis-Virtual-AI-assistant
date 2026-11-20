"""User profile and preferences API."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import profile as profile_service

router = APIRouter(tags=["profile"])


class Preferences(BaseModel):
    name: str | None = None
    location: str | None = None
    markets: list[str] | None = None
    target_categories: list[str] | None = None
    salary: str | None = None
    employment_types: list[str] | None = None
    work_modes: list[str] | None = None
    experience_levels: list[str] | None = None
    search_interval_minutes: int | None = None
    resume_path: str | None = None


@router.get("/profile")
async def get_profile(db: Session = Depends(get_db)):
    return profile_service.get_preferences(db)


@router.put("/profile")
async def put_profile(req: Preferences, db: Session = Depends(get_db)):
    return profile_service.update_preferences(db, req.model_dump(exclude_none=True))

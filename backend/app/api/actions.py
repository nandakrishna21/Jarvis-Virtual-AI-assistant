"""Approval-first action API.

These endpoints are the only way a proposed action can be executed.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import proposals
from app.services import action_handlers  # noqa: F401 - registers the handlers

router = APIRouter(tags=["actions"])


@router.get("/actions")
async def list_actions(status: str | None = None, db: Session = Depends(get_db)):
    return {
        "actions": proposals.list_proposals(db, status),
        "pending": proposals.pending_count(db),
        "available": proposals.registered_actions(),
    }


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: int, db: Session = Depends(get_db)):
    return await proposals.approve(db, action_id)


@router.post("/actions/{action_id}/reject")
async def reject_action(action_id: int, note: str = "", db: Session = Depends(get_db)):
    return proposals.reject(db, action_id, note)

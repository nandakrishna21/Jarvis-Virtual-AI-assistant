"""Notification service API."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.models import Notification
from app.database.session import get_db
from app.services.notifications import notify, notify_safe

router = APIRouter(tags=["notifications"])

__all__ = ["router", "notify", "notify_safe"]


@router.get("/notifications")
async def list_notifications(unread_only: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(Notification)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    rows = q.order_by(Notification.id.desc()).limit(min(limit, 100)).all()
    return {
        "notifications": [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "body": r.body,
                "link": r.link,
                "is_read": r.is_read,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "unread": db.query(Notification).filter(Notification.is_read.is_(False)).count(),
    }


@router.patch("/notifications/{notification_id}/read")
async def mark_read(notification_id: int, db: Session = Depends(get_db)):
    row = db.get(Notification, notification_id)
    if not row:
        return {"error": "notification not found"}
    row.is_read = True
    db.commit()
    return {"id": notification_id, "is_read": True}


@router.post("/notifications/read-all")
async def mark_all_read(db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"marked": n}

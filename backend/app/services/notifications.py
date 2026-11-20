"""Notification emission.

Key events raise a local notification row so the Command Center can show
something happened without you having to poll every page.

Notifications are read-only local records - they never trigger an external
action and never contain secrets or message bodies.
"""
import logging

from sqlalchemy.orm import Session

from app.database.models import Notification

logger = logging.getLogger("jarvis.notifications")

KINDS = ("info", "success", "warning", "error")


def notify(db: Session, title: str, body: str = "", kind: str = "info", link: str = "") -> int:
    if kind not in KINDS:
        kind = "info"
    try:
        row = Notification(kind=kind, title=title[:200], body=(body or "")[:2000], link=link or "")
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info("notification: %s (%s)", title, kind)
        return row.id
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not write notification: %s", exc)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return 0


def notify_safe(db: Session, title: str, body: str = "", kind: str = "info", link: str = "") -> int:
    """notify() that never raises and never breaks the calling flow."""
    try:
        return notify(db, title, body, kind, link)
    except Exception as exc:  # noqa: BLE001
        logger.warning("notification failed: %s", exc)
        return 0

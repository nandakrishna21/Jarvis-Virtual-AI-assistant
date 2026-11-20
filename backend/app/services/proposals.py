"""Approval-first action layer.

Every mutating or external action JARVIS wants to perform becomes an
ActionProposal. The proposal is stored with a SHA-256 hash of its payload and
stays pending until the user explicitly approves it. Only then is the handler
executed. This is the single choke point that keeps JARVIS from acting on its
own.
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Awaitable, Callable

from sqlalchemy.orm import Session

from app.database.models import ActionProposal, AgentRun

logger = logging.getLogger("jarvis.proposals")

Handler = Callable[[dict, Session], Awaitable[dict]]
_HANDLERS: dict[str, Handler] = {}


def handler(action_type: str):
    def register(fn: Handler) -> Handler:
        _HANDLERS[action_type] = fn
        return fn
    return register


def hash_payload(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def create_proposal(
    db: Session,
    action_type: str,
    title: str,
    reason: str = "",
    plan: list[str] | None = None,
    payload: dict | None = None,
    source: str = "chat",
) -> dict:
    payload = payload or {}
    row = ActionProposal(
        action_type=action_type,
        title=title,
        reason=reason,
        plan=json.dumps(plan or [], default=str),
        payload=json.dumps(payload, default=str),
        payload_hash=hash_payload(payload),
        status="pending",
        source=source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("proposal created #%s %s", row.id, action_type)
    _notify(db, f"Approval needed: {title}", reason or "", "warning", "/applications")
    return to_dict(row)


def _notify(db: Session, title: str, body: str, kind: str, link: str = "") -> None:
    from app.services.notifications import notify_safe

    notify_safe(db, title, body, kind, link)


def get_proposal(db: Session, proposal_id: int) -> ActionProposal | None:
    return db.get(ActionProposal, proposal_id)


def list_proposals(db: Session, status: str | None = None, limit: int = 50) -> list[dict]:
    q = db.query(ActionProposal)
    if status:
        q = q.filter(ActionProposal.status == status)
    rows = q.order_by(ActionProposal.id.desc()).limit(limit).all()
    return [to_dict(r) for r in rows]


def pending_count(db: Session) -> int:
    return db.query(ActionProposal).filter(ActionProposal.status == "pending").count()


def to_dict(row: ActionProposal) -> dict:
    def loads(value, fallback):
        if not value:
            return fallback
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return fallback

    return {
        "id": row.id,
        "action_type": row.action_type,
        "title": row.title,
        "reason": row.reason or "",
        "plan": loads(row.plan, []),
        "payload": loads(row.payload, {}),
        "status": row.status,
        "source": row.source,
        "result": loads(row.result, None),
        "error": row.error,
        "payload_hash": row.payload_hash,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "executed_at": row.executed_at.isoformat() if row.executed_at else None,
    }


async def approve(db: Session, proposal_id: int) -> dict:
    row = get_proposal(db, proposal_id)
    if not row:
        return {"ok": False, "error": "proposal not found"}
    if row.status != "pending":
        return {"ok": False, "error": f"proposal already {row.status}", "proposal": to_dict(row)}

    fn = _HANDLERS.get(row.action_type)
    if not fn:
        row.status = "failed"
        row.error = f"no handler for action '{row.action_type}'"
        row.decided_at = datetime.utcnow()
        db.commit()
        _notify(db, f"Failed: {row.title}", row.error, "error", "/applications")
        return {"ok": False, "error": row.error, "proposal": to_dict(row)}

    payload = json.loads(row.payload or "{}")
    row.status = "approved"
    row.decided_at = datetime.utcnow()
    db.commit()

    started = datetime.utcnow()
    try:
        result = await fn(payload, db)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, never swallowed
        logger.exception("proposal %s execution failed", proposal_id)
        row.status = "failed"
        row.error = str(exc)
        row.executed_at = datetime.utcnow()
        db.add(
            AgentRun(
                agent="approval",
                action=row.action_type,
                status="failed",
                detail=str(exc)[:500],
                duration_ms=int((datetime.utcnow() - started).total_seconds() * 1000),
            )
        )
        db.commit()
        _notify(db, f"Failed: {row.title}", str(exc)[:300], "error", "/applications")
        return {"ok": False, "error": str(exc), "proposal": to_dict(row)}

    row.status = "executed"
    row.result = json.dumps(result, default=str)
    row.executed_at = datetime.utcnow()
    db.add(
        AgentRun(
            agent="approval",
            action=row.action_type,
            status="success",
            detail=row.title[:500],
            duration_ms=int((datetime.utcnow() - started).total_seconds() * 1000),
        )
    )
    db.commit()
    _notify(db, f"Completed: {row.title}", str(result.get("message", ""))[:300], "success", "/applications")
    return {"ok": True, "result": result, "proposal": to_dict(row)}


def reject(db: Session, proposal_id: int, note: str = "") -> dict:
    row = get_proposal(db, proposal_id)
    if not row:
        return {"ok": False, "error": "proposal not found"}
    if row.status != "pending":
        return {"ok": False, "error": f"proposal already {row.status}", "proposal": to_dict(row)}
    row.status = "rejected"
    row.error = note or "rejected by user"
    row.decided_at = datetime.utcnow()
    db.commit()
    logger.info("proposal %s rejected", proposal_id)
    _notify(db, f"Rejected: {row.title}", note or "You rejected this action.", "info", "/applications")
    return {"ok": True, "status": "rejected", "proposal": to_dict(row)}


def registered_actions() -> list[str]:
    return sorted(_HANDLERS)

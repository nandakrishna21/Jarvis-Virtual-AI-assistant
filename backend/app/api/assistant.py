"""Assistant API: greeting on open, command handling and history."""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import AgentRun, Application, Interview, Job, JobMatch
from app.services import profile as profile_service
from app.services import proposals
from app.orchestrator.router import handle

router = APIRouter(tags=["assistant"])

QUICK_COMMANDS = [
    {"label": "Find jobs for me", "command": "Find Python backend jobs in India"},
    {"label": "Analyze my resume", "command": "Analyze my resume"},
    {"label": "Search Python jobs", "command": "Search Python jobs in Hyderabad"},
    {"label": "Find AI engineering jobs", "command": "Find remote AI engineering jobs"},
    {"label": "Jobs above 80% match", "command": "Show jobs above 80 percent match"},
    {"label": "Prepare my applications", "command": "Prepare applications for my top matched jobs"},
    {"label": "Pending approvals", "command": "Show pending approvals"},
    {"label": "Today's report", "command": "Generate today's report"},
]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 5:
        return "Working late"
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    if hour < 21:
        return "Good evening"
    return "Good night"


@router.get("/assistant/greeting")
def greeting(db: Session = Depends(get_db)):
    prefs = profile_service.get_preferences(db)
    pending = proposals.pending_count(db)
    jobs = db.query(Job).count()
    matches = db.query(JobMatch).count()
    high = db.query(JobMatch).filter(JobMatch.score >= 80).count()
    apps = db.query(Application).count()
    submitted = db.query(Application).filter(Application.status.in_(["Applied", "Interview", "Offer"])).count()
    prepared = db.query(Application).filter(Application.status.in_(["Ready for approval", "Approved"])).count()
    interviews = db.query(Interview).filter(Interview.status == "scheduled").count()

    first = (prefs.get("name") or "there").split()[0]
    return {
        "greeting": f"{_greeting()}, {first}",
        "message": (
            f"{_greeting()}, {first}. I am JARVIS, your local job-search assistant. "
            "Tell me what you need and I will show you exactly what I plan to do "
            "before anything happens."
        ),
        "name": prefs.get("name"),
        "location": prefs.get("location"),
        "pending_approvals": pending,
        "stats": {
            "jobs_discovered": jobs,
            "high_match": high,
            "matches": matches,
            "applications_prepared": prepared,
            "applications_submitted": submitted,
            "interviews_scheduled": interviews,
        },
        "quick_commands": QUICK_COMMANDS,
    }


@router.post("/assistant/chat")
async def assistant_chat(req: ChatRequest, db: Session = Depends(get_db)):
    return await handle(req.message, db)


@router.post("/assistant/command")
async def assistant_command(req: ChatRequest, db: Session = Depends(get_db)):
    return await handle(req.message, db)


@router.get("/assistant/history")
def assistant_history(limit: int = 40, db: Session = Depends(get_db)):
    rows = db.query(AgentRun).order_by(AgentRun.id.desc()).limit(limit).all()
    return {
        "history": [
            {
                "id": r.id,
                "agent": r.agent,
                "action": r.action,
                "status": r.status,
                "detail": (r.detail or "")[:400],
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }

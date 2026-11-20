"""Automation Center API backed by n8n."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.automation import service as automation_service
from app.database.session import get_db
from app.scheduler import scheduler
from app.services import proposals

router = APIRouter(tags=["automation"])


class RunRequest(BaseModel):
    workflow: str
    payload: dict = {}


@router.get("/automation")
async def automation_overview(db: Session = Depends(get_db)):
    data = automation_service.overview(db)
    data["n8n"] = await automation_service.n8n_status()
    data["scheduler"] = scheduler.status()
    return data


@router.post("/automation/run")
async def run_workflow(req: RunRequest, db: Session = Depends(get_db)):
    # require approval before running
    from app.agents.automation import catalog
    wf = catalog.get(req.workflow)
    if not wf:
        return {"ok": False, "error": f"unknown workflow '{req.workflow}'"}
    proposal = proposals.create_proposal(
        db,
        action_type="run_workflow",
        title=f"Run automation: {wf['title']}",
        reason="Automation run requested from API.",
        plan=wf["steps"],
        payload={"workflow": req.workflow, "payload": req.payload},
        source="automation_api",
    )
    return {"ok": True, "requires_approval": True, "proposal": proposal}


@router.get("/automation/logs")
async def automation_logs(limit: int = 30, db: Session = Depends(get_db)):
    return {"runs": automation_service.list_runs(db, limit), "scheduler": scheduler.status()}


@router.get("/automation/n8n")
async def n8n_status():
    return await automation_service.n8n_status()


@router.post("/automation/start")
async def automation_start():
    return scheduler.start()


@router.post("/automation/stop")
async def automation_stop():
    return scheduler.stop()


@router.post("/automation/pause")
async def automation_pause():
    return scheduler.pause()


@router.post("/automation/resume")
async def automation_resume():
    return scheduler.resume()

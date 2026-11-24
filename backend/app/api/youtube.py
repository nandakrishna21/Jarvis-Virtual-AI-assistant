from __future__ import annotations
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from app.services import youtube

router = APIRouter(tags=["youtube"])

class DownloadReq(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
    mode: str = Field(default="video")

@router.get("/youtube/probe")
async def youtube_probe(url: str = Query(min_length=8)):
    return youtube.probe(url)

@router.post("/youtube/download")
async def youtube_download(req: DownloadReq):
    mode = "audio" if req.mode == "audio" else "video"
    return youtube.start_download(req.url, mode=mode)

@router.get("/youtube/jobs")
async def youtube_jobs():
    return {"jobs": youtube.list_jobs()}

@router.get("/youtube/jobs/{job_id}")
async def youtube_job(job_id: str):
    job = youtube.get_job(job_id)
    return job or {"error": "not found"}

@router.get("/youtube/jobs/{job_id}/file")
async def youtube_job_file(job_id: str):
    job = youtube.get_job(job_id)
    if not job or not job.get("filepath"):
        return {"error": "file not ready"}
    p = Path(job["filepath"])
    if not p.exists():
        return {"error": "file missing"}
    return FileResponse(str(p), filename=p.name)

from __future__ import annotations
import json, os, re, subprocess, threading, time, uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "downloads" / "youtube"
DATA_DIR.mkdir(parents=True, exist_ok=True)
YTDLP = Path(__file__).resolve().parents[3] / "backend" / "scripts" / "yt-dlp.exe"
JOBS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()

def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE).strip(" ._")
    return name[:120] or "video"

def _job_public(j: dict) -> dict:
    return {k: j[k] for k in ["id","url","kind","status","title","progress","speed","eta","filename","filepath","error","created_at","updated_at","items","downloaded","total"] if k in j}

def list_jobs() -> list[dict]:
    with LOCK:
        return [_job_public(j) for j in sorted(JOBS.values(), key=lambda x: x.get("created_at",0), reverse=True)]

def get_job(job_id: str) -> dict | None:
    with LOCK:
        j = JOBS.get(job_id)
        return _job_public(j) if j else None

def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=600)

def probe(url: str) -> dict:
    if not YTDLP.exists():
        return {"ok": False, "error": "yt-dlp.exe not found. Place it in backend/scripts/yt-dlp.exe."}
    cmd = [str(YTDLP), "--dump-single-json", "--flat-playlist", "--no-warnings", url]
    p = _run(cmd)
    if p.returncode != 0:
        return {"ok": False, "error": (p.stderr or p.stdout or "probe failed")[-500:]}
    try:
        data = json.loads(p.stdout)
    except Exception as e:
        return {"ok": False, "error": f"Invalid yt-dlp output: {e}"}
    entries = data.get("entries") or []
    is_playlist = bool(entries) or data.get("_type") in {"playlist","multi_video"}
    items = []
    for e in entries[:200]:
        if not e: continue
        items.append({"id": e.get("id"), "title": e.get("title"), "url": e.get("url") or e.get("webpage_url") or (f"https://www.youtube.com/watch?v={e.get('id')}" if e.get('id') else None), "duration": e.get("duration")})
    return {"ok": True, "title": data.get("title") or data.get("id") or url, "is_playlist": is_playlist, "count": len(items) if is_playlist else 1, "items": items, "uploader": data.get("uploader") or data.get("channel"), "webpage_url": data.get("webpage_url") or url}

def _progress_hook(job_id: str, line: str):
    with LOCK:
        j = JOBS.get(job_id)
        if not j: return
        j["updated_at"] = time.time()
        m = re.search(r"(\d+(?:\.\d+)?)%", line)
        if m: j["progress"] = float(m.group(1))
        m = re.search(r"at\s+([^\s]+/s)", line)
        if m: j["speed"] = m.group(1)
        m = re.search(r"ETA\s+([^\s]+)", line)
        if m: j["eta"] = m.group(1)
        if "Destination:" in line:
            j["filename"] = line.split("Destination:",1)[1].strip().split("\\")[-1].split("/")[-1]
        if "has already been downloaded" in line and j.get("filename") is None:
            j["filename"] = line.strip()[:200]

def _download_worker(job_id: str, url: str, mode: str):
    job_dir = DATA_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(job_dir / "%(title).120s [%(id)s].%(ext)s")
    cmd = [str(YTDLP), "--newline", "--no-warnings", "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best", "--merge-output-format", "mp4", "-o", out_tpl]
    if mode == "audio":
        cmd = [str(YTDLP), "--newline", "--no-warnings", "-x", "--audio-format", "mp3", "-o", out_tpl]
    cmd.append(url)
    with LOCK:
        j = JOBS[job_id]; j["status"] = "running"; j["updated_at"] = time.time(); j["command"] = cmd
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        with LOCK: JOBS[job_id]["pid"] = proc.pid
        for line in proc.stdout or []:
            line = line.rstrip()
            _progress_hook(job_id, line)
            if "[download] Downloading item" in line:
                m = re.search(r"Downloading item (\d+) of (\d+)", line)
                if m:
                    with LOCK:
                        JOBS[job_id]["downloaded"] = int(m.group(1))-1
                        JOBS[job_id]["total"] = int(m.group(2))
        rc = proc.wait(timeout=3600)
        files = sorted([p for p in job_dir.glob("*") if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
        with LOCK:
            j = JOBS[job_id]
            j["status"] = "completed" if rc == 0 else "failed"
            j["progress"] = 100.0 if rc == 0 else j.get("progress",0)
            j["updated_at"] = time.time()
            if files:
                j["filepath"] = str(files[0])
                j["filename"] = files[0].name
                j["files"] = [p.name for p in files[:50]]
            if rc != 0 and not j.get("error"):
                j["error"] = f"yt-dlp exited with code {rc}"
    except Exception as e:
        with LOCK:
            j = JOBS[job_id]; j["status"]="failed"; j["error"]=str(e); j["updated_at"]=time.time()

def start_download(url: str, mode: str = "video") -> dict:
    if not YTDLP.exists():
        return {"ok": False, "error": "yt-dlp.exe missing in backend/scripts/yt-dlp.exe"}
    if not re.match(r"^https?://", url):
        return {"ok": False, "error": "Invalid URL"}
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "url": url, "kind": mode, "status": "queued", "title": url, "progress": 0.0, "speed": "", "eta": "", "filename": None, "filepath": None, "error": None, "created_at": time.time(), "updated_at": time.time(), "downloaded": 0, "total": 0, "files": []}
    with LOCK: JOBS[job_id] = job
    t = threading.Thread(target=_download_worker, args=(job_id, url, mode), daemon=True)
    t.start()
    return {"ok": True, "job": _job_public(job)}

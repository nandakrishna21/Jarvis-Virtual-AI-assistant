from pathlib import Path
from fastapi import APIRouter
import shutil, subprocess

router = APIRouter(tags=["openjarvis"])
ROOT = Path(__file__).resolve().parents[3]
OJ = ROOT / "external" / "OpenJarvis"


def _has(extra: str, pyproject: str) -> bool:
    return f"{extra} =" in pyproject or f"{extra}=" in pyproject


@router.get("/openjarvis/status")
async def openjarvis_status():
    exists = OJ.exists()
    pyproject_path = OJ / "pyproject.toml"
    pyproject = pyproject_path.exists()
    uv = shutil.which("uv")
    version = None
    extras = []
    if pyproject:
        text = pyproject_path.read_text(encoding="utf-8", errors="ignore")
        for e in ["dev","server","desktop","tools-search","memory-bm25","memory-pdf","browser","memory-faiss","inference-cloud","channel-telegram","sandbox-docker","learning-dspy"]:
            if _has(e, text):
                extras.append(e)
    installed_extras = []
    try:
        lock = (OJ / "uv.lock").read_text(encoding="utf-8", errors="ignore") if (OJ / "uv.lock").exists() else ""
        for e in ["server","desktop","tools-search","memory-bm25","memory-pdf","browser","dev"]:
            marker = {"server":"fastapi","desktop":"faster-whisper","tools-search":"tavily-python","memory-bm25":"rank-bm25","memory-pdf":"pdfplumber","browser":"playwright","dev":"pytest"}.get(e,e)
            if marker in lock:
                installed_extras.append(e)
    except Exception:
        pass
    if exists and uv:
        try:
            r = subprocess.run([uv, "run", "jarvis", "--version"], cwd=str(OJ), capture_output=True, text=True, timeout=30)
            out = (r.stdout or r.stderr).strip()
            version = out.splitlines()[-1] if out else None
        except Exception:
            version = None
    return {
        "installed": exists and pyproject,
        "path": str(OJ),
        "submodule": (ROOT / ".gitmodules").exists(),
        "uv_available": bool(uv),
        "jarvis_version": version,
        "extras_available": extras,
        "extras_installed_hint": installed_extras,
        "setup_command": "powershell -ExecutionPolicy Bypass -File scripts/openjarvis_setup.ps1",
        "run_command": "powershell -ExecutionPolicy Bypass -File scripts/openjarvis_run.ps1 -- doctor",
        "docs": "https://open-jarvis.github.io/OpenJarvis/",
        "approval_required": True,
    }

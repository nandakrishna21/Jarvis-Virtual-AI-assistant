from pathlib import Path
from fastapi import APIRouter
import shutil, subprocess, os

router = APIRouter(tags=["openjarvis"])
ROOT = Path(__file__).resolve().parents[3]
OJ = ROOT / "external" / "OpenJarvis"

@router.get("/openjarvis/status")
async def openjarvis_status():
    exists = OJ.exists()
    pyproject = (OJ / "pyproject.toml").exists()
    uv = shutil.which("uv")
    version = None
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
        "setup_command": "powershell -ExecutionPolicy Bypass -File scripts/openjarvis_setup.ps1",
        "run_command": "powershell -ExecutionPolicy Bypass -File scripts/openjarvis_run.ps1 -- doctor",
        "docs": "https://open-jarvis.github.io/OpenJarvis/",
    }

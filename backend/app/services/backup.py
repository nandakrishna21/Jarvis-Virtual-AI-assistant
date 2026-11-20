import os, shutil, sqlite3, datetime
from pathlib import Path

BACKUP_DIR = Path(os.environ.get("JARVIS_BACKUP_DIR", r"C:\JARVIS\data\backups"))
DB_PATH = Path(os.environ.get("JARVIS_DB_PATH", r"C:\JARVIS\backend\jarvis.db"))
MAX_BACKUPS = 20


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def create_backup(label: str = "") -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        return {"error": f"database not found at {DB_PATH}"}
    name = f"jarvis_{_timestamp()}{('_' + label) if label else ''}.db"
    target = BACKUP_DIR / name
    try:
        conn = sqlite3.connect(str(DB_PATH))
        dest = sqlite3.connect(str(target))
        with dest:
            conn.backup(dest)
        dest.close()
        conn.close()
    except sqlite3.Error as e:
        return {"error": f"sqlite backup failed: {e}"}
    _prune()
    return {"ok": True, "file": str(target), "name": name, "size": target.stat().st_size,
            "created": datetime.datetime.now().isoformat(timespec="seconds")}


def list_backups() -> list[dict]:
    if not BACKUP_DIR.exists():
        return []
    out = []
    for p in sorted(BACKUP_DIR.glob("jarvis_*.db"), reverse=True):
        out.append({"name": p.name, "path": str(p), "size": p.stat().st_size,
                    "created": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
    return out


def restore_backup(name: str, keep_safety_copy: bool = True) -> dict:
    source = BACKUP_DIR / name
    if not source.exists():
        return {"error": f"backup not found: {name}"}
    if not source.name.startswith("jarvis_") or source.suffix != ".db":
        return {"error": "refusing to restore a file that is not a JARVIS backup"}
    safety = None
    if keep_safety_copy and DB_PATH.exists():
        safety = create_backup("before_restore")
    try:
        conn = sqlite3.connect(str(source))
        check = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if not check or check[0] != "ok":
            return {"error": "backup file is corrupt", "integrity": check}
        shutil.copy2(source, DB_PATH)
    except Exception as e:
        return {"error": str(e)}
    return {"ok": True, "restored": name, "db": str(DB_PATH), "safety_copy": safety}


def _prune() -> None:
    files = sorted(BACKUP_DIR.glob("jarvis_*.db"), reverse=True)
    for old in files[MAX_BACKUPS:]:
        try:
            old.unlink()
        except OSError:
            pass

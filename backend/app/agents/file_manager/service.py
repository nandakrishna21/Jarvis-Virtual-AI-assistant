import os, re
from pathlib import Path

ALLOWED_ROOT = Path(os.environ.get("JARVIS_FILE_ROOT", r"C:\JARVIS")).resolve()
MAX_FILE_BYTES = 2_000_000
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".txt", ".html", ".css",
            ".yml", ".yaml", ".toml", ".ini", ".cfg", ".sql", ".env.example", ".gitignore"}

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b", r"\brmdir\s+/s\b", r"\bformat\s+[a-z]:", r"\bdel\s+/[fsq]\b",
    r"\bRemove-Item\b.*-Recurse", r"\bDROP\s+(TABLE|DATABASE)\b", r"\bTRUNCATE\s+TABLE\b",
    r"\bgit\s+push\s+--force\b", r"\bgit\s+reset\s+--hard\b", r"\bshutdown\b", r"\bdel\s+/f\b",
]

def is_safe_path(path: str) -> bool:
    try:
        p = Path(path).resolve()
    except Exception:
        return False
    try:
        p.relative_to(ALLOWED_ROOT)
        return True
    except ValueError:
        return False

def list_files(subdir: str = "", limit: int = 200) -> dict:
    base = (ALLOWED_ROOT / subdir).resolve() if subdir else ALLOWED_ROOT
    if not is_safe_path(str(base)):
        return {"error": "path outside allowed root", "allowed_root": str(ALLOWED_ROOT)}
    if not base.exists():
        return {"error": "path not found", "path": str(base)}
    out = []
    for p in sorted(base.rglob("*")):
        if len(out) >= limit:
            break
        if any(part in {".venv", "node_modules", ".git", "__pycache__", "site-packages"} for part in p.parts):
            continue
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        out.append({"path": str(p.relative_to(ALLOWED_ROOT)), "is_dir": p.is_dir(), "size": size})
    return {"root": str(ALLOWED_ROOT), "count": len(out), "files": out}

def read_text(path: str) -> dict:
    if not is_safe_path(path):
        return {"error": "path outside allowed root", "allowed_root": str(ALLOWED_ROOT)}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {"error": "file not found", "path": str(p)}
    if p.stat().st_size > MAX_FILE_BYTES:
        return {"error": "file too large", "size": p.stat().st_size, "max": MAX_FILE_BYTES}
    if p.suffix.lower() not in TEXT_EXT and p.name not in {".gitignore", "Dockerfile"}:
        return {"error": "unsupported file type for text analysis", "suffix": p.suffix}
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"error": str(e)}
    return {"path": str(p), "size": p.stat().st_size, "lines": text.count("\n") + 1,
            "content": text[:200000]}

def read_pdf(path: str) -> dict:
    if not is_safe_path(path):
        return {"error": "path outside allowed root", "allowed_root": str(ALLOWED_ROOT)}
    p = Path(path)
    if not p.exists():
        return {"error": "file not found"}
    if p.stat().st_size > MAX_FILE_BYTES * 5:
        return {"error": "pdf too large"}
    try:
        from pypdf import PdfReader
        r = PdfReader(str(p))
        pages = len(r.pages)
        text = "\n".join((pg.extract_text() or "") for pg in r.pages[:100])
        return {"path": str(p), "pages": pages, "text": text[:200000]}
    except Exception as e:
        return {"error": str(e)}

def find_dangerous(text: str) -> list[str]:
    hits = []
    for pat in DANGEROUS_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            line = text[:m.start()].count("\n") + 1
            hits.append({"pattern": pat, "line": line, "text": m.group(0)})
    return hits

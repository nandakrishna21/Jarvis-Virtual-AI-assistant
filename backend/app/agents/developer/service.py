import os, re, ast
from pathlib import Path
from app.agents.file_manager import service as file_service

CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx"}

def detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
            ".jsx": "javascript"}.get(ext, ext.lstrip(".") or "text")

def analyze_code(text: str, path: str = "") -> dict:
    lang = detect_language(path) if path else "python"
    result = {"language": lang, "lines": text.count("\n") + 1, "functions": [], "classes": [],
              "imports": [], "issues": []}
    if lang == "python":
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result["functions"].append({"name": node.name, "line": node.lineno})
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append({"name": node.name, "line": node.lineno})
                elif isinstance(node, ast.Import):
                    result["imports"] += [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    result["imports"].append(node.module)
        except SyntaxError as e:
            result["issues"].append({"type": "syntax_error", "line": e.lineno, "message": e.msg})
        for i, line in enumerate(text.splitlines(), 1):
            if len(line) > 120:
                result["issues"].append({"type": "long_line", "line": i, "message": "line longer than 120 chars"})
            if re.search(r"\beval\s*\(|\bexec\s*\(", line):
                result["issues"].append({"type": "dangerous_call", "line": i, "message": "eval/exec usage"})
            if "TODO" in line or "FIXME" in line:
                result["issues"].append({"type": "todo", "line": i, "message": line.strip()[:120]})
    else:
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"\beval\s*\(|new Function\s*\(", line):
                result["issues"].append({"type": "dangerous_call", "line": i, "message": "eval usage"})
    result["dangerous_commands"] = file_service.find_dangerous(text)
    return result

def summarize_project(root: str | None = None) -> dict:
    listing = file_service.list_files(root or "")
    if "error" in listing:
        return listing
    files = listing["files"]
    code_files = [f for f in files if Path(f["path"]).suffix.lower() in CODE_EXT]
    total_lines = 0
    for f in code_files[:200]:
        data = file_service.read_text(str(Path(file_service.ALLOWED_ROOT) / f["path"]))
        if "content" in data:
            total_lines += data["lines"]
    return {"root": listing["root"], "total_files": listing["count"], "code_files": len(code_files),
            "approx_code_lines": total_lines,
            "top_level": sorted({str(Path(f["path"]).parts[0]) for f in files})[:30]}

async def explain_code(text: str, path: str = "") -> dict:
    from app.services.ollama import chat
    analysis = analyze_code(text, path)
    prompt = (
        "Explain this code for a Python beginner. Structure: 1) What it does (2-3 sentences), "
        "2) Key functions/classes and their roles, 3) Any issues or risks, 4) One suggestion to improve it. "
        "Be concise and do not invent behaviour that is not in the code.\n\n"
        f"File: {path}\nLanguage: {analysis['language']}\n\nCode:\n{text[:12000]}"
    )
    res = await chat(prompt)
    return {"analysis": analysis, "explanation": res}

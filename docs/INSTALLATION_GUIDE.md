# JARVIS Installation Guide

## What it does
Local JARVIS backend (FastAPI + SQLite + Ollama) running on 127.0.0.1:8000.

## Why required
Foundation for all agents. Single orchestrator, single DB, single model service.

## System found (Phase 1 inspection)
- Python 3.11.5, Node v24.18.0, npm 11.16.0, Git 2.54, OpenCode 1.18.4
- CPU: Intel i5-1035G1 (4c/8t), RAM 8GB (not 16GB), Disk C: 153GB free
- Ollama: installed in Phase 6 via winget → version 0.40.15

## Install missing
1. Ollama (already installed):
   ```powershell
   winget install --id Ollama.Ollama --exact
   ollama --version
   ```
2. Pull models:
   ```powershell
   ollama pull qwen3:4b     # stronger, ~2.5 GB, but SLOW on 8GB RAM CPU-only
   ollama pull qwen3:1.7b   # default for this laptop, ~1.2 GB, ~8 tok/s
   ```
   Measured on this laptop: qwen3:4b = 2.3 tok/s (180 s for one sentence); qwen3:1.7b with thinking off = 8.19 tok/s.
   Default is `qwen3:1.7b`. To use the bigger model, set `OLLAMA_MODEL=qwen3:4b` in `backend/.env`.
3. Optional coder model: `ollama pull qwen2.5-coder:1.5b` (add later when the Developer Agent needs it).

## Backend setup (already done in Phase 1)
```powershell
cd C:\JARVIS\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

## Verify
```powershell
curl http://127.0.0.1:8000/health
# {"status":"ok","app":"JARVIS"}
curl http://127.0.0.1:8000/system/status
# shows ollama.models, active model, loaded models, CPU and RAM
```

## Common errors
- `ollama: command not found` → restart PowerShell after install
- Port in use → change --port or kill process
- Slow model → switch OLLAMA_MODEL to smaller model in .env
- Model stays in RAM too long → it auto-unloads after 2 minutes idle; force it with `curl -X POST http://127.0.0.1:8000/system/unload-model`
- RAM near 95% → close memory-heavy apps, or use `qwen3:1.7b` (default)

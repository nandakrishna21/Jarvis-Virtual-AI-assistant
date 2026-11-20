# Performance Guide

## What it measures
How much CPU, RAM and disk JARVIS uses on your laptop, and how to keep it small.

## Why
Your laptop has **8 GB RAM** (not 16) and **no GPU**. The whole design exists so JARVIS never makes the machine slow.

## Measured results (this laptop, 2026-11-09)

| Metric | Value |
|---|---|
| Backend process RAM (idle) | **26 MB** |
| Ollama model RAM (loaded) | ~1.2 GB for `qwen3:1.7b`, ~2.9 GB for `qwen3:4b` |
| Light endpoint average | 1.3 s |
| Light endpoint max | 4.2 s (first call, includes connection setup) |
| `qwen3:1.7b` speed (warm) | 8.19 tok/s |
| `qwen3:4b` speed | 2.29 tok/s - too slow for this machine |
| Whisper `tiny` transcription | ~6 s for a 3 s clip |
| Whisper model disk | 75 MB |
| Log file | rotates at 1 MB, 3 backups kept |
| Backups kept | newest 20 in `data/backups` |

**Note on your RAM:** the whole system showed 91.7% RAM used (0.65 GB free) while JARVIS itself used only 26 MB. The heavy users were Chrome (~1.6 GB across processes), OpenCode (~780 MB) and Windows Memory Compression (~964 MB). Close unused browser tabs before running long AI tasks.

## The limits JARVIS enforces

| Limit | Value | Where |
|---|---|---|
| Concurrent AI jobs | 1 | `asyncio.Semaphore` in `services/ollama.py` |
| Model unload after idle | 2 minutes | `keep_alive` in Ollama requests |
| Model thinking mode | off | `OLLAMA_THINK=false` (3x faster, cleaner answers) |
| Context window | 2048 tokens | `OLLAMA_NUM_CTX` |
| Web collection tasks | sequential per source | async client, no parallel storms |
| Browser automation | none | JARVIS never launches a browser |
| File read size | 2 MB (10 MB for PDF) | `file_manager/service.py` |
| Listings | 200 files max per request | `list_files` |
| Background polling | only when a schedule is enabled | scheduler defaults to paused |

## Verify the concurrency limit
```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\concurrency_test.py
```
Result: 4 simultaneous requests are **serialised** (47 s total, each finishing later than the last) - proving only one AI job runs at a time.

## Measure everything
```powershell
.\.venv\Scripts\python scripts\performance_test.py
```
Writes `C:\JARVIS\data\reports\performance_report.json` with per-endpoint latency, backend RAM and system RAM.

## Watch it live
- Dashboard header: CPU %, RAM %, free RAM, Ollama status.
- System Monitor page: the same numbers plus loaded models and an **Unload model** button.

## Tune for your machine
| Symptom | Fix |
|---|---|
| Replies feel slow | Use `qwen3:1.7b` (default). Try `qwen3:4b` only if you free RAM. |
| RAM above 90% | `POST /system/unload-model`, close Chrome tabs, pause schedules. |
| First reply very slow | The model loads on demand - normal. It unloads after 2 minutes idle. |
| Voice slow | Set `JARVIS_WHISPER_MODEL=tiny` (default). `base` is more accurate but slower. |
| Disk filling up | Old logs and old backups are pruned automatically; delete `data/temp` audio safely. |

## Change the model
```powershell
# C:\JARVIS\backend\.env
OLLAMA_MODEL=qwen3:4b
OLLAMA_THINK=false
OLLAMA_KEEP_ALIVE=2m
```
Restart the backend. Check `GET /system/status` to confirm the active model.

## Expected disk usage
| Item | Size |
|---|---|
| qwen3:1.7b model | 1.2 GB |
| qwen3:4b model | 2.5 GB |
| Whisper tiny | 75 MB |
| Python venv + deps | ~600 MB |
| Frontend node_modules + build | ~350 MB |
| Database | grows slowly, a few MB typical |

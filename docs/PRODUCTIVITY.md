# Tasks, Developer Assistant & File Manager (Phase 7)

## What it does
- **Tasks/Reminders:** add, list, complete, delete (with confirmation), due dates, times, categories, overdue detection, reminders, productivity report.
- **Scheduler:** configurable schedules (morning report, job discovery, Gmail review, study reminders) with pause/resume/stop. Runs only while enabled — no polling when disabled.
- **Developer Assistant:** static code analysis (Python AST), dangerous-command detection, project summary, AI code explanation.
- **File Manager:** listing, text/PDF reading, AI summarising — restricted to `C:\JARVIS`.

## Why required
Productivity loop (plan → act → review) plus safe local file/code analysis without touching the rest of your PC.

## Task parsing
`"Remind me to study SQL at 7 PM"` → due 19:00 (today, or tomorrow if 7 PM already passed).
`"Call recruiter tomorrow"` → due tomorrow. `Submit assignment today at 9 PM` → today 21:00.
Categories: `general`, `study`, `job`, `follow-up`. Delete requires `confirmed=true`.

## Endpoints
- `POST /tasks` {title, notes?, category?, priority?, due_date?, due_time?, remind_at?}
- `GET /tasks?status=&due=today|overdue` · `POST /tasks/{id}/complete` · `DELETE /tasks/{id}?confirmed=true`
- `GET /tasks/productivity` · `GET /reminders/due`
- `GET /schedules` · `POST /schedules` {name, job_type, time_of_day?, enabled?} · `POST /schedules/pause|resume` · `POST /schedules/run/{job_type}`
- `POST /developer/analyze` {path?|code?} · `POST /developer/explain` · `GET /developer/project?root=`
- `GET /files?subdir=` · `GET /files/read?path=` · `POST /files/summarize` {path|code}

## Safety
- File access is confined to `C:\JARVIS` (`JARVIS_FILE_ROOT`). Any other path returns an error.
- `.venv`, `node_modules`, `.git`, `__pycache__` are skipped when listing.
- Destructive shell patterns (`rm -rf`, `format C:`, `DROP TABLE`, `git push --force`, `Remove-Item -Recurse`, …) are detected and reported, never executed.
- JARVIS never executes shell commands from chat.

## Verify
```powershell
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"Study SQL at 7 PM","category":"study"}'
curl http://127.0.0.1:8000/tasks
curl http://127.0.0.1:8000/tasks/productivity
curl -X POST http://127.0.0.1:8000/developer/analyze -H "Content-Type: application/json" -d '{"code":"def f(x): return x+1"}'
curl "http://127.0.0.1:8000/files?subdir=docs"
curl http://127.0.0.1:8000/schedules
```

## Common errors
- `path outside allowed root` — expected for anything outside `C:\JARVIS`; set `JARVIS_FILE_ROOT` to widen it deliberately.
- `unsupported file type for text analysis` — only text/code/PDF types are read.
- `file too large` — limit is 2 MB (10 MB for PDFs).
- Scheduler does nothing — schedules are disabled by default; set `enabled: true` then `POST /schedules/resume`.

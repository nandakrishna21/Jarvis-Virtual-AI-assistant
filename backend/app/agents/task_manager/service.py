import re
from datetime import datetime, date
from app.database.session import SessionLocal
from app.database.models import Task, Reminder, Schedule, AgentRun

CATEGORIES = ["general", "study", "job", "follow-up"]

def parse_when(text: str) -> dict:
    """Parse a simple time expression into due_date and due_time.
    Supports: 'today', 'tomorrow', 'YYYY-MM-DD', '7 PM', '7:30 pm', 'at 19:00'."""
    low = (text or "").lower()
    today = date.today()
    due_date, due_time = None, None
    if "tomorrow" in low:
        from datetime import timedelta
        due_date = (today + timedelta(days=1)).isoformat()
    elif "today" in low:
        due_date = today.isoformat()
    else:
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text or "")
        if m:
            due_date = m.group(1)
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", low)
    if m:
        hour = int(m.group(1)) % 12
        minute = int(m.group(2) or 0)
        if m.group(3) == "pm":
            hour += 12
        due_time = f"{hour:02d}:{minute:02d}"
    else:
        m = re.search(r"\bat\s+(\d{1,2}):(\d{2})\b", low)
        if m:
            due_time = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    return {"due_date": due_date, "due_time": due_time}

def add_task(title: str, notes: str = "", category: str = "general", priority: int = 2,
             due_date: str | None = None, due_time: str | None = None,
             remind_at: str | None = None) -> dict:
    if not title or not title.strip():
        return {"error": "title is required"}
    if category not in CATEGORIES:
        category = "general"
    parsed = parse_when(title + " " + (notes or ""))
    due_date = due_date or parsed["due_date"]
    due_time = due_time or parsed["due_time"]
    if due_time and not due_date:
        from datetime import datetime, timedelta
        now = datetime.now()
        hh, mm = [int(x) for x in due_time.split(":")]
        candidate = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        due_date = candidate.date().isoformat()
    db = SessionLocal()
    try:
        task = Task(title=title.strip(), notes=notes, category=category, priority=priority,
                    due_date=due_date, due_time=due_time)
        db.add(task); db.flush()
        if remind_at:
            db.add(Reminder(task_id=task.id, remind_at=remind_at, message=title.strip()))
        db.commit()
        return {"task_id": task.id, "title": task.title, "due_date": due_date, "due_time": due_time,
                "category": category, "reminder_scheduled": bool(remind_at)}
    finally:
        db.close()

def list_tasks(status: str | None = None, due: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        q = db.query(Task)
        if status:
            q = q.filter(Task.status == status)
        rows = q.order_by(Task.due_date.is_(None), Task.due_date, Task.due_time, Task.priority).all()
        out = []
        today = date.today().isoformat()
        for t in rows:
            overdue = bool(t.due_date and t.due_date < today and t.status == "pending")
            out.append({"id": t.id, "title": t.title, "notes": t.notes, "category": t.category,
                        "due_date": t.due_date, "due_time": t.due_time, "priority": t.priority,
                        "status": t.status, "overdue": overdue})
        if due == "today":
            out = [t for t in out if t["due_date"] == today or (t["due_date"] is None and t["status"] == "pending")]
        elif due == "overdue":
            out = [t for t in out if t["overdue"]]
        return out
    finally:
        db.close()

def complete_task(task_id: int) -> dict:
    db = SessionLocal()
    try:
        t = db.get(Task, task_id)
        if not t:
            return {"error": "task not found"}
        t.status = "completed"
        t.completed_at = datetime.utcnow().isoformat()
        db.commit()
        return {"task_id": task_id, "status": "completed"}
    finally:
        db.close()

def delete_task(task_id: int, confirmed: bool = False) -> dict:
    if not confirmed:
        return {"error": "confirmation required", "needs_confirmation": True, "task_id": task_id}
    db = SessionLocal()
    try:
        t = db.get(Task, task_id)
        if not t:
            return {"error": "task not found"}
        db.query(Reminder).filter(Reminder.task_id == task_id).delete()
        db.delete(t); db.commit()
        return {"task_id": task_id, "deleted": True}
    finally:
        db.close()

def due_reminders(now: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        now = now or datetime.now().isoformat(timespec="minutes")
        rows = db.query(Reminder).filter(Reminder.status == "scheduled", Reminder.remind_at <= now).all()
        return [{"id": r.id, "task_id": r.task_id, "remind_at": r.remind_at, "message": r.message} for r in rows]
    finally:
        db.close()

def fire_reminders(now: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        now = now or datetime.now().isoformat(timespec="minutes")
        rows = db.query(Reminder).filter(Reminder.status == "scheduled", Reminder.remind_at <= now).all()
        fired = []
        for r in rows:
            task = db.get(Task, r.task_id)
            r.status = "fired"
            fired.append({"reminder_id": r.id, "task_id": r.task_id,
                          "message": r.message or (task.title if task else "Reminder")})
        db.commit()
        return fired
    finally:
        db.close()

def list_schedules() -> list[dict]:
    db = SessionLocal()
    try:
        rows = db.query(Schedule).all()
        return [{"id": r.id, "name": r.name, "job_type": r.job_type, "time_of_day": r.time_of_day,
                 "enabled": r.enabled, "interval_minutes": r.interval_minutes, "last_run": r.last_run}
                for r in rows]
    finally:
        db.close()

def set_schedule(name: str, job_type: str, time_of_day: str | None = None,
                 interval_minutes: int | None = None, enabled: bool = False) -> dict:
    db = SessionLocal()
    try:
        row = db.query(Schedule).filter(Schedule.name == name).first()
        if not row:
            row = Schedule(name=name, job_type=job_type)
            db.add(row)
        row.job_type = job_type
        row.time_of_day = time_of_day
        row.interval_minutes = interval_minutes
        row.enabled = enabled
        db.commit()
        return {"id": row.id, "name": name, "job_type": job_type, "time_of_day": time_of_day,
                "interval_minutes": interval_minutes, "enabled": enabled}
    finally:
        db.close()

def pause_all() -> dict:
    db = SessionLocal()
    try:
        n = db.query(Schedule).filter(Schedule.enabled.is_(True)).update({"enabled": False})
        db.commit()
        return {"paused": n}
    finally:
        db.close()

def resume_all() -> dict:
    db = SessionLocal()
    try:
        n = db.query(Schedule).filter(Schedule.enabled.is_(False)).update({"enabled": True})
        db.commit()
        return {"resumed": n}
    finally:
        db.close()

def log_run(agent: str, action: str, status: str = "success", detail: str = "", duration_ms: int = 0) -> None:
    db = SessionLocal()
    try:
        db.add(AgentRun(agent=agent, action=action, status=status, detail=detail[:2000], duration_ms=duration_ms))
        db.commit()
    finally:
        db.close()

def productivity_report() -> dict:
    tasks = list_tasks()
    pending = [t for t in tasks if t["status"] == "pending"]
    overdue = [t for t in pending if t["overdue"]]
    today = date.today().isoformat()
    due_today = [t for t in pending if t["due_date"] == today]
    by_cat = {}
    for t in pending:
        by_cat[t["category"]] = by_cat.get(t["category"], 0) + 1
    return {"date": today, "pending": len(pending), "due_today": len(due_today),
            "overdue": len(overdue), "completed": len([t for t in tasks if t["status"] == "completed"]),
            "by_category": by_cat,
            "today_tasks": [{"id": t["id"], "title": t["title"], "due_time": t["due_time"],
                             "category": t["category"]} for t in due_today]}

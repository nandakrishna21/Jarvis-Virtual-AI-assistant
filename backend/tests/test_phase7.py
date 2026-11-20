from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.agents.task_manager import service as task_service
from app.agents.developer import service as dev_service
from app.agents.file_manager import service as file_service
from app.scheduler import scheduler
from app.database.session import SessionLocal
from app.database.models import Task

client = TestClient(app)

def test_parse_when_today_tomorrow_time():
    p = task_service.parse_when("study SQL today at 7 PM")
    assert p["due_date"] == task_service.date.today().isoformat()
    assert p["due_time"] == "19:00"

def test_parse_when_tomorrow():
    from datetime import timedelta
    p = task_service.parse_when("call recruiter tomorrow")
    assert p["due_date"] == (task_service.date.today() + timedelta(days=1)).isoformat()

def test_add_and_list_task():
    r = task_service.add_task("Study SQL at 7 PM", category="study")
    assert r["task_id"] > 0 and r["due_time"] == "19:00"
    tasks = task_service.list_tasks()
    assert any(t["title"] == "Study SQL at 7 PM" for t in tasks)

def test_complete_task():
    r = task_service.add_task("Finish assignment")
    res = task_service.complete_task(r["task_id"])
    assert res["status"] == "completed"
    assert not any(t["id"] == r["task_id"] for t in task_service.list_tasks(status="pending"))

def test_delete_requires_confirmation():
    r = task_service.add_task("Temporary task")
    blocked = task_service.delete_task(r["task_id"], confirmed=False)
    assert blocked.get("needs_confirmation") is True
    ok = task_service.delete_task(r["task_id"], confirmed=True)
    assert ok["deleted"] is True

def test_overdue_detection():
    db = SessionLocal()
    try:
        t = Task(title="Old task", due_date="2020-01-01", status="pending")
        db.add(t); db.commit()
    finally:
        db.close()
    overdue = task_service.list_tasks(due="overdue")
    assert any(t["title"] == "Old task" for t in overdue)

def test_productivity_report():
    task_service.add_task("Report check")
    rep = task_service.productivity_report()
    assert "pending" in rep and "overdue" in rep and rep["date"]

def test_reminder_fire_once():
    r = task_service.add_task("Call bank", remind_at="2000-01-01T00:00")
    fired = task_service.fire_reminders()
    assert any(f["task_id"] == r["task_id"] for f in fired)
    fired2 = task_service.fire_reminders()
    assert not any(f["task_id"] == r["task_id"] for f in fired2)

def test_schedule_pause_resume():
    task_service.set_schedule("morning", "morning_report", "07:00", enabled=True)
    assert any(s["enabled"] for s in task_service.list_schedules())
    task_service.pause_all()
    assert not any(s["enabled"] for s in task_service.list_schedules())
    task_service.resume_all()
    assert any(s["enabled"] for s in task_service.list_schedules())

def test_scheduler_status_and_pause():
    st = scheduler.status()
    assert "running" in st and "schedules" in st
    assert scheduler.pause()["status"] == "paused"
    assert scheduler.resume()["status"] == "resumed"

def test_file_access_restricted_outside_root():
    res = file_service.read_text("C:\\Windows\\System32\\drivers\\etc\\hosts")
    assert "error" in res and "allowed root" in res["error"]

def test_file_listing_skips_venv():
    res = file_service.list_files("backend")
    paths = [f["path"] for f in res["files"]]
    assert not any(".venv" in p for p in paths)

def test_read_text_file_in_root():
    res = file_service.read_text(r"C:\JARVIS\README.md")
    assert "content" in res and "JARVIS" in res["content"]

def test_dangerous_command_detection():
    hits = file_service.find_dangerous("run rm -rf /home/user")
    assert hits and hits[0]["pattern"] == r"\brm\s+-rf\b"

def test_code_analysis_detects_functions_and_syntax_error():
    code = "import os\n\ndef hello():\n    return 1\n"
    res = dev_service.analyze_code(code, "x.py")
    assert res["functions"][0]["name"] == "hello"
    assert res["imports"] == ["os"]
    bad = dev_service.analyze_code("def broken(:\n  pass", "x.py")
    assert any(i["type"] == "syntax_error" for i in bad["issues"])

def test_explain_code_uses_ollama():
    with patch("app.services.ollama.chat", new=AsyncMock(return_value={"ok": True, "response": "explains"})):
        res = __import__("asyncio").run(dev_service.explain_code("def f(): return 1", "x.py"))
    assert res["explanation"]["response"] == "explains"

def test_task_endpoints():
    r = client.post("/tasks", json={"title": "API task"})
    assert r.status_code == 200
    tid = r.json()["task_id"]
    assert client.post(f"/tasks/{tid}/complete").json()["status"] == "completed"
    assert client.get("/tasks").status_code == 200
    assert client.get("/tasks/productivity").status_code == 200
    assert client.get("/schedules").status_code == 200
    assert client.get("/files").status_code == 200
    assert client.get("/developer/project").status_code == 200

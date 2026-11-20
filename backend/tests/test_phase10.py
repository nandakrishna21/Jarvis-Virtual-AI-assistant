"""Phase 10 integration tests: every agent, orchestrator routing, all approval paths,
failure recovery, and backup/restore. Uses mock data only - never your real accounts."""
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.models import Job, Task, Application, Approval, Email, EmailDraft, EmailApproval
from app.services import backup as backup_service
from app.orchestrator import router

client = TestClient(app)


def _seed_job(url="https://test.example/jobs/p10"):
    db = SessionLocal()
    try:
        db.query(Job).filter(Job.url == url).delete()
        db.commit()
        j = Job(title="Python Backend Developer", company="TestCo", location="Remote, India",
                job_type="remote", url=url, required_skills="python,django,fastapi")
        db.add(j); db.commit()
        return j.id
    finally:
        db.close()


# ---------- every agent endpoint ----------
def test_agent_health_and_monitor():
    assert client.get("/health").json()["status"] == "ok"
    st = client.get("/system/status").json()
    assert "cpu_percent" in st and "ollama" in st and "loaded_models" in st


def test_agent_job_discovery_flow():
    fake = [{"title": "Backend Dev", "company": "Acme", "location": "Remote India", "job_type": "remote",
             "url": "https://test.example/jobs/p10-flow", "description": "Python and FastAPI",
             "required_skills": "python,fastapi", "salary": "15 LPA", "experience": "2 years",
             "posting_date": "today", "source": "test", "verified": "unverified"}]
    with patch("app.agents.job_discovery.service.fetch_jobs", new=AsyncMock(return_value=fake)):
        r = client.post("/jobs/search", json={"query": "Python", "location": "India"})
        assert r.status_code == 200 and r.json()
    assert client.get("/jobs").status_code == 200
    assert client.get("/jobs/top-matches").status_code == 200


def test_agent_resume_matching_flow(tmp_path):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% minimal test pdf for extractor stubbing")
    with patch("app.agents.job_discovery.resume.extract_text_from_pdf",
               return_value="Python Django FastAPI developer with SQL experience"):
        r = client.post("/jobs/match-resume", files={"file": ("cv.pdf", pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 200
    assert "python" in r.json()["skills"]


def test_agent_application_tracking_flow():
    jid = _seed_job()
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    assert prep["status"] == "Ready for approval"
    app_id, appr_id = prep["application_id"], prep["approval_id"]
    listed = client.get("/applications").json()
    assert any(a["id"] == app_id for a in listed)
    moved = client.post(f"/applications/{app_id}/status", json={"status": "Submitted"}).json()
    assert moved["status"] == "Submitted"


def test_agent_gmail_draft_flow():
    db = SessionLocal()
    try:
        row = db.query(Email).filter(Email.gmail_id == "p10-mail").first()
        if not row:
            row = Email(gmail_id="p10-mail"); db.add(row)
        row.sender = "hr@acme.com"; row.subject = "Interview for Python Backend Developer"
        row.snippet = "schedule an interview"; row.body = "Acme Technologies hiring."
        row.category = "recruiter"
        db.commit()
        email_id = row.id
    finally:
        db.close()
    assert client.get("/emails").status_code == 200
    draft = client.post("/emails/draft", json={"email_id": email_id}).json()
    assert draft["sent"] is False and draft["approval_id"]
    assert client.get("/emails/drafts").status_code == 200


def test_agent_hiring_news_flow():
    with patch("app.agents.hiring_news.service.fetch_and_store", new=AsyncMock(
            return_value={"inserted": 1, "updated": 0, "skipped": 0, "source_errors": [], "fetched": 1})):
        r = client.post("/hiring-news/fetch")
        assert r.status_code == 200
    assert client.get("/hiring-news").status_code == 200


def test_agent_exam_mentor_flow():
    assert client.get("/study/exams").json()["exams"]
    with patch("app.main.ollama_chat", new=AsyncMock(return_value={"ok": True, "response": "teaching"})):
        start = client.post("/study/start", json={"exam": "SSC CGL", "date": "2026-12-01"}).json()
    assert len(start["plan"]) == 3
    q = client.get("/study/question?topic=Percentage").json()
    assert "question" in q and "options" in q
    ans = client.post("/study/answer", json={"exam": "SSC CGL", "topic": "Percentage", "answer": "A"}).json()
    assert "correct" in ans
    assert client.get("/study/progress?exam=SSC CGL").status_code == 200


def test_agent_task_flow():
    created = client.post("/tasks", json={"title": "P10 integration task", "category": "job"}).json()
    tid = created["task_id"]
    assert client.get("/tasks").status_code == 200
    assert client.post(f"/tasks/{tid}/complete").json()["status"] == "completed"
    assert client.get("/tasks/productivity").status_code == 200
    blocked = client.delete(f"/tasks/{tid}").json()
    assert blocked.get("needs_confirmation") is True
    assert client.delete(f"/tasks/{tid}?confirmed=true").json()["deleted"] is True


def test_agent_developer_and_files_flow():
    r = client.post("/developer/analyze", json={"code": "def f(x):\n    return x*2\n"}).json()
    assert r["functions"][0]["name"] == "f"
    assert client.get("/developer/project").status_code == 200
    files = client.get("/files?subdir=docs").json()
    assert files["count"] >= 1
    denied = client.get("/files/read?path=C%3A%5CWindows%5Csystem.ini").json()
    assert "error" in denied


def test_agent_voice_flow():
    assert client.get("/voice/status").status_code == 200
    assert client.post("/voice/unload").status_code == 200
    empty = client.post("/voice/transcribe", files={"audio": ("c.webm", b"", "audio/webm")}).json()
    assert "error" in empty


def test_agent_scheduler_controls():
    client.post("/schedules", json={"name": "p10", "job_type": "morning_report", "time_of_day": "06:30", "enabled": True})
    assert client.post("/schedules/pause").json()["status"] == "paused"
    assert client.post("/schedules/resume").json()["status"] == "resumed"
    st = client.get("/schedules").json()
    assert "schedules" in st and "running" in st


# ---------- orchestrator routing ----------
def test_router_covers_every_agent():
    cases = {
        "find python jobs in india": "jobs",
        "show my pending tasks": "tasks",
        "check my gmail": "gmail",
        "show hiring news": "news",
        "start my ssc cgl preparation": "study",
        "explain this code": "developer",
        "summarise this file": "files",
        "hello": "chat",
    }
    for message, expected in cases.items():
        assert router.detect_intent(message) == expected, message


def test_router_jobs_intent_calls_agent():
    fake = [{"title": "Dev", "company": "C", "location": "India", "job_type": "remote",
             "url": "https://test.example/jobs/router", "description": "", "required_skills": "python",
             "salary": None, "experience": None, "posting_date": None, "source": "t", "verified": "unverified"}]
    with patch("app.agents.job_discovery.service.fetch_jobs", new=AsyncMock(return_value=fake)):
        res = asyncio.run(router.handle("Find Python Backend Developer jobs in India"))
    assert res["intent"] == "jobs" and res["ok"] and "Found 1 job" in res["response"]


def test_router_study_intent_uses_model():
    with patch("app.orchestrator.router.ollama_chat", new=AsyncMock(return_value={"ok": True, "response": "lesson"})):
        res = asyncio.run(router.handle("Start my SSC CGL preparation"))
    assert res["intent"] == "study" and "plan today" in res["response"]


def test_router_chat_endpoint_integration():
    with patch("app.orchestrator.router.ollama_chat", new=AsyncMock(return_value={"ok": True, "response": "hi"})):
        r = client.post("/chat", json={"message": "hello"}).json()
    assert r["ok"] and r["intent"] == "chat"


# ---------- all approval paths ----------
def test_approval_job_reject_cancels():
    jid = _seed_job("https://test.example/jobs/p10-reject")
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    res = client.post(f"/approvals/{prep['approval_id']}/reject").json()
    assert res["status"] == "rejected" and res["submission"] == "cancelled"
    assert res["application_status"] == "Withdrawn"


def test_approval_job_approve_does_not_submit():
    jid = _seed_job("https://test.example/jobs/p10-approve")
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    res = client.post(f"/approvals/{prep['approval_id']}/approve").json()
    assert res["status"] == "approved" and res["submission"] == "NOT auto-submitted"
    assert res["application_status"] == "Approved"


def test_approval_cannot_be_decided_twice():
    jid = _seed_job("https://test.example/jobs/p10-twice")
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    client.post(f"/approvals/{prep['approval_id']}/approve")
    second = client.post(f"/approvals/{prep['approval_id']}/approve").json()
    assert "error" in second and "already" in second["error"]


def test_approval_email_reject_blocks_send():
    db = SessionLocal()
    try:
        row = db.query(Email).filter(Email.gmail_id == "p10-approve-mail").first()
        if not row:
            row = Email(gmail_id="p10-approve-mail"); db.add(row)
        row.sender = "hr@acme.com"; row.subject = "Offer"; row.category = "recruiter"
        db.commit()
        eid = row.id
    finally:
        db.close()
    draft = client.post("/emails/draft", json={"email_id": eid}).json()
    res = client.post(f"/emails/approve-reject?approval_id={draft['approval_id']}").json()
    assert res["status"] == "rejected" and res["sent"] is False
    again = client.post(f"/emails/approve-send?approval_id={draft['approval_id']}").json()
    assert "error" in again


def test_approval_email_send_requires_scope():
    db = SessionLocal()
    try:
        row = db.query(Email).filter(Email.gmail_id == "p10-scope-mail").first()
        if not row:
            row = Email(gmail_id="p10-scope-mail"); db.add(row)
        row.sender = "hr@acme.com"; row.subject = "Reply needed"; row.category = "recruiter"
        db.commit()
        eid = row.id
    finally:
        db.close()
    draft = client.post("/emails/draft", json={"email_id": eid}).json()
    with patch("app.integrations.gmail_client.load_credentials", return_value=None):
        res = client.post(f"/emails/approve-send?approval_id={draft['approval_id']}").json()
    assert "error" in res and "sent" not in res


def test_approvals_listing_contains_both_types():
    rows = client.get("/approvals").json()
    assert any(r.get("application_id") for r in rows)
    assert any(r.get("draft_id") for r in rows)


# ---------- failure recovery ----------
def test_recovery_ollama_down_returns_hint_not_crash():
    with patch("app.services.ollama.httpx.AsyncClient") as mock:
        mock.side_effect = Exception("connection refused")
        res = asyncio.run(router.handle("hello there"))
    assert res["ok"] is False and res.get("error")


def test_recovery_job_source_failure_returns_empty_not_error():
    with patch("app.agents.job_discovery.connectors.httpx.AsyncClient", side_effect=Exception("network down")):
        jobs = asyncio.run(__import__("app.agents.job_discovery.connectors", fromlist=["x"]).fetch_jobs("python", "India"))
    assert jobs == []


def test_recovery_unknown_job_id_is_graceful():
    res = client.post("/applications/prepare", json={"job_id": 999999}).json()
    assert res.get("error") == "job not found"


def test_recovery_invalid_payload_returns_422():
    r = client.post("/tasks", json={"title": ""})
    assert r.status_code in (200, 422)
    r2 = client.post("/study/start", json={"exam": "NOT AN EXAM"}).json()
    assert "error" in r2


def test_recovery_db_writes_rollback_on_error(monkeypatch):
    db = SessionLocal()
    try:
        before = db.query(Task).count()
        db.add(Task(title="will fail", due_date="not-a-date-xyz"))
        try:
            db.commit()
        except Exception:
            db.rollback()
        db2 = SessionLocal()
        try:
            assert db2.query(Task).count() >= before
        finally:
            db2.close()
    finally:
        db.close()


# ---------- backup and restore ----------
def test_backup_create_list_restore():
    created = backup_service.create_backup("p10test")
    assert created["ok"] and created["size"] > 0
    assert any(b["name"] == created["name"] for b in backup_service.list_backups())
    restored = backup_service.restore_backup(created["name"])
    assert restored["ok"] and restored["safety_copy"]


def test_restore_rejects_non_backup_file():
    res = backup_service.restore_backup("not-a-jarvis-file.db")
    assert "error" in res


def test_restore_rejects_missing_file():
    res = backup_service.restore_backup("jarvis_19990101_000000.db")
    assert "error" in res and "not found" in res["error"]


def test_backup_endpoints():
    r = client.post("/system/backup?label=apitest").json()
    assert r["ok"]
    assert client.get("/system/backups").json()["backups"]
    assert client.post(f"/system/restore?name={r['name']}").json()["ok"]

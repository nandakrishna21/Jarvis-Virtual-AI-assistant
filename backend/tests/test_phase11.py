"""Phase 11 tests: approval-first action layer, interviews, analytics, automation,
tailored document versioning, LLM provider fallback and the local auth guard.

Mock data only - never your real accounts.
"""
import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal
from app.database.models import (
    ActionProposal,
    Application,
    DocumentVersion,
    Interview,
    Job,
    Notification,
    ResumeProfile,
    ResumeSection,
    Task,
    WorkflowRun,
)
from app.orchestrator import router
from app.services import auth as auth_service
from app.services import documents as documents_service
from app.services import llm as llm_service

client = TestClient(app)


def _seed_job(url: str, title: str = "Python Backend Developer") -> int:
    db = SessionLocal()
    try:
        db.query(Job).filter(Job.url == url).delete()
        db.commit()
        job = Job(
            title=title,
            company="TestCo",
            location="Remote, India",
            job_type="remote",
            url=url,
            description="Python FastAPI and PostgreSQL role",
            required_skills="python,fastapi,postgresql",
            source="test",
            verified="unverified",
        )
        db.add(job)
        db.commit()
        return job.id
    finally:
        db.close()


def _seed_resume(text: str = "Python FastAPI Django SQL developer") -> int:
    db = SessionLocal()
    try:
        row = ResumeProfile(file_path="C:/JARVIS/data/resumes/p11.txt", raw_text=text,
                            extracted_skills="python,fastapi,django,sql")
        db.add(row)
        db.commit()
        return row.id
    finally:
        db.close()


# ---------- approval-first action layer ----------

def test_action_listing_exposes_registered_handlers():
    data = client.get("/actions").json()
    assert data["pending"] >= 0
    assert "create_task" in data["available"]
    assert "run_workflow" in data["available"]
    assert "generate_documents" in data["available"]


def test_chat_task_action_creates_pending_proposal_not_a_task():
    db = SessionLocal()
    try:
        before = db.query(Task).count()
    finally:
        db.close()
    res = client.post("/assistant/chat", json={"message": "add task p11 approval probe"}).json()
    assert res["requires_approval"] is True
    assert res["proposal"]["status"] == "pending"
    db = SessionLocal()
    try:
        after = db.query(Task).count()
        assert after == before
    finally:
        db.close()


def test_approve_proposal_executes_handler_once():
    db = SessionLocal()
    try:
        row = ActionProposal(
            action_type="create_task",
            title="p11 direct proposal",
            plan="[]",
            payload='{"title": "p11 executed task", "category": "general"}',
            payload_hash="test",
        )
        db.add(row)
        db.commit()
        pid = row.id
    finally:
        db.close()

    first = client.post(f"/actions/{pid}/approve").json()
    assert first["ok"] is True
    assert first["proposal"]["status"] == "executed"
    assert first["result"]["ok"] is True

    second = client.post(f"/actions/{pid}/approve").json()
    assert second["ok"] is False
    assert "already" in second["error"]


def test_reject_proposal_does_not_execute():
    db = SessionLocal()
    try:
        row = ActionProposal(
            action_type="create_task",
            title="p11 rejected proposal",
            plan="[]",
            payload='{"title": "p11 must not exist"}',
            payload_hash="test",
        )
        db.add(row)
        db.commit()
        pid = row.id
    finally:
        db.close()

    res = client.post(f"/actions/{pid}/reject?note=not+now").json()
    assert res["ok"] is True
    assert res["proposal"]["status"] == "rejected"

    db = SessionLocal()
    try:
        exists = db.query(Task).filter(Task.title == "p11 must not exist").count()
        assert exists == 0
    finally:
        db.close()


def test_proposal_hash_is_stable_and_order_independent():
    from app.services.proposals import hash_payload

    a = hash_payload({"x": 1, "y": 2})
    b = hash_payload({"y": 2, "x": 1})
    assert a == b
    assert len(a) == 64


def test_unknown_action_type_fails_gracefully():
    db = SessionLocal()
    try:
        row = ActionProposal(action_type="not_a_real_action", title="p11 unknown", plan="[]",
                             payload="{}", payload_hash="test")
        db.add(row)
        db.commit()
        pid = row.id
    finally:
        db.close()
    res = client.post(f"/actions/{pid}/approve").json()
    assert res["ok"] is False
    assert "no handler" in res["error"]


# ---------- interviews ----------

def test_interview_crud_and_stats():
    created = client.post("/interviews", json={
        "company": "TestCo", "role": "Python Backend Developer",
        "interview_date": "2099-12-01", "interview_time": "10:00", "mode": "online",
    }).json()
    assert created["company"] == "TestCo"
    iid = created["id"]

    listing = client.get("/interviews").json()
    assert any(i["id"] == iid for i in listing["interviews"])
    assert listing["stats"]["total"] >= 1

    patched = client.patch(f"/interviews/{iid}", json={"status": "completed"}).json()
    assert patched["status"] == "completed"

    removed = client.delete(f"/interviews/{iid}").json()
    assert removed["deleted"] is True


def test_interview_invalid_mode_defaults_to_online():
    created = client.post("/interviews", json={"company": "ModeCo", "mode": "carrier-pigeon"}).json()
    assert created["mode"] == "online"


def test_interview_missing_returns_error_not_crash():
    res = client.patch("/interviews/999999", json={"status": "completed"}).json()
    assert res.get("error")


def test_interview_reminder_creates_task_once():
    db = SessionLocal()
    try:
        db.query(Task).filter(Task.title.like("Interview: RemindCo%")).delete()
        db.query(Interview).filter(Interview.company == "RemindCo").delete()
        db.commit()
        row = Interview(company="RemindCo", role="AI Engineer",
                        interview_date=__import__("datetime").date.today().isoformat(),
                        interview_time="09:00", status="scheduled")
        db.add(row)
        db.commit()
    finally:
        db.close()
    from app.agents.interview import service as interview_service

    db = SessionLocal()
    try:
        first = interview_service.create_upcoming_tasks(db)
        second = interview_service.create_upcoming_tasks(db)
        assert len(first) == 1
        assert second == []
    finally:
        db.close()


# ---------- analytics ----------

def test_analytics_overview_shape():
    data = client.get("/analytics/overview").json()
    for section in ("jobs", "applications", "interviews", "tasks", "automations", "history_points"):
        assert section in data
    assert "top_sources" in data["jobs"]
    assert "by_status" in data["applications"]
    assert "by_category" in data["tasks"]


def test_analytics_jobs_and_applications_endpoints():
    jid = _seed_job("https://test.example/jobs/p11-analytics")
    client.post("/applications/prepare", json={"job_id": jid})
    jobs = client.get("/analytics/jobs").json()
    assert isinstance(jobs["jobs"], list)
    apps = client.get("/analytics/applications").json()
    assert isinstance(apps["applications"], list)
    assert any(a["job_id"] == jid for a in apps["applications"])


# ---------- automation ----------

def test_automation_run_requires_approval():
    res = client.post("/automation/run", json={"workflow": "daily_report"}).json()
    assert res["requires_approval"] is True
    assert res["proposal"]["status"] == "pending"
    assert res["proposal"]["action_type"] == "run_workflow"


def test_automation_run_unknown_workflow_is_rejected():
    res = client.post("/automation/run", json={"workflow": "not_a_workflow"}).json()
    assert res["ok"] is False
    assert "unknown workflow" in res["error"]


def test_automation_overview_and_logs():
    data = client.get("/automation").json()
    assert data["workflows"]
    assert "n8n" in data
    assert "scheduler" in data
    logs = client.get("/automation/logs").json()
    assert "runs" in logs


def test_automation_native_fallback_runs_and_records():
    db = SessionLocal()
    try:
        row = ActionProposal(action_type="run_workflow", title="p11 workflow run", plan="[]",
                             payload='{"workflow": "daily_report"}', payload_hash="test")
        db.add(row)
        db.commit()
        pid = row.id
    finally:
        db.close()

    res = client.post(f"/actions/{pid}/approve").json()
    assert res["ok"] is True
    assert res["result"]["ok"] is True
    assert res["result"]["engine"] in ("n8n", "native", "native-fallback")

    db = SessionLocal()
    try:
        assert db.query(WorkflowRun).filter(WorkflowRun.workflow == "daily_report").count() >= 1
    finally:
        db.close()


def test_automation_catalog_has_all_workflows():
    from app.agents.automation import catalog

    names = {w["name"] for w in catalog.WORKFLOWS}
    assert {"job_discovery", "daily_report", "application_follow_up",
            "interview_reminders", "gmail_review"} <= names


# ---------- tailored documents ----------

def test_resume_sections_crud():
    rid = _seed_resume("Python FastAPI developer with SQL experience")
    created = client.post(f"/resumes/{rid}/sections", json={
        "section_type": "experience", "title": "Backend Developer",
        "organization": "Acme", "start_date": "2024-01", "end_date": "2026-01",
        "description": "Built FastAPI services with PostgreSQL.",
    }).json()
    assert created["section_type"] == "experience"
    sid = created["id"]

    listed = client.get(f"/resumes/{rid}/sections").json()
    assert any(s["id"] == sid for s in listed["sections"])

    patched = client.patch(f"/sections/{sid}", json={"title": "Senior Backend Developer"}).json()
    assert patched["title"] == "Senior Backend Developer"

    removed = client.delete(f"/sections/{sid}").json()
    assert removed["deleted"] is True


def test_invalid_section_type_falls_back_to_custom():
    rid = _seed_resume("Python developer")
    created = client.post(f"/resumes/{rid}/sections", json={
        "section_type": "not-a-type", "title": "Thing", "description": "text",
    }).json()
    assert created["section_type"] == "custom"


def test_generate_documents_creates_versions_and_downloads():
    rid = _seed_resume("Python FastAPI Django SQL developer")
    jid = _seed_job("https://test.example/jobs/p11-docs")
    client.post(f"/resumes/{rid}/sections", json={
        "section_type": "experience", "title": "Backend Developer", "organization": "Acme",
        "description": "Built FastAPI services.",
    })

    res = client.post("/documents/generate", json={
        "resume_id": rid, "job_id": jid, "types": ["resume", "cover_letter"],
    }).json()
    assert res["count"] == 2
    types = {d["doc_type"] for d in res["documents"]}
    assert types == {"resume", "cover_letter"}
    for doc in res["documents"]:
        assert doc["version"] == 1
        assert doc["file_path"]
        assert "JARVIS" in doc["content"]

    listed = client.get(f"/documents?resume_id={rid}").json()
    assert len(listed["documents"]) >= 2

    doc_id = res["documents"][0]["id"]
    single = client.get(f"/documents/{doc_id}").json()
    assert single["id"] == doc_id

    download = client.get(f"/documents/{doc_id}/download")
    assert download.status_code == 200
    assert "JARVIS" in download.text


def test_document_versions_increment_per_job():
    rid = _seed_resume("Python developer")
    jid = _seed_job("https://test.example/jobs/p11-version")
    first = client.post("/documents/generate", json={"resume_id": rid, "job_id": jid,
                                                     "types": ["resume"]}).json()
    second = client.post("/documents/generate", json={"resume_id": rid, "job_id": jid,
                                                      "types": ["resume"]}).json()
    assert first["documents"][0]["version"] == 1
    assert second["documents"][0]["version"] == 2


def test_document_generation_never_submits():
    rid = _seed_resume("Python developer")
    jid = _seed_job("https://test.example/jobs/p11-nosubmit")
    res = client.post("/documents/generate", json={"resume_id": rid, "job_id": jid}).json()
    assert "Nothing was submitted" in res["warning"]
    db = SessionLocal()
    try:
        apps = db.query(Application).filter(Application.job_id == jid).count()
        assert apps == 0
    finally:
        db.close()


def test_chat_document_request_proposes_instead_of_writing():
    rid = _seed_resume("Python FastAPI developer")
    jid = _seed_job("https://test.example/jobs/p11-chatdoc")
    db = SessionLocal()
    try:
        before = db.query(DocumentVersion).count()
    finally:
        db.close()

    res = client.post("/assistant/chat", json={
        "message": f"tailor my resume for job {jid}",
    }).json()
    assert res["requires_approval"] is True
    assert res["proposal"]["action_type"] == "generate_documents"

    db = SessionLocal()
    try:
        assert db.query(DocumentVersion).count() == before
    finally:
        db.close()


def test_documents_listing_filters_by_type():
    rid = _seed_resume("Python developer")
    jid = _seed_job("https://test.example/jobs/p11-filter")
    client.post("/documents/generate", json={"resume_id": rid, "job_id": jid,
                                             "types": ["cover_letter"]})
    only_cover = client.get(f"/documents?resume_id={rid}&doc_type=cover_letter").json()
    assert only_cover["documents"]
    assert all(d["doc_type"] == "cover_letter" for d in only_cover["documents"])


def test_missing_document_returns_error():
    res = client.get("/documents/999999").json()
    assert res.get("error")


# ---------- LLM providers ----------

def test_provider_status_reports_availability():
    status = llm_service.provider_status()
    assert status["active"] in ("ollama", "gemini", "openrouter")
    assert status["available"]["ollama"] is True
    assert status["fallback"] == "ollama"


def test_provider_switch_rejects_unknown():
    res = client.put("/system/llm", json={"provider": "not-a-provider"}).json()
    assert res["ok"] is False


def test_provider_switch_persists_and_can_be_restored():
    from app.config import settings

    original = settings.llm_provider
    try:
        res = client.put("/system/llm", json={"provider": "ollama"}).json()
        assert res["ok"] is True
        assert llm_service.load_persisted_provider() == "ollama"
    finally:
        settings.llm_provider = original


def test_gemini_without_key_falls_back_to_ollama():
    from app.config import settings

    original_provider = settings.llm_provider
    original_key = settings.gemini_api_key
    try:
        settings.llm_provider = "gemini"
        settings.gemini_api_key = ""
        with patch("app.services.llm.ollama.chat", new=AsyncMock(
                return_value={"ok": True, "response": "from ollama"})) as mock:
            res = asyncio.run(llm_service.chat("hello"))
        assert res["ok"] is True
        assert res["response"] == "from ollama"
        mock.assert_awaited_once()
    finally:
        settings.llm_provider = original_provider
        settings.gemini_api_key = original_key


def test_gemini_failure_falls_back_to_ollama():
    from app.config import settings

    original_provider = settings.llm_provider
    original_key = settings.gemini_api_key
    try:
        settings.llm_provider = "gemini"
        settings.gemini_api_key = "fake-key"
        with patch("app.services.llm._gemini", new=AsyncMock(side_effect=Exception("network down"))):
            with patch("app.services.llm.ollama.chat", new=AsyncMock(
                    return_value={"ok": True, "response": "fallback"})) as mock:
                res = asyncio.run(llm_service.chat("hello"))
        assert res["ok"] is True
        assert res["fallback_from"] == "gemini"
        mock.assert_awaited_once()
    finally:
        settings.llm_provider = original_provider
        settings.gemini_api_key = original_key


def test_ollama_is_default_provider_for_chat():
    from app.config import settings

    original = settings.llm_provider
    try:
        settings.llm_provider = "ollama"
        with patch("app.services.llm.ollama.chat", new=AsyncMock(
                return_value={"ok": True, "response": "local"})) as mock:
            res = asyncio.run(llm_service.chat("hi"))
        assert res["response"] == "local"
        assert res.get("provider") == "ollama"
        mock.assert_awaited_once()
    finally:
        settings.llm_provider = original


# ---------- auth guard ----------

def test_auth_status_endpoint():
    status = client.get("/system/auth").json()
    assert "enabled" in status
    assert status["header"] == "X-API-Key"


def test_auth_guard_blocks_mutations_when_key_set():
    original = auth_service.settings.api_key
    original_prefixed = getattr(auth_service.settings, "jarvis_api_key", "")
    try:
        auth_service.settings.api_key = "p11-secret"
        if hasattr(auth_service.settings, "jarvis_api_key"):
            auth_service.settings.jarvis_api_key = ""
        blocked = client.post("/tasks", json={"title": "should be blocked"})
        assert blocked.status_code == 401
        assert "api key required" in blocked.json()["error"]

        allowed = client.post("/tasks", json={"title": "allowed with key"},
                               headers={"X-API-Key": "p11-secret"})
        assert allowed.status_code == 200

        wrong = client.post("/tasks", json={"title": "wrong key"},
                            headers={"X-API-Key": "nope"})
        assert wrong.status_code == 401
    finally:
        auth_service.settings.api_key = original
        if hasattr(auth_service.settings, "jarvis_api_key"):
            auth_service.settings.jarvis_api_key = original_prefixed


def test_auth_guard_leaves_reads_open():
    """Direct read endpoints stay open, but /api reads require the key (tunnel safety)."""
    original = auth_service.settings.api_key
    original_prefixed = getattr(auth_service.settings, "jarvis_api_key", "")
    try:
        auth_service.settings.api_key = "p11-secret"
        if hasattr(auth_service.settings, "jarvis_api_key"):
            auth_service.settings.jarvis_api_key = ""
        assert client.get("/health").status_code == 200
        assert client.get("/jobs").status_code == 200
        assert client.get("/api/jobs").status_code == 401
        assert client.get("/api/jobs", headers={"X-API-Key": "p11-secret"}).status_code == 200
    finally:
        auth_service.settings.api_key = original
        if hasattr(auth_service.settings, "jarvis_api_key"):
            auth_service.settings.jarvis_api_key = original_prefixed


def test_auth_check_is_tolerant_of_empty_config():
    original = auth_service.settings.api_key
    original_prefixed = getattr(auth_service.settings, "jarvis_api_key", "")
    try:
        auth_service.settings.api_key = ""
        if hasattr(auth_service.settings, "jarvis_api_key"):
            auth_service.settings.jarvis_api_key = ""
        assert auth_service.check(None) is True
        assert auth_service.enabled() is False
    finally:
        auth_service.settings.api_key = original
        if hasattr(auth_service.settings, "jarvis_api_key"):
            auth_service.settings.jarvis_api_key = original_prefixed


# ---------- router coverage for the new intents ----------

def test_router_detects_document_intent():
    assert router.detect_intent("tailor my resume for job 3") == "documents"
    assert router.detect_intent("generate a cover letter for job 4") == "documents"


def test_router_document_intent_returns_proposal():
    rid = _seed_resume("Python FastAPI developer")
    jid = _seed_job("https://test.example/jobs/p11-routerdoc")
    res = asyncio.run(router.handle(f"tailor my resume for job {jid}"))
    assert res["intent"] == "documents"
    assert res["requires_approval"] is True
    assert res["proposal"]["payload"]["resume_id"] == rid


# ---------- notifications ----------

def test_notification_is_emitted_when_proposal_is_created():
    from app.database.models import Notification

    db = SessionLocal()
    try:
        before = db.query(Notification).count()
    finally:
        db.close()

    client.post("/assistant/chat", json={"message": "add task p11 notification probe"})

    db = SessionLocal()
    try:
        after = db.query(Notification).count()
        assert after == before + 1
        row = db.query(Notification).order_by(Notification.id.desc()).first()
        assert "Approval needed" in row.title
    finally:
        db.close()


def test_notification_is_emitted_when_action_runs_and_fails():
    from app.database.models import Notification

    db = SessionLocal()
    try:
        before = db.query(Notification).count()
        row = ActionProposal(action_type="not_a_real_action", title="p11 fail notify",
                             plan="[]", payload="{}", payload_hash="test")
        db.add(row)
        db.commit()
        pid = row.id
    finally:
        db.close()

    client.post(f"/actions/{pid}/approve")

    db = SessionLocal()
    try:
        assert db.query(Notification).count() == before + 1
        last = db.query(Notification).order_by(Notification.id.desc()).first()
        assert last.kind == "error"
    finally:
        db.close()


def test_notification_api_lists_and_marks_read():
    from app.services.notifications import notify

    db = SessionLocal()
    try:
        nid = notify(db, "p11 test notification", "body", "info", "/")
    finally:
        db.close()

    listing = client.get("/notifications").json()
    assert any(n["id"] == nid for n in listing["notifications"])

    marked = client.patch(f"/notifications/{nid}/read").json()
    assert marked["is_read"] is True

    unread = client.get("/notifications?unread_only=true").json()
    assert all(n["id"] != nid for n in unread["notifications"])


def test_notification_helper_never_breaks_the_caller():
    from app.services.notifications import notify_safe

    db = SessionLocal()
    try:
        assert notify_safe(db, "p11 safe", "body", "not-a-kind") >= 0
        row = db.query(Notification).order_by(Notification.id.desc()).first()
        assert row.kind == "info"
    finally:
        db.close()

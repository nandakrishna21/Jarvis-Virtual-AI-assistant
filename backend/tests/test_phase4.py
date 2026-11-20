from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.models import Email, EmailDraft
from app.agents.gmail import service as gmail_service

client = TestClient(app)

def _seed_email(subject="Re: Interview for Python Backend Developer", sender="hr@acmetech.com"):
    db = SessionLocal()
    try:
        gid = f"test-{abs(hash(subject+sender))}"
        row = db.query(Email).filter(Email.gmail_id == gid).first()
        if not row:
            row = Email(gmail_id=gid); db.add(row)
        row.sender = sender; row.subject = subject; row.snippet = "We would like to schedule an interview"
        row.body = "Hi, this is Acme Technologies hiring for Python Backend Developer. Interview on 12 May 2026."
        row.category = gmail_service.classify(subject, row.snippet)
        d = gmail_service.extract_details(subject, row.body)
        row.company = d["company"]; row.job_role = d["job_role"]
        row.important_details = str(d["dates"])
        db.commit()
        return row.id
    finally:
        db.close()

def test_classify_recruiter():
    assert gmail_service.classify("We are hiring a Python developer", "your application") == "recruiter"

def test_classify_interview():
    assert gmail_service.classify("Interview schedule confirmation", "technical round") == "interview"

def test_classify_assessment():
    assert gmail_service.classify("Coding assessment", "complete the OA") == "assessment"

def test_classify_spam():
    assert gmail_service.classify("Congratulations you have won lottery", "wire transfer") == "spam"

def test_classify_other():
    assert gmail_service.classify("Newsletter", "weekly digest") == "other"

def test_extract_company_role_date():
    d = gmail_service.extract_details("Python Backend Developer", "Acme Technologies interview on 12 May 2026")
    assert d["company"] and "Acme" in d["company"]
    assert d["dates"] == ["12 May 2026"]

def test_draft_created_not_sent():
    eid = _seed_email()
    r = gmail_service.create_draft(eid)
    assert r["sent"] is False and r["approval_id"] and r["draft_id"]
    assert r["recipient"] == "hr@acmetech.com"
    assert r["subject"].startswith("Re:")

def test_send_blocked_without_approval():
    eid = _seed_email()
    d = gmail_service.create_draft(eid)
    res = gmail_service.send_draft(d["draft_id"])
    assert "error" in res

def test_send_blocked_without_send_scope(monkeypatch):
    eid = _seed_email()
    d = gmail_service.create_draft(eid)
    with patch("app.integrations.gmail_client.load_credentials", return_value=None):
        res = gmail_service.approve_send(d["approval_id"])
    assert "error" in res
    db = SessionLocal()
    try:
        appr_status = db.query(EmailDraft).filter(EmailDraft.id==d["draft_id"]).one().status
    finally:
        db.close()
    assert appr_status == "draft"

def test_approve_send_calls_gmail(monkeypatch):
    eid = _seed_email()
    d = gmail_service.create_draft(eid)
    class Creds:
        scopes = ["https://www.googleapis.com/auth/gmail.send"]
    sent = {"id": "sent-123"}
    class MsgSvc:
        def send(self, userId, body):
            return type("R", (), {"execute": lambda self: sent})()
    class Users:
        def messages(self):
            return MsgSvc()
    class FakeService:
        def users(self):
            return Users()
    monkeypatch.setattr("app.integrations.gmail_client.load_credentials", lambda scopes=None: Creds())
    monkeypatch.setattr("app.integrations.gmail_client.build_service", lambda scopes=None: FakeService())
    res = gmail_service.approve_send(d["approval_id"])
    assert res["sent"] is True and res["gmail_message_id"] == "sent-123"

def test_endpoints():
    assert client.get("/emails").status_code == 200
    assert client.get("/gmail/status").status_code == 200
    assert client.get("/emails/drafts").status_code == 200

def test_email_reject_cancels_draft():
    eid = _seed_email()
    d = gmail_service.create_draft(eid)
    res = gmail_service.reject_send(d["approval_id"])
    assert res["status"] == "rejected" and res["sent"] is False
    db = SessionLocal()
    try:
        assert db.query(EmailDraft).filter(EmailDraft.id == d["draft_id"]).one().status == "rejected"
    finally:
        db.close()

def test_approvals_endpoint_includes_email_approvals():
    eid = _seed_email()
    d = gmail_service.create_draft(eid)
    rows = client.get("/approvals").json()
    assert any(r.get("draft_id") == d["draft_id"] for r in rows)

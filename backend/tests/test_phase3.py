from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.database.models import Job
from app.agents.job_application.materials import build_materials, STATUSES

client = TestClient(app)

def _seed_job():
    db = SessionLocal()
    try:
        db.query(Job).filter(Job.url=="https://test.example/jobs/p3").delete()
        db.commit()
        j = Job(title="Python Backend Developer", company="TestCo", location="Remote",
                url="https://test.example/jobs/p3", required_skills="python")
        db.add(j); db.commit()
        return j.id
    finally:
        db.close()

def test_materials_honest():
    m = build_materials({"title":"Dev","company":"X","location":"Remote"}, ["python"], {"matching_skills":"python","missing_skills":"react"})
    assert "react" in m["cover_letter"]
    assert "do not fabricate" in m["cover_letter"].lower() or "review only" in m["cover_letter"].lower()

def test_statuses_include_required():
    for s in ["Discovered","Shortlisted","Ready for approval","Submitted","Interview","Offer","Withdrawn"]:
        assert s in STATUSES

def test_prepare_creates_pending_approval():
    jid = _seed_job()
    r = client.post("/applications/prepare", json={"job_id": jid})
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "Ready for approval" and d["approval_id"] >= 1
    assert "NOT" not in d["cover_letter"]

def test_reject_cancels():
    jid = _seed_job()
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    r = client.post(f"/approvals/{prep['approval_id']}/reject")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "rejected" and d["application_status"] == "Withdrawn" and d["submission"] == "cancelled"

def test_approve_does_not_autosubmit():
    jid = _seed_job()
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    r = client.post(f"/approvals/{prep['approval_id']}/approve")
    d = r.json()
    assert d["status"] == "approved" and d["application_status"] == "Approved"
    assert d["submission"] == "NOT auto-submitted"

def test_invalid_status_rejected():
    jid = _seed_job()
    prep = client.post("/applications/prepare", json={"job_id": jid}).json()
    r = client.post(f"/applications/{prep['application_id']}/status", json={"status":"Hacked"})
    assert "error" in r.json()

def test_list_endpoints():
    assert client.get("/applications").status_code == 200
    assert client.get("/approvals").status_code == 200

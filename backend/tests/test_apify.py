from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.database.models import Job
from app.database.session import SessionLocal
from app.main import app
from app.services import apify

client = TestClient(app)

SAMPLE = {
    "title": "Python Backend Developer",
    "companyDetails": {"name": "Acme Systems"},
    "formattedLocation": "Hyderabad, Telangana",
    "viewJobLink": "/viewjob?jk=abc123",
    "jobDescription": "<p>Build <b>Python</b> APIs with FastAPI</p>",
    "attributes": [{"key": "1", "label": "Python"}, {"key": "2", "label": "FastAPI"}],
    "jobTypes": ["Full-time"],
    "salary": {"formatted": "8L - 12L"},
    "pubDate": 1730000000000,
}


def test_normalize_indeed_item():
    job = apify._normalize(SAMPLE, "in")
    assert job["title"] == "Python Backend Developer"
    assert job["company"] == "Acme Systems"
    assert job["url"] == "https://in.indeed.com/viewjob?jk=abc123"
    assert job["source"] == "indeed (apify)"
    assert "Python" in job["tags"] and "FastAPI" in job["tags"]
    assert "<p>" not in job["description"] and "FastAPI" in job["description"]
    assert job["salary"] == "8L - 12L"
    assert job["posting_date"] == "2024-10-27"
    assert job["employment_type"] == "Full-time"


def test_apify_disabled_returns_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "apify_token", "")
    r = client.post("/jobs/apify", json={"query": "Python", "location": "India"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "APIFY_API_KEY" in body["error"]


def test_apify_adds_jobs_without_clearing_board(monkeypatch):
    monkeypatch.setattr(settings, "apify_token", "apify_test_token")
    monkeypatch.setattr(settings, "apify_per_minute", 0)

    fake_job = apify._normalize(SAMPLE, "in")
    keep_url = "https://test.example/apify-keep"
    new_url = fake_job["url"]

    db = SessionLocal()
    try:
        db.query(Job).filter(Job.url.in_([keep_url, new_url])).delete()
        db.add(Job(title="Keep Me", company="Existing", url=keep_url, required_skills="python"))
        db.commit()
    finally:
        db.close()

    with patch("app.services.apify.search_jobs", new=AsyncMock(return_value=[fake_job])):
        r = client.post("/jobs/apify", json={
            "query": "Python Backend Developer",
            "location": "Hyderabad, India",
            "limit": 5,
        })
    body = r.json()
    assert body["ok"] is True and body["count"] == 1

    db = SessionLocal()
    try:
        assert db.query(Job).filter(Job.url == keep_url).first() is not None
        added = db.query(Job).filter(Job.url == new_url).first()
        assert added is not None and added.source == "indeed (apify)"
        db.query(Job).filter(Job.url.in_([keep_url, new_url])).delete()
        db.commit()
    finally:
        db.close()

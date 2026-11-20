from fastapi.testclient import TestClient
from app.main import app
from app.agents.job_discovery.scoring import score_job, rank
from app.agents.job_discovery.connectors import dedupe
from app.agents.job_discovery.resume import extract_skills

client = TestClient(app)

def test_extract_skills():
    assert "python" in extract_skills("I know Python and Django")
    assert "fastapi" not in extract_skills("I know Python")

def test_dedupe():
    jobs = [{"url": "https://x/jobs/1"}, {"url": "https://x/jobs/1"}, {"url": "https://x/jobs/2"}]
    assert len(dedupe(jobs)) == 2

def test_scoring():
    s = score_job(["python","django"], {"required_skills":"python,django,react","location":"Remote"})
    assert s["matching_skills"] == ["django","python"]
    assert s["missing_skills"] == ["react"]
    assert 0 < s["score"] <= 100

def test_rank():
    jobs = [{"required_skills":"python","url":"a"},{"required_skills":"python,react","url":"b"}]
    r = rank(jobs, ["python"])
    assert r[0]["url"] == "a"

def test_jobs_list_empty_ok():
    assert client.get("/jobs").status_code == 200

def test_jobs_search_smoke(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock, patch
    fake = [{"title":"Backend Dev","company":"Acme","location":"Remote","job_type":"remote",
             "url":"https://example.com/jobs/1","description":"","required_skills":"python,django",
             "salary":None,"experience":None,"posting_date":None,"source":"test","verified":"unverified"}]
    with patch("app.agents.job_discovery.service.fetch_jobs", new=AsyncMock(return_value=fake)):
        r = client.post("/jobs/search", json={"query":"Python","location":"India"})
        assert r.status_code == 200
        assert len(r.json()) == 1

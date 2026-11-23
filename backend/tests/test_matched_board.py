from fastapi.testclient import TestClient

from app.agents.job_discovery import quality
from app.database.models import Job, JobMatch
from app.database.session import SessionLocal
from app.main import app

client = TestClient(app)


def _seed(url: str, title: str, company: str, location: str, source: str,
          score: float, skills: str = "", description: str = "", job_type: str | None = None) -> int:
    db = SessionLocal()
    try:
        for old in db.query(Job).filter(Job.url == url).all():
            db.query(JobMatch).filter(JobMatch.job_id == old.id).delete()
            db.delete(old)
        db.commit()
        job = Job(title=title, company=company, location=location, url=url,
                  source=source, required_skills=skills, description=description,
                  job_type=job_type)
        db.add(job)
        db.flush()
        db.add(JobMatch(job_id=job.id, score=score, matching_skills=skills,
                        missing_skills="", components="{}", notes="{}"))
        db.commit()
        return job.id
    finally:
        db.close()


def _cleanup(*urls: str) -> None:
    db = SessionLocal()
    try:
        for url in urls:
            for old in db.query(Job).filter(Job.url == url).all():
                db.query(JobMatch).filter(JobMatch.job_id == old.id).delete()
                db.delete(old)
        db.commit()
    finally:
        db.close()


def test_quality_gates():
    class Row:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    prefs = {"target_categories": ["Python Backend Developer", "AI Engineer"],
             "markets": ["India", "Remote worldwide"]}
    skills = ["python", "fastapi"]

    good = Row(title="Backend Software Developer", description="Build APIs with Python",
               tags="", required_skills="", employment_type="", location="Hyderabad, India",
               job_type=None)
    noise = Row(title="Stagiair(e) marketing en communicatie",
                description="Marketing stage", tags="", required_skills="",
                employment_type="", location="Utrecht, Nederland", job_type=None)
    remote = Row(title="Marketing Manager", description="", tags="", required_skills="",
                 employment_type="", location="Remote", job_type="remote")

    assert quality.is_relevant(good, skills, prefs) is True
    assert quality.is_relevant(noise, skills, prefs) is False
    assert quality.location_ok(good, prefs) is True
    assert quality.location_ok(noise, prefs) is False
    assert quality.location_ok(remote, prefs) is True


def test_matched_board_hides_unrelated_and_supports_filters():
    py_url = "https://test.example/matched-python"
    noise_url = "https://test.example/matched-marketing"
    _seed(py_url, "Python Backend Developer", "Acme", "Hyderabad, India", "test",
          88, "python,fastapi", "Build Python APIs with FastAPI")
    _seed(noise_url, "Stagiair(e) marketing en communicatie", "Berenschot",
          "Utrecht, Nederland", "arbeitnow", 53, "", "Marketing stage")

    try:
        body = client.get("/jobs/matched", params={"limit": 100}).json()
        titles = [j["title"] for j in body["jobs"]]
        assert "Python Backend Developer" in titles
        assert "Stagiair(e) marketing en communicatie" not in titles
        assert body["stats"]["hidden"] >= 1
        assert body["stats"]["total"] == len(body["jobs"])

        relaxed = client.get("/jobs/matched", params={"limit": 100, "hide_irrelevant": "false"}).json()
        assert "Stagiair(e) marketing en communicatie" in [j["title"] for j in relaxed["jobs"]]

        searched = client.get("/jobs/matched", params={"limit": 100, "q": "fastapi"}).json()
        assert [j["title"] for j in searched["jobs"]] == ["Python Backend Developer"]

        source = client.get("/jobs/matched", params={"limit": 100, "source": "arbeitnow"}).json()
        assert all(j["source"] == "arbeitnow" for j in source["jobs"])

        legacy = client.get("/matching/results", params={"limit": 100})
        assert legacy.status_code == 200 and isinstance(legacy.json(), list)
    finally:
        _cleanup(py_url, noise_url)

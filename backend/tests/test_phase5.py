import httpx
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from fastapi.testclient import TestClient
from app.main import app
from app.agents.hiring_news import connectors
from app.agents.hiring_news.service import dedupe_key
from app.database.session import SessionLocal
from app.database.models import HiringNews

client = TestClient(app)

NOW = datetime.now(timezone.utc)
RECENT = format_datetime(NOW - timedelta(days=2))
OLD = format_datetime(NOW - timedelta(days=800))

RSS = f"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Acme Technologies is hiring Python Backend Developer</title>
<link>https://careers.acme.com/jobs/123</link>
<description>We are hiring a Python Backend Developer. Location: India, Remote. Experience: 2-4 years. Salary: 15 LPA.</description>
<pubDate>{RECENT}</pubDate></item>
<item><title>Old Coffee Shop hiring barista</title><link>https://example.com/x</link>
<description>Now hiring baristas.</description><pubDate>{OLD}</pubDate></item>
</channel></rss>"""

def test_parse_rss_extracts_fields():
    items = connectors._parse_rss(RSS, "test")
    assert len(items) == 2
    first = items[0]
    assert first["company"] == "Acme Technologies"
    assert first["role"] == "Python Backend Developer"
    assert first["location"] == "India, Remote"
    assert "2-4" in first["experience"]
    assert "LPA" in first["salary"].upper()
    assert first["application_url"] == "https://careers.acme.com/jobs/123"

def test_hiring_keyword_detection():
    assert connectors.is_hiring_related("We are hiring engineers") is True
    assert connectors.is_hiring_related("Company quarterly results") is False

def test_role_relevance():
    assert connectors.role_relevance("Python Backend FastAPI") > 0
    assert connectors.role_relevance("barista coffee shop") == 0

def test_freshness_uses_date():
    assert connectors.is_fresh(RECENT) is True
    assert connectors.is_fresh(OLD) is False
    assert connectors.is_fresh(None) is False

def test_dedupe_key_stable():
    a = dedupe_key({"application_url": "https://x/1", "company": "A"})
    b = dedupe_key({"application_url": "https://x/1", "company": "B"})
    assert a == b

def test_fetch_and_store_filters_old_and_irrelevant():
    def handler(request: httpx.Request) -> httpx.Response:
        if "remotive" in str(request.url):
            return httpx.Response(200, json={"jobs": []})
        return httpx.Response(200, text=RSS, headers={"content-type": "application/rss+xml"})
    transport = httpx.MockTransport(handler)
    import asyncio
    from app.agents.hiring_news import service
    original = httpx.AsyncClient
    def patched(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)
    httpx.AsyncClient = patched
    try:
        result = asyncio.run(service.fetch_and_store())
    finally:
        httpx.AsyncClient = original
    assert result["inserted"] + result["updated"] >= 1
    assert result["skipped"] >= 0
    db = SessionLocal()
    try:
        rows = db.query(HiringNews).all()
        acme = [r for r in rows if r.company == "Acme Technologies"]
        assert acme, "expected Acme Technologies row"
        assert acme[0].is_current is True
        assert acme[0].application_url == "https://careers.acme.com/jobs/123"
        assert all("barista" not in (r.title or "").lower() for r in rows)
        count_before = len(rows)
    finally:
        db.close()
    # Second run must not create a duplicate (dedupe by URL)
    httpx.AsyncClient = patched
    try:
        result2 = asyncio.run(service.fetch_and_store())
    finally:
        httpx.AsyncClient = original
    assert result2["inserted"] == 0 and result2["updated"] >= 1
    db = SessionLocal()
    try:
        assert len(db.query(HiringNews).all()) == count_before
    finally:
        db.close()

def test_endpoint_lists():
    assert client.get("/hiring-news").status_code == 200

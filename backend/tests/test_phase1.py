import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_system_status():
    r = client.get("/system/status")
    assert r.status_code == 200
    data = r.json()
    assert "cpu_percent" in data and "ram_percent" in data

def test_chat_endpoint_exists():
    r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert "ok" in r.json()

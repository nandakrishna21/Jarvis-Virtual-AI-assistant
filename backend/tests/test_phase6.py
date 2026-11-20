from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.agents.government_exam import service as exam_service
from app.agents.government_exam.syllabus import exam_names, topics_for, sections_for
from app.database.session import SessionLocal
from app.database.models import StudyTopic

client = TestClient(app)

def test_supported_exams():
    for e in ["SSC CGL", "SSC CHSL", "RBI Assistant", "IBPS PO"]:
        assert e in exam_names()

def test_topics_not_empty():
    assert len(topics_for("SSC CGL")) > 20
    assert sections_for("SSC CGL").keys()

def test_seed_creates_topics():
    result = exam_service.seed_syllabus()
    assert result["topics_added"] >= 0
    db = SessionLocal()
    try:
        assert db.query(StudyTopic).filter(StudyTopic.exam=="SSC CGL").count() > 0
    finally:
        db.close()

def test_daily_plan_created_and_reused():
    plan1 = exam_service.get_or_create_plan("SSC CGL", "2026-01-01")
    plan2 = exam_service.get_or_create_plan("SSC CGL", "2026-01-01")
    assert len(plan1) == 3
    assert plan1 == plan2

def test_question_has_answer_and_explanation():
    q = exam_service.get_question("Percentage")
    assert q and q["options"] and q["answer"] in ["A","B","C","D"] and q["explanation"]

def test_record_answer_correct_and_wrong():
    q = exam_service.get_question("Number System")
    res = exam_service.record_answer("SSC CGL", "Number System", q, q["answer"])
    assert res["correct"] is True
    res2 = exam_service.record_answer("SSC CGL", "Number System", q, "Z")
    assert res2["correct"] is False and res2["explanation"]

def test_progress_reports_accuracy():
    exam_service.seed_syllabus()
    prog = exam_service.progress("SSC CGL")
    assert "accuracy" in prog and "weak_topics" in prog
    assert prog["total_attempts"] >= 2

def test_answer_keys_are_consistent():
    for topic in ["Percentage", "Average", "Direction and Sense", "Puzzle", "Vocabulary"]:
        q = exam_service.get_question(topic)
        assert q["options"][ord(q["answer"]) - ord("A")] is not None

def test_start_endpoint_uses_ollama():
    with patch("app.main.ollama_chat", new=AsyncMock(return_value={"ok": True, "response": "teaching text"})):
        r = client.post("/study/start", json={"exam": "SSC CGL", "date": "2026-02-02"})
        assert r.status_code == 200
        d = r.json()
        assert d["exam"] == "SSC CGL" and len(d["plan"]) == 3
        assert d["teaching"]["response"] == "teaching text"

def test_start_rejects_unknown_exam():
    r = client.post("/study/start", json={"exam": "UNKNOWN EXAM"})
    assert "error" in r.json()

def test_question_and_answer_endpoints():
    r = client.get("/study/question?topic=Percentage")
    assert r.status_code == 200 and "question" in r.json()
    r2 = client.post("/study/answer", json={"exam": "SSC CGL", "topic": "Percentage", "answer": "A"})
    assert "correct" in r2.json()

def test_progress_endpoint():
    assert client.get("/study/progress?exam=SSC CGL").status_code == 200
    assert client.get("/study/exams").status_code == 200

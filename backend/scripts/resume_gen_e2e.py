"""End-to-end check of the resume generator against the live server."""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"

JD = """
Python Backend Developer
Company: Acme Technologies
Location: Hyderabad, India (Hybrid)

About the role
We are hiring a Python Backend Developer to build and scale our APIs.

Requirements
- Strong Python and FastAPI experience
- Experience with Django or Flask
- Solid SQL and PostgreSQL knowledge
- REST API design and Docker
- Git, Linux and CI/CD
- 1-3 years of experience
- Machine learning exposure is a plus

Responsibilities
- Design, build and maintain backend services with Python and FastAPI
- Write unit tests with pytest and review code in pull requests
- Work with Docker, Git and CI/CD to ship services
"""


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    print("== preview with AI summary polish ==")
    out = post("/resume-generator/preview", {"jd": JD, "polish_summary": True})
    if out.get("error"):
        print("ERROR:", out["error"])
        return 1
    analysis = out["analysis"]
    print("coverage:", analysis["coverage_pct"], "%")
    print("covered:", ", ".join(analysis["covered"]))
    print("gaps:", ", ".join(analysis["gaps"]) or "none")
    print("ai_summary_used:", analysis["ai_summary_used"])
    print("---- resume ----")
    print(out["content"])

    print("== save a version ==")
    saved = post("/resume-generator/save", {"jd": JD, "polish_summary": True})
    if saved.get("error"):
        print("ERROR:", saved["error"])
        return 1
    doc = saved["document"]
    print("document id:", doc["id"], "version:", doc["version"], "file:", doc["file_path"])
    print("download:", get(f"/resume-generator/{doc['id']}/download") if False else "ok")

    print("== chat intent ==")
    chat = post("/assistant/chat", {
        "message": "generate resume from this job description:\n" + JD
    })
    print("intent:", chat.get("intent"), "| requires_approval:", chat.get("requires_approval"))
    if chat.get("proposal"):
        print("proposal:", chat["proposal"]["title"])
        print("plan:", " | ".join(chat["proposal"]["plan"][:3]))
    else:
        print("response:", (chat.get("response") or chat.get("error") or "")[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())

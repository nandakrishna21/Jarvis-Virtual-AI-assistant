"""Create and install the JARVIS n8n workflows.

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\setup_n8n.py

Generates one n8n workflow JSON per JARVIS automation, imports them into the
local n8n instance and activates them so their webhook triggers answer.
"""
import json
import os
import pathlib
import subprocess
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / "automation" / "n8n_workflows"
N8N_HOME = os.environ.get("N8N_USER_FOLDER", r"C:\JARVIS\n8n")
JARVIS_API = os.environ.get("JARVIS_API_URL", "http://127.0.0.1:8000")

WORKFLOWS = [
    {
        "key": "job_discovery",
        "name": "JARVIS - Job Discovery",
        "path": "jarvis/job-discovery",
        "method": "POST",
        "endpoint": "/jobs/search",
        "description": "Collect and score new job listings against the active resume.",
    },
    {
        "key": "daily_report",
        "name": "JARVIS - Daily Report",
        "path": "jarvis/daily-report",
        "method": "GET",
        "endpoint": "/analytics/overview",
        "description": "Daily job-search summary: discoveries, matches, applications, approvals.",
    },
    {
        "key": "application_follow_up",
        "name": "JARVIS - Application Follow-up",
        "path": "jarvis/application-follow-up",
        "method": "GET",
        "endpoint": "/applications",
        "description": "List applications that may need a follow-up. Drafts only, never auto-sent.",
    },
    {
        "key": "interview_reminders",
        "name": "JARVIS - Interview Reminders",
        "path": "jarvis/interview-reminders",
        "method": "GET",
        "endpoint": "/interviews",
        "description": "Upcoming interviews and reminder status.",
    },
    {
        "key": "gmail_review",
        "name": "JARVIS - Gmail Review",
        "path": "jarvis/gmail-review",
        "method": "POST",
        "endpoint": "/emails/fetch",
        "description": "Fetch recruiter and interview email for a digest.",
    },
]


def _uid() -> str:
    return str(uuid.uuid4())


def build_workflow(spec: dict) -> dict:
    http_params = {
        "method": spec["method"],
        "url": f"{JARVIS_API}{spec['endpoint']}",
        "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
        "options": {"timeout": 120000},
    }
    if spec["method"] == "POST":
        http_params["sendBody"] = True
        http_params["specifyBody"] = "json"
        http_params["jsonBody"] = "={{ JSON.stringify($json.body ?? $json) }}"
        http_params["options"] = {"timeout": 120000}

    webhook_params = {
        "httpMethod": spec["method"],
        "path": spec["path"],
        "responseMode": "lastNode",
        "options": {},
    }

    return {
        "name": spec["name"],
        "nodes": [
            {
                "parameters": webhook_params,
                "id": _uid(),
                "name": "Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [0, 0],
                "webhookId": f"jarvis-{spec['key']}",
            },
            {
                "parameters": http_params,
                "id": _uid(),
                "name": "Call JARVIS API",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [240, 0],
            },
        ],
        "connections": {
            "Trigger": {"main": [[{"node": "Call JARVIS API", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
        "active": False,
        "pinData": {},
        "meta": {"description": spec["description"]},
        "tags": [],
    }


def write_workflows() -> list[pathlib.Path]:
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for spec in WORKFLOWS:
        path = WORKFLOW_DIR / f"{spec['key']}.json"
        path.write_text(json.dumps(build_workflow(spec), indent=2), encoding="utf-8")
        paths.append(path)
        print(f"wrote {path}")
    return paths


def _n8n_env() -> dict:
    env = os.environ.copy()
    env["N8N_USER_FOLDER"] = N8N_HOME
    env.setdefault("N8N_HOST", "127.0.0.1")
    env.setdefault("N8N_PORT", "5678")
    env.setdefault("N8N_USER_MANAGEMENT_DISABLED", "true")
    return env


def run_cli(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["n8n.cmd", *args],
        cwd=str(ROOT),
        env=_n8n_env(),
        capture_output=True,
        text=True,
        shell=False,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def install(paths: list[pathlib.Path]) -> bool:
    ok = True
    for path in paths:
        code, out = run_cli(["import:workflow", "--input", str(path)])
        status = "OK" if code == 0 else "FAILED"
        print(f"import {path.name}: {status}")
        if code != 0:
            ok = False
            print(out[-800:])
    code, out = run_cli(["update:workflow", "--all", "--active=true"])
    print(f"activate all workflows: {'OK' if code == 0 else 'FAILED'}")
    if code != 0:
        ok = False
        print(out[-800:])
    return ok


def main() -> int:
    print(f"n8n home : {N8N_HOME}")
    print(f"jarvis api: {JARVIS_API}")
    paths = write_workflows()
    if "--no-install" in sys.argv:
        print("skipping install (--no-install)")
        return 0
    return 0 if install(paths) else 1


if __name__ == "__main__":
    raise SystemExit(main())

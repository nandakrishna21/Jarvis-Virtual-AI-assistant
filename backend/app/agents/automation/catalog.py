"""Automation catalog.

Each entry maps a JARVIS automation to an n8n workflow webhook path and to a
native fallback that runs inside the backend when n8n is not running. The
catalog is the single place where a workflow is described.
"""

WORKFLOWS = [
    {
        "name": "job_discovery",
        "title": "Job Discovery",
        "webhook": "job-discovery",
        "description": "Collect new listings from every configured source, normalise them, remove duplicates and score them against your active resume.",
        "steps": [
            "Read job preferences from Settings",
            "Collect listings from configured public sources",
            "Normalise and deduplicate by normalised URL",
            "Classify role, seniority, work mode and employment type",
            "Score each job against the active resume (35/25/20/10/10)",
            "Save results and notify about high-quality matches",
        ],
        "cadence": "Every 4 hours",
        "native": "job_discovery",
    },
    {
        "name": "daily_report",
        "title": "Daily Report",
        "webhook": "daily-report",
        "description": "Summarise jobs discovered, qualified matches, applications, pending approvals and upcoming interviews for the day.",
        "steps": [
            "Count jobs discovered today",
            "Count qualified matches (score >= 60)",
            "Identify the top five opportunities",
            "Count applications by status",
            "List pending approvals",
            "Generate the daily summary",
        ],
        "cadence": "Once daily at 07:00",
        "native": "morning_report",
    },
    {
        "name": "application_follow_up",
        "title": "Application Follow-up",
        "webhook": "application-follow-up",
        "description": "List applications that have gone quiet and draft a follow-up message. Drafts only - sending still needs your approval.",
        "steps": [
            "Find applications with no response beyond the follow-up interval",
            "Draft a polite follow-up for each",
            "Create a pending approval for every draft",
            "Do not send anything automatically",
        ],
        "cadence": "Every 3 days",
        "native": "application_follow_up",
    },
    {
        "name": "interview_reminders",
        "title": "Interview Reminders",
        "webhook": "interview-reminders",
        "description": "Notify about interviews happening in the next 24 hours and create a task for each one.",
        "steps": [
            "Find interviews scheduled within 24 hours",
            "Create a task for each upcoming interview",
            "Mark the reminder as sent",
        ],
        "cadence": "Every 6 hours",
        "native": "interview_reminders",
    },
    {
        "name": "gmail_review",
        "title": "Gmail Review",
        "webhook": "gmail-review",
        "description": "Fetch new recruiter and interview emails and build a short digest.",
        "steps": [
            "Fetch unread recruiter and interview emails",
            "Categorise each message",
            "Extract company, role and dates",
            "Build the digest",
        ],
        "cadence": "Twice daily",
        "native": "gmail_review",
    },
]

BY_NAME = {w["name"]: w for w in WORKFLOWS}


def get(name: str) -> dict | None:
    return BY_NAME.get(name)


def all_workflows() -> list[dict]:
    return [
        {k: v for k, v in w.items() if k != "native"} | {"native_fallback": w["native"]}
        for w in WORKFLOWS
    ]

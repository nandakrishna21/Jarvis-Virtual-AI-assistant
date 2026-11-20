import re, base64, json, hashlib
from datetime import datetime
from app.database.session import SessionLocal
from app.database.models import Email, EmailDraft, EmailApproval

RECRUITER_PATTERNS = [
    r"recruit", r"hiring", r"candidate", r"interview", r"assessment", r"your application",
    r"job alert", r"job opening", r"shortlist", r"resume", r"cv review", r"talent acquisition",
]
SPAM_PATTERNS = [r"lottery", r"crypto giveaway", r"wire transfer", r"you have won", r"viagra"]
INTERVIEW_PATTERNS = [r"interview", r"schedule", r"technical round", r"hr round", r"availability"]
ASSESSMENT_PATTERNS = [r"assessment", r"coding test", r"hackerrank", r"hackerearth", r"aptitude test", r"oa link"]
JOBALERT_PATTERNS = [r"new job", r"jobs for you", r"job alert", r"recommended job", r"matching job", r"new openings"]
COMPANY_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9&.\- ]{1,30}(?:Technologies|Systems|Labs|Solutions|Software|Services|AI|InfoTech|Consulting))\b")
ROLE_PATTERN = re.compile(r"(?:position|role|for)\s+(?:an?\s+)?([A-Za-z][A-Za-z/ +\-]{2,40}?)(?:\s*[-–—]|\s+at\s|\.|\,|$)", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b")

def classify(subject: str, snippet: str) -> str:
    text = f"{subject} {snippet}".lower()
    if any(re.search(p, text) for p in SPAM_PATTERNS):
        return "spam"
    if any(re.search(p, text) for p in INTERVIEW_PATTERNS):
        return "interview"
    if any(re.search(p, text) for p in ASSESSMENT_PATTERNS):
        return "assessment"
    if any(re.search(p, text) for p in JOBALERT_PATTERNS):
        return "job_alert"
    if any(re.search(p, text) for p in RECRUITER_PATTERNS):
        return "recruiter"
    return "other"

def extract_details(subject: str, body: str) -> dict:
    text = f"{subject}\n{body}"
    company = None
    m = COMPANY_PATTERN.search(text)
    if m:
        company = m.group(1).strip()
    role = None
    rm = ROLE_PATTERN.search(text)
    if rm:
        role = rm.group(1).strip()
    dates = DATE_PATTERN.findall(text)
    return {"company": company, "job_role": role, "dates": dates[:5]}

def fetch_and_store(max_results: int = 25, query: str = "newer_than:14d") -> list[dict]:
    from app.integrations import gmail_client
    service = gmail_client.build_service(gmail_client.SCOPES_READONLY)
    listing = service.users().messages().list(userId="me", maxResults=max_results, q=query).execute()
    db = SessionLocal()
    out = []
    recruiter_new = []
    try:
        for item in listing.get("messages", []):
            msg = service.users().messages().get(userId="me", id=item["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            body = _extract_body(msg.get("payload", {}))
            subject = headers.get("subject", "")
            snippet = msg.get("snippet", "")
            sender = headers.get("from", "")
            category = classify(subject, snippet)
            details = extract_details(subject, body)
            row = db.query(Email).filter(Email.gmail_id == item["id"]).first()
            is_new = row is None
            if not row:
                row = Email(gmail_id=item["id"])
                db.add(row)
            row.sender = sender; row.subject = subject; row.snippet = snippet; row.body = body[:20000]
            row.received_at = headers.get("date", "")
            row.category = category
            row.company = details["company"]; row.job_role = details["job_role"]
            row.important_details = json.dumps({"dates": details["dates"]})
            db.flush()
            if is_new and category in ("recruiter", "interview", "assessment"):
                recruiter_new.append(f"{category}: {subject} ({details['company'] or sender})")
            out.append({"id": row.id, "sender": sender, "company": row.company, "subject": subject,
                        "received_at": row.received_at, "job_role": row.job_role,
                        "category": category, "important_details": details["dates"], "body": body[:1500]})
        db.commit()
        if recruiter_new:
            from app.services.notifications import notify_safe

            notify_safe(
                db,
                f"{len(recruiter_new)} new recruiter/interview email(s)",
                "\n".join(recruiter_new[:10]),
                "info",
                "/",
            )
    finally:
        db.close()
    return out

def _extract_body(payload: dict) -> str:
    if not payload:
        return ""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "ignore")
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", "ignore")
    return ""

def create_draft(email_id: int, reply_body: str | None = None) -> dict:
    db = SessionLocal()
    try:
        em = db.get(Email, email_id)
        if not em:
            return {"error": "email not found"}
        subject = em.subject if em.subject.lower().startswith("re:") else f"Re: {em.subject}"
        body = reply_body or (
            "Hi,\n\nThank you for reaching out regarding this opportunity. "
            "I am interested and would be happy to provide further details.\n\nBest regards"
        )
        draft = EmailDraft(email_id=email_id, recipient=em.sender, subject=subject, body=body, attachments="")
        db.add(draft); db.flush()
        snapshot = json.dumps({"draft_id": draft.id, "recipient": draft.recipient, "cc": None, "bcc": None,
                               "subject": draft.subject, "body": draft.body, "attachments": [],
                               "hash": hashlib.sha256(draft.body.encode()).hexdigest()[:12]})
        appr = EmailApproval(draft_id=draft.id, action="send_email", content_snapshot=snapshot)
        db.add(appr); db.commit()
        return {"draft_id": draft.id, "approval_id": appr.id, "recipient": draft.recipient,
                "subject": draft.subject, "body": draft.body, "hash": json.loads(snapshot)["hash"],
                "sent": False, "warning": "Draft only. Nothing sent until you approve the exact message."}
    finally:
        db.close()

def approve_send(approval_id: int) -> dict:
    """Approve then send. Sending requires gmail.send scope in token; blocked otherwise."""
    from app.integrations import gmail_client
    db = SessionLocal()
    try:
        appr = db.get(EmailApproval, approval_id)
        if not appr:
            return {"error": "approval not found"}
        if appr.status != "pending":
            return {"error": f"already {appr.status}"}
        snap = json.loads(appr.content_snapshot)
        draft = db.get(EmailDraft, appr.draft_id)
        if draft.body != snap["body"] or draft.recipient != snap["recipient"] or draft.subject != snap["subject"]:
            return {"error": "draft changed since approval request; review and create a new approval"}
        creds = gmail_client.load_credentials(gmail_client.SCOPES_SEND)
        if not creds:
            return {"error": "no stored Gmail credentials; run scripts/gmail_auth.py --send"}
        scopes = creds.scopes or []
        if "https://www.googleapis.com/auth/gmail.send" not in scopes:
            return {"error": "token lacks gmail.send scope; re-authenticate with scripts/gmail_auth.py --send"}
        appr.status = "approved"; appr.decided_at = datetime.utcnow()
        draft.status = "approved"
        db.commit()
        return send_draft(draft.id, approval_id)
    finally:
        db.close()

def reject_send(approval_id: int) -> dict:
    """Reject a pending email approval. Cancels the draft; never sends."""
    db = SessionLocal()
    try:
        appr = db.get(EmailApproval, approval_id)
        if not appr:
            return {"error": "approval not found"}
        if appr.status != "pending":
            return {"error": f"already {appr.status}"}
        appr.status = "rejected"
        appr.decided_at = datetime.utcnow()
        draft = db.get(EmailDraft, appr.draft_id)
        if draft:
            draft.status = "rejected"
        db.commit()
        return {"approval_id": approval_id, "status": "rejected", "sent": False,
                "next": "none"}
    finally:
        db.close()

def send_draft(draft_id: int, approval_id: int | None = None) -> dict:
    from app.integrations import gmail_client
    db = SessionLocal()
    try:
        draft = db.get(EmailDraft, draft_id)
        if not draft:
            return {"error": "draft not found"}
        if draft.status not in ("approved",):
            return {"error": "draft is not approved; approve the exact message first"}
        if approval_id is not None:
            appr = db.get(EmailApproval, approval_id)
            if not appr or appr.status != "approved":
                return {"error": "approval missing or not approved"}
        service = gmail_client.build_service(gmail_client.SCOPES_SEND)
        raw = f"To: {draft.recipient}\r\nSubject: {draft.subject}\r\n\r\n{draft.body}"
        body = {"raw": base64.urlsafe_b64encode(raw.encode()).decode()}
        sent = service.users().messages().send(userId="me", body=body).execute()
        draft.status = "sent"
        db.commit()
        return {"sent": True, "gmail_message_id": sent.get("id"), "draft_id": draft_id,
                "recipient": draft.recipient, "subject": draft.subject}
    finally:
        db.close()

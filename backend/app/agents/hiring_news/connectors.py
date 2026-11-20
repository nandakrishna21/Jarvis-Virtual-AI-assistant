import html as html_lib
import json
import re
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 JARVIS-local/0.1 (personal assistant)"}

# kind="announcement": company hiring posts (must mention hiring intent).
# kind="jobs": direct job postings (a posting is itself the announcement).
SOURCES = [
    {"name": "hn_hiring", "kind": "announcement", "url": "https://hn.algolia.com/api/v1/search_by_date",
     "params": {"query": "Ask HN: Who is hiring", "tags": "story", "hitsPerPage": 6}},
    {"name": "weworkremotely", "kind": "jobs", "url": "https://weworkremotely.com/remote-jobs.rss"},
    {"name": "remotive", "kind": "jobs", "url": "https://remotive.com/api/remote-jobs?limit=50"},
    {"name": "arbeitnow", "kind": "jobs", "url": "https://www.arbeitnow.com/api/job-board-api"},
]

RSS_SOURCES = [(s["name"], s["url"]) for s in SOURCES]

HIRING_KEYWORDS = [
    "hiring", "we are hiring", "now hiring", "open roles", "open positions", "job openings",
    "vacancies", "join our team", "career opportunities", "new openings", "recruiting",
]
ROLE_KEYWORDS = [
    "python", "django", "fastapi", "backend", "full stack", "ai engineer", "ai agent",
    "generative ai", "machine learning", "software engineer", "developer", "api engineer",
    "automation engineer", "junior", "fresher", "graduate",
]
ROLE_KEYWORD_WEIGHTS = [
    ("python", 4), ("django", 4), ("fastapi", 4), ("generative ai", 4), ("ai agent", 4),
    ("ai engineer", 3), ("machine learning", 3), ("backend", 3), ("full stack", 2),
    ("api engineer", 3), ("automation engineer", 3), ("software engineer", 2),
    ("developer", 1), ("junior", 2), ("fresher", 2), ("graduate", 2),
]
FRESH_DAYS = 45


def _parse_date(raw) -> datetime | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except Exception:
            return None
    raw = str(raw).strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%d %B %Y", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(raw.replace("Z", "+0000"), fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


async def fetch_source(src: dict, client: httpx.AsyncClient) -> list[dict]:
    name = src["name"]
    last_status = None
    for attempt in range(3):
        try:
            r = await client.get(src["url"], params=src.get("params"), timeout=30)
            last_status = r.status_code
            if r.status_code == 200:
                break
            if r.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(2 * (attempt + 1))
                continue
            return []
        except Exception:
            await asyncio.sleep(1 * (attempt + 1))
    else:
        return []
    if last_status != 200:
        return []
    try:
        if name == "hn_hiring":
            return _parse_hn_hiring(r.json())
        if name == "remotive":
            return _parse_remotive_json(r.text, name)
        if name == "arbeitnow":
            return _parse_arbeitnow_json(r.text, name)
        return _parse_rss(r.text, name)
    except Exception:
        return []


async def fetch_feed(name: str, url: str, client: httpx.AsyncClient) -> list[dict]:
    src = next((s for s in SOURCES if s["name"] == name), None)
    if src:
        return await fetch_source(src, client)
    return _parse_rss((await client.get(url, timeout=30)).text, name)


def _parse_rss(xml_text: str, source: str) -> list[dict]:
    out = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return out
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)
    for item in items:
        def text_of(tag):
            el = item.find(tag)
            if el is None and tag.startswith("atom:"):
                el = item.find(tag.replace("atom:", "atom:"), ns)
            if el is None:
                return ""
            return (el.text or "").strip()
        title = text_of("title")
        link = text_of("link")
        if not link:
            el = item.find("atom:link", ns)
            link = el.get("href") if el is not None else ""
        desc_raw = text_of("description") or text_of("atom:summary")
        desc = _strip_html(desc_raw)
        pub = text_of("pubDate") or text_of("atom:published") or text_of("atom:updated")
        region = text_of("region")
        country = text_of("country")
        skills = text_of("skills")
        category = text_of("category")
        emp_type = text_of("type")
        location = ", ".join([p for p in (region, country) if p]) or _extract_location(desc)
        if skills:
            desc = f"{skills}. {category}. {desc}".strip()
        if emp_type:
            desc = f"{desc} Employment type: {emp_type}."
        company, role = _split_title(title)
        if not company and ":" in title:
            company, role = [p.strip() for p in title.split(":", 1)]
        out.append({
            "company": company, "role": role, "title": title, "description": desc[:800],
            "location": location, "experience": _extract_experience(desc),
            "salary": _extract_salary(desc), "posting_date": pub,
            "source": source, "official_source": None, "application_url": link,
        })
    return out


def _parse_remotive_json(text: str, source: str) -> list[dict]:
    out = []
    try:
        data = json.loads(text)
    except Exception:
        return out
    for j in data.get("jobs", []):
        desc = _strip_html(j.get("description", ""))[:800]
        out.append({
            "company": j.get("company_name") or "", "role": j.get("title") or "",
            "title": j.get("title") or "", "description": desc,
            "location": (j.get("candidate_required_location") or "").lower(),
            "experience": "", "salary": "", "posting_date": j.get("publication_date") or "",
            "source": source, "official_source": j.get("url"), "application_url": j.get("url"),
        })
    return out


def _parse_arbeitnow_json(text: str, source: str) -> list[dict]:
    out = []
    try:
        data = json.loads(text)
    except Exception:
        return out
    for j in data.get("data", []):
        desc = _strip_html(j.get("description", ""))[:800]
        title = j.get("title") or ""
        created = j.get("created_at")
        if isinstance(created, (int, float)):
            created = datetime.fromtimestamp(float(created), tz=timezone.utc).isoformat()
        out.append({
            "company": j.get("company_name") or "", "role": title,
            "title": title, "description": desc,
            "location": j.get("location") or "", "experience": "",
            "salary": "", "posting_date": created or "",
            "source": source, "official_source": j.get("url"), "application_url": j.get("url"),
        })
    return out


def _decode_hn(text: str) -> str:
    text = html_lib.unescape(text or "")
    text = re.sub(r"<p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\u2028", " ").replace("\u00a0", " ").strip()


def _parse_hn_hiring(data: dict) -> list[dict]:
    """Parse Hacker News 'Ask HN: Who is hiring' threads into company/role/location records."""
    out = []
    stories = data.get("hits") or []
    for story in stories:
        title = story.get("title") or ""
        if "who is hiring" not in title.lower():
            continue
        story_id = story.get("objectID")
        posted = story.get("created_at")
        if not story_id:
            continue
        out.extend(_parse_hn_thread(story_id, posted, title))
    return out


def _parse_hn_thread(story_id: str, posted: str | None, thread_title: str) -> list[dict]:
    import httpx

    try:
        r = httpx.get(f"https://hn.algolia.com/api/v1/items/{story_id}", headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return []
        tree = r.json()
    except Exception:
        return []

    out = []
    for node in tree.get("children") or []:
        body = _decode_hn(node.get("text") or "")
        if not body:
            continue
        first = body.split("\n", 1)[0].strip()
        if "|" not in first:
            continue
        parts = [html_lib.unescape(p).strip() for p in first.split("|")]
        parts = [p for p in parts if p]
        if len(parts) < 2:
            continue
        company = parts[0]
        role = parts[1]
        location = ""
        work_mode = ""
        salary = ""
        url = ""
        for p in parts[2:]:
            low = p.lower()
            if low.startswith(("remote", "onsite", "on-site", "hybrid")):
                work_mode = p
            elif re.search(r"[$₹€£]|\b(?:k|lpa|usd|eur|inr)\b|\b(?:per year|per month|/yr)\b", low):
                salary = p
            elif p.lower().startswith("http"):
                url = p
            elif not location:
                location = p
        if not location:
            location = work_mode
        node_id = node.get("id") or story_id
        out.append({
            "company": company[:200],
            "role": role[:200],
            "title": f"{company} - {role}",
            "description": body[:800],
            "location": location[:120],
            "experience": _extract_experience(body),
            "salary": salary[:80],
            "posting_date": posted or "",
            "source": "hn_hiring",
            "official_source": f"https://news.ycombinator.com/item?id={story_id}",
            "application_url": url or f"https://news.ycombinator.com/item?id={node_id}",
            "thread_title": thread_title,
        })
    return out


def _split_title(title: str) -> tuple[str, str]:
    for sep in [" is hiring ", " are hiring ", " hiring ", " at ", " @ ", " - ", " — ", ": "]:
        if sep in title:
            a, b = title.split(sep, 1)
            a, b = a.strip(), b.strip()
            if sep in (" is hiring ", " are hiring ", " hiring "):
                return a, b
            if len(a) < 60 and len(b) < 80:
                return a, b
    return "", title.strip()


def _extract_location(text: str) -> str:
    m = re.search(r"(?:location|based in|remote)\s*[:\-]\s*([A-Za-z ,]{3,40})", text, re.I)
    if m:
        return m.group(1).strip()
    if re.search(r"\bremote\b", text, re.I):
        return "Remote"
    return ""


def _extract_experience(text: str) -> str:
    m = re.search(r"(\d+\s*[-–+]?\s*\d*\s*(?:\+)?\s*(?:years?|yrs?)[^.,;]{0,20})", text, re.I)
    return m.group(1).strip() if m else ""


def _extract_salary(text: str) -> str:
    m = re.search(r"(?:₹|rs\.?|inr|\$|usd|€)\s?[\d,]+(?:\s?[-–]\s?[\d,]+)?(?:\s*(?:k| lakh|lpa|/yr|per year|month))?", text, re.I)
    if m:
        return m.group(0).strip()
    m2 = re.search(r"\b[\d,.]+\s*(?:lpa|lakh[s]?|ctc|k\s?(?:per\s?month|/yr|per year))\b", text, re.I)
    return m2.group(0).strip() if m2 else ""


def is_hiring_related(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in HIRING_KEYWORDS)


def role_relevance(text: str) -> int:
    low = text.lower()
    score = 0
    for keyword, weight in ROLE_KEYWORD_WEIGHTS:
        if keyword in low:
            score += weight
    return score


SENIOR_MARKERS = ["senior", "staff", "principal", "lead", "manager", "head of", "director",
                  "vp", "architect", "expert", "sr.", "sr "]


def item_relevance(item: dict) -> int:
    """Role/title relevance weighted higher than body text, with seniority penalty."""
    primary = role_relevance(f"{item.get('role') or ''} {item.get('title') or ''}")
    secondary = min(2, role_relevance(item.get("description") or ""))
    score = primary * 2 + secondary
    blob = f"{item.get('role') or ''} {item.get('title') or ''}".lower()
    if any(marker in blob for marker in SENIOR_MARKERS):
        score -= 3
    return max(score, 0)


def is_fresh(posting_date: str | None, days: int = FRESH_DAYS) -> bool:
    dt = _parse_date(posting_date)
    if dt is None:
        return False
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)

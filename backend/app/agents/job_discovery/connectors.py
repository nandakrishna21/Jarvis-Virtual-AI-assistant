"""Job connectors.

Two kinds of permitted public sources:

1. **Structured public APIs** (preferred) - key-free JSON feeds that actually
   honour a search query and return title, company, location, tags and the
   full description: Remotive, Arbeitnow, RemoteOK, Himalayas.
2. **Public listing pages** (fallback) - Wellfound and Hirist HTML. These are
   scraped from the public page only, no auth or CAPTCHA bypass.

Every job keeps its original URL and is marked `unverified` until you open the
source yourself.
"""
import asyncio
import re
import httpx
from html import unescape

HEADERS = {"User-Agent": "Mozilla/5.0 JARVIS-local", "Accept": "application/json, text/html"}

SOURCE_DOMAINS = {
    "wellfound": "https://wellfound.com",
    "hirist": "https://www.hirist.com",
}

SEPARATORS = "\u2022\u00b7\uFFFD|"

REMOTE_HINTS = ("remote", "anywhere", "worldwide", "work from home", "wfh", "distributed", "global")
INDIA_HINTS = ("india", "hyderabad", "bangalore", "bengaluru", "pune", "mumbai", "chennai",
               "delhi", "noida", "gurugram", "gurgaon", "kolkata", "ahmedabad", "jaipur",
               "coimbatore", "madurai", "kochi", "thiruvananthapuram")

SENIORITY_BLOCKERS = (
    "principal", "distinguished", "fellow", "vice president", "vp", "chief", "cto", "ceo",
    "coo", "director", "head of", "global head", "svp", "evp", "partner",
)
SENIORITY_HIGH = ("senior", "lead", "staff", "principal", "architect", "manager", "director",
                   "head", "expert")
SENIORITY_ENTRY = ("junior", "entry", "graduate", "fresher", "trainee", "intern", "associate",
                   "apprentice", "graduate trainee")


def _is_remote(text: str) -> bool:
    low = (text or "").lower()
    return any(h in low for h in REMOTE_HINTS)


def _is_india(text: str) -> bool:
    low = (text or "").lower()
    return any(h in low for h in INDIA_HINTS)


def _seniority_of(text: str) -> str:
    low = (text or "").lower()
    for word in SENIORITY_BLOCKERS:
        if re.search(rf"\b{re.escape(word)}\b", low):
            return "executive"
    for word in SENIORITY_HIGH:
        if re.search(rf"\b{re.escape(word)}\b", low):
            return "senior"
    for word in SENIORITY_ENTRY:
        if re.search(rf"\b{re.escape(word)}\b", low):
            return "entry"
    # explicit years, e.g. "1 year(s)" or "2-3 years"
    m = re.search(r"(\d+)\s*(?:-\s*(\d+)\s*)?year", low)
    if m:
        low_years = int(m.group(1))
        if low_years == 0:
            return "entry"
        if low_years <= 3:
            return "mid"
        return "senior"
    if "no experience" in low or "fresher" in low or "not required" in low:
        return "entry"
    return "unspecified"


def _query_tokens(query: str) -> list[str]:
    stop = {
        "a", "an", "the", "for", "in", "at", "of", "and", "or", "to", "job", "jobs", "role",
        "roles", "position", "positions", "opening", "openings", "vacancy", "vacancies",
        "developer", "engineer", "looking", "find", "me", "my", "show", "give", "list",
        "get", "search", "apply",
    }
    tokens = re.findall(r"[a-z0-9+#.]+", (query or "").lower())
    return [t for t in tokens if t not in stop and len(t) > 1]


def relevance(job: dict, query: str, require_entry: bool = False) -> float:
    """How well a job matches the query. 0.0 means drop it."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "")[:1500].lower()
    tags = " ".join(job.get("tags") or []).lower()
    haystack = f"{title} {tags} {desc}"

    tokens = _query_tokens(query)
    if not tokens:
        return 0.5
    hits = sum(1 for t in tokens if t in title)
    soft = sum(1 for t in tokens if t in haystack and t not in title)
    score = (hits * 1.0 + soft * 0.6) / len(tokens)

    if require_entry and _seniority_of(title) in ("executive", "senior"):
        score *= 0.3
    return round(score, 3)


async def fetch_jobs(query: str, location: str = "India", max_results: int = 5,
                     require_entry: bool = True) -> list[dict]:
    """Fetch from permitted public sources only. No bypass of auth/CAPTCHA/paywalls."""
    api_jobs: list[dict] = []
    html_jobs: list[dict] = []
    try:
        api_jobs = await _fetch_api_sources(query, location)
    except Exception:
        api_jobs = []
    try:
        html_jobs = await _fetch_html_sources(query, location)
    except Exception:
        html_jobs = []

    jobs = dedupe(api_jobs + html_jobs)
    jobs = [j for j in jobs if relevance(j, query, require_entry) > 0.12]
    jobs.sort(key=lambda j: relevance(j, query, require_entry), reverse=True)
    return jobs[:max_results]


# ---------- structured public APIs ----------

async def _get_json(client: httpx.AsyncClient, url: str, params: dict | None = None):
    try:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


async def _fetch_api_sources(query: str, location: str) -> list[dict]:
    jobs: list[dict] = []
    async with httpx.AsyncClient(timeout=25, headers=HEADERS, follow_redirects=True) as c:
        remotive = await _get_json(c, "https://remotive.com/api/remote-jobs", {"search": query})
        if isinstance(remotive, dict):
            for j in remotive.get("jobs", []) or []:
                jobs.append(_norm_remotive(j))

        arbeitnow = await _get_json(c, "https://www.arbeitnow.com/api/job-board-api")
        if isinstance(arbeitnow, dict):
            for j in arbeitnow.get("data", []) or []:
                jobs.append(_norm_arbeitnow(j))

        remoteok = await _get_json(c, "https://remoteok.com/api")
        if isinstance(remoteok, list):
            for j in remoteok[1:]:
                if isinstance(j, dict):
                    jobs.append(_norm_remoteok(j))

        himalayas = await _get_json(c, "https://himalayas.app/jobs/api",
                                    {"limit": 50, "query": query})
        if isinstance(himalayas, dict):
            for j in himalayas.get("jobs", []) or []:
                jobs.append(_norm_himalayas(j))
    jobs.extend(await _fetch_internshala(query, location))
    return jobs


# ---------- Internshala (India junior / internship roles) ----------

_INTERN_CARD = re.compile(
    r'id="individual_internship_(?P<id>\d+)"(?P<attrs>[^>]*)>(?P<body>.*?)'
    r'(?=id="individual_internship_|\Z)',
    re.S | re.I,
)
_INTERN_TITLE = re.compile(r'class="job-title-href"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<text>.*?)</a>', re.S | re.I)
_INTERN_COMPANY = re.compile(r'class="company-name"[^>]*>(?P<text>.*?)</p>', re.S | re.I)
_INTERN_LOCATION = re.compile(
    r'class="row-1-item\s+locations"[^>]*>(?P<text>.*?)</p>', re.S | re.I)
_INTERN_SALARY = re.compile(r'class="desktop"[^>]*>(?P<text>.*?)</span>', re.S | re.I)
_INTERN_EXPERIENCE = re.compile(
    r'ic-16-briefcase[\s\S]{0,400}?</i>(?P<text>[\s\S]{0,200}?)</div>', re.S | re.I)
_INTERN_SKILL = re.compile(r"class='job_skill'>(?P<text>.*?)</div>", re.S | re.I)
_INTERN_CATEGORY = re.compile(r'class="category_name"[^>]*>(?P<text>.*?)</div>', re.S | re.I)
_INTERN_ABOUT = re.compile(r'class="about_job"[^>]*>[\s\S]{0,300}?class="text"[^>]*>(?P<text>.*?)</div>', re.S | re.I)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _internshala_urls(query: str, location: str) -> list[str]:
    """Internshala filters properly on slug URLs, not on ?query=.

    The exact role slug is often not a filter the site recognises, so known
    role slugs are tried too.
    """
    role = _slugify(query)
    place = _slugify(location or "india") or "india"
    urls: list[str] = []
    if role:
        urls.append(f"https://internshala.com/jobs/{role}-jobs-in-{place}")
        for alt in ("python-developer", "backend-developer", "ai-engineer",
                    "data-science", "full-stack-developer"):
            if alt != role:
                urls.append(f"https://internshala.com/jobs/{alt}-jobs-in-{place}")
    return urls[:4]


async def _fetch_internshala(query: str, location: str, limit: int = 30) -> list[dict]:
    """Public Internshala listings. India-focused junior and internship roles."""
    urls = _internshala_urls(query, location)
    if not urls:
        return []

    async def _one(client: httpx.AsyncClient, url: str) -> list[dict]:
        try:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            return _parse_internshala(r.text, limit)
        except Exception:
            return []

    try:
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as c:
            batches = await asyncio.gather(*[_one(c, u) for u in urls])
    except Exception:
        return []
    jobs: list[dict] = []
    for batch in batches:
        jobs.extend(batch)
    return jobs[: limit * 2]


def _parse_internshala(html: str, limit: int) -> list[dict]:
    out: list[dict] = []
    for m in _INTERN_CARD.finditer(html):
        if len(out) >= limit:
            break
        body = m.group("body")
        title_m = _INTERN_TITLE.search(body)
        if not title_m:
            continue
        href = title_m.group("href")
        if href.startswith("/"):
            href = "https://internshala.com" + href
        title = _clean(title_m.group("text"))
        if not title:
            continue
        company_m = _INTERN_COMPANY.search(body)
        company = _clean(company_m.group("text")) if company_m else None
        loc_m = _INTERN_LOCATION.search(body)
        loc = _clean(loc_m.group("text")) if loc_m else None
        sal_m = _INTERN_SALARY.search(body)
        salary = _clean(sal_m.group("text")) if sal_m else None
        exp_m = _INTERN_EXPERIENCE.search(body)
        experience = _clean(exp_m.group("text")) if exp_m else None
        skills = [_clean(s.group("text")) for s in _INTERN_SKILL.finditer(body)]
        cats = [_clean(s.group("text")) for s in _INTERN_CATEGORY.finditer(body)]
        about_m = _INTERN_ABOUT.search(body)
        about = _clean(about_m.group("text")) if about_m else ""
        if loc:
            loc = loc.split("\u2022")[0].strip() or loc
        out.append({
            "title": title,
            "company": company,
            "location": loc,
            "job_type": "remote" if (loc and "home" in loc.lower()) else None,
            "url": href,
            "description": about,
            "required_skills": "",
            "tags": [t for t in (skills + cats) if t][:12],
            "salary": salary,
            "experience": experience,
            "posting_date": None,
            "source": "internshala",
            "seniority": _seniority_of(f"{title} {experience or ''}"),
            "employment_type": "Full-time",
            "verified": "unverified",
        })
    return out


def _strip_html(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text or "", flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _date_str(value) -> str | None:
    """Feeds use ISO strings, epoch seconds or datetimes. Normalise to a date."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            from datetime import datetime, timezone

            return datetime.fromtimestamp(float(value), tz=timezone.utc).date().isoformat()
        except (ValueError, OSError, OverflowError):
            return None
    text = str(value)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    return text[:10] or None


def _norm_remotive(j: dict) -> dict:
    title = j.get("title") or ""
    company = j.get("company_name") or ""
    loc = j.get("candidate_required_location") or "Remote"
    desc = _strip_html(j.get("description") or "")
    return {
        "title": title,
        "company": company,
        "location": loc,
        "job_type": "remote" if _is_remote(loc + " " + title) else None,
        "url": j.get("url") or "",
        "description": desc,
        "required_skills": "",
        "tags": [t for t in (j.get("tags") or []) if isinstance(t, str)],
        "salary": j.get("salary") or None,
        "experience": None,
        "posting_date": _date_str(j.get("publication_date")),
        "source": "remotive",
        "seniority": _seniority_of(title),
        "employment_type": j.get("job_type") or "",
        "verified": "unverified",
    }


def _norm_arbeitnow(j: dict) -> dict:
    title = j.get("title") or ""
    loc = j.get("location") or ""
    desc = _strip_html(j.get("description") or "")
    remote = bool(j.get("remote")) or _is_remote(title + " " + loc)
    tags = [t for t in (j.get("tags") or []) if isinstance(t, str)]
    return {
        "title": title,
        "company": j.get("company_name") or "",
        "location": "Remote" if remote and not loc else loc,
        "job_type": "remote" if remote else None,
        "url": j.get("url") or "",
        "description": desc,
        "required_skills": "",
        "tags": tags,
        "salary": None,
        "experience": None,
        "posting_date": _date_str(j.get("created_at")),
        "source": "arbeitnow",
        "seniority": _seniority_of(title),
        "employment_type": ", ".join(j.get("job_types") or []),
        "verified": "unverified",
    }


def _norm_remoteok(j: dict) -> dict:
    title = j.get("position") or ""
    loc = j.get("location") or "Remote"
    desc = _strip_html(j.get("description") or "")
    tags = [t for t in (j.get("tags") or []) if isinstance(t, str)]
    salary = ""
    if j.get("salary_min"):
        salary = f"{j.get('salary_min')} - {j.get('salary_max')}"
    return {
        "title": title,
        "company": j.get("company") or "",
        "location": loc,
        "job_type": "remote" if _is_remote(loc) else None,
        "url": j.get("url") or j.get("apply_url") or "",
        "description": desc,
        "required_skills": "",
        "tags": tags,
        "salary": salary or None,
        "experience": None,
        "posting_date": _date_str(j.get("date")),
        "source": "remoteok",
        "seniority": _seniority_of(title),
        "employment_type": "Full-time",
        "verified": "unverified",
    }


def _norm_himalayas(j: dict) -> dict:
    title = j.get("title") or ""
    desc = _strip_html(j.get("description") or "")
    loc = ", ".join(j.get("locationRestrictions") or []) or "Remote"
    salary = ""
    if j.get("minSalary"):
        salary = f"{j.get('minSalary')}-{j.get('maxSalary')} {j.get('currency', '')}".strip()
    raw_seniority = j.get("seniority")
    if isinstance(raw_seniority, list):
        raw_seniority = " ".join(str(s) for s in raw_seniority)
    return {
        "title": title,
        "company": j.get("companyName") or "",
        "location": loc,
        "job_type": "remote" if _is_remote(loc) else None,
        "url": j.get("applicationLink") or "",
        "description": desc,
        "required_skills": "",
        "tags": [t for t in (j.get("categories") or []) if isinstance(t, str)],
        "salary": salary or None,
        "experience": None,
        "posting_date": _date_str(j.get("pubDate")),
        "source": "himalayas",
        "seniority": (raw_seniority or "").strip().lower() or _seniority_of(title),
        "employment_type": j.get("employmentType") or "",
        "verified": "unverified",
    }


# ---------- public listing pages (fallback) ----------

async def _fetch_html_sources(query: str, location: str) -> list[dict]:
    jobs: list[dict] = []
    q = query.strip().replace(" ", "+")
    sources = [
        ("wellfound", f"https://wellfound.com/jobs?q={q}"),
        ("hirist", f"https://www.hirist.com/jobs?search={q}"),
    ]
    try:
        async with httpx.AsyncClient(timeout=25, headers=HEADERS, follow_redirects=True) as c:
            for name, url in sources:
                try:
                    r = await c.get(url)
                    if r.status_code != 200:
                        continue
                    jobs.extend(_parse_cards(r.text, name, 20))
                except Exception:
                    continue
    except Exception:
        pass
    return jobs


_JOB_ANCHOR = re.compile(
    r'<a[^>]+href="(?P<href>(?:https?://[^"]+)?/jobs?/(?!signup)[^"]+)"[^>]*>(?P<text>.*?)</a>',
    re.S | re.I,
)
_COMPANY_LINK = re.compile(r'href="(?:https?://[^"]+)?/company/(?P<slug>[^"/?#]+)"', re.I)
_META_SPAN = re.compile(r'<span[^>]*class="[^"]*text-gray-700[^"]*"[^>]*>(?P<meta>.*?)</span>', re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return re.sub(r"\s+", " ", unescape(_TAG.sub(" ", text))).strip()


def _split_meta(meta: str) -> list[str]:
    """Split a meta blob. React renders separators as `<!-- -->` comments."""
    meta = re.sub(r"<!--\s*-->", "\u2022", meta or "")
    parts = [p.strip() for p in re.split(f"[{SEPARATORS}]", _clean(meta)) if p.strip()]
    return parts


def _parse_cards(html: str, source: str, limit: int) -> list[dict]:
    domain = SOURCE_DOMAINS.get(source, "https://" + source)
    out, seen = [], set()
    for m in _JOB_ANCHOR.finditer(html):
        href = m.group("href")
        if href in seen:
            continue
        title = _clean(m.group("text"))
        if not title or len(title) < 3 or len(title) > 160:
            continue
        if title.lower() in {"jobs", "view all jobs", "see all jobs", "search jobs", "create profile"}:
            continue
        seen.add(href)
        url = href if href.startswith("http") else domain.rstrip("/") + href
        before = html[max(0, m.start() - 1600):m.start()]
        after = html[m.end():m.end() + 1400]
        out.append(_build_job(url, source, title, before, after))
        if len(out) >= limit:
            break
    return out


def _build_job(url: str, source: str, title: str, before: str, after: str) -> dict:
    company = None
    company_links = _COMPANY_LINK.findall(before)
    if company_links:
        company = _slug_to_name(company_links[-1])

    location = salary = posting_date = experience = None
    job_type = None
    meta_match = _META_SPAN.search(after)
    if meta_match:
        parts = _split_meta(meta_match.group("meta"))
        company_slug = ""
        if company_links:
            company_slug = company_links[-1].lower()
        for part in parts:
            low = part.lower()
            if company and low == company.lower():
                continue
            if company_slug and (low in company_slug or company_slug.startswith(low)):
                continue
            if re.search(r"[$â‚¬Â£â‚¹]", part) or re.search(r"\b(lpa|lakh|ctc|per year|/yr|per month)\b", part, re.I):
                salary = salary or part
            elif re.search(r"\b\d+\s*(day|hour|week|month|year)s?\s+ago\b|\bjust now\b|\btoday\b|\byesterday\b", part, re.I):
                posting_date = posting_date or part
            elif re.search(r"\d+\s*[-â€“]\s*\d+\s*years?|\b\d+\+\s*years?\b", part, re.I):
                experience = experience or part
            elif low in ("remote", "hybrid", "on-site", "onsite", "on site"):
                job_type = low.replace(" ", "-")
            elif location is None and not low.startswith("http"):
                location = part
    if not company:
        company = _company_from_slug(url.rstrip("/").split("/")[-1])
    if job_type is None:
        blob = f"{title} {location or ''}"
        job_type = "remote" if _is_remote(blob) else None
    return {
        "title": title,
        "company": company,
        "location": location,
        "job_type": job_type,
        "url": url,
        "description": "",
        "required_skills": "",
        "tags": [],
        "salary": salary,
        "experience": experience,
        "posting_date": posting_date,
        "source": source,
        "seniority": _seniority_of(title),
        "employment_type": "",
        "verified": "unverified",
    }


def _slug_to_name(slug: str) -> str:
    return " ".join(p.capitalize() for p in re.split(r"[-_]", slug) if p)


def _company_from_slug(slug: str) -> str | None:
    parts = [p for p in slug.split("-") if p.isalpha()]
    if len(parts) >= 3:
        return " ".join(p.capitalize() for p in parts[:2])
    return None


def dedupe(jobs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for j in jobs:
        key = (j.get("url") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(j)
    return out


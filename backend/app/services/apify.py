"""Apify-backed job discovery.

The default actor is ``curious_coder/indeed-scraper`` because it searches the
public Indeed job board by keyword and location and needs no LinkedIn/Indeed
login. Apify is pay-per-result, so this connector is only used by the explicit
``/jobs/apify`` endpoint - never by the normal free-source search.

Configuration (all optional except the token):

* ``APIFY_API_KEY``    - Apify personal API token.
* ``APIFY_ACTOR``      - actor id, default ``curious_coder/indeed-scraper``.
* ``APIFY_COUNTRY``    - default Indeed country code, default ``in``.
* ``APIFY_MAX_ITEMS``  - result cap, default 20 (hard-capped at 50).
* ``APIFY_PER_MINUTE`` - per-IP request limit, default 3/min.
* ``APIFY_INPUT_JSON`` - full actor input template. Supports the placeholders
  ``{query}``, ``{location}``, ``{limit}`` and ``{country}``.
"""
import json
from urllib.parse import urljoin

import httpx

from app.agents.job_discovery.connectors import (
    _date_str,
    _is_remote,
    _seniority_of,
    _strip_html,
    dedupe,
    relevance,
)
from app.config import settings

API_ROOT = "https://api.apify.com/v2"
DEFAULT_ACTOR = "curious_coder/indeed-scraper"

INDIA_HINTS = (
    "india", "hyderabad", "bangalore", "bengaluru", "pune", "mumbai", "chennai",
    "delhi", "noida", "gurugram", "gurgaon", "kolkata", "ahmedabad", "jaipur",
    "coimbatore", "kochi", "thiruvananthapuram",
)
COUNTRY_HINTS = {
    "in": INDIA_HINTS,
    "us": ("united states", "usa", "new york", "san francisco", "seattle", "austin", "boston"),
    "uk": ("united kingdom", "london", "manchester", "england", "scotland"),
    "ca": ("canada", "toronto", "vancouver", "montreal"),
    "au": ("australia", "sydney", "melbourne", "brisbane"),
    "sg": ("singapore",),
    "ae": ("dubai", "united arab emirates", "abu dhabi"),
}


class ApifyError(RuntimeError):
    """A user-facing Apify failure (bad token, actor error, timeout)."""


def enabled() -> bool:
    return bool((settings.apify_token or "").strip())


def actor_name() -> str:
    return (settings.apify_actor or DEFAULT_ACTOR).strip() or DEFAULT_ACTOR


def country_for(location: str) -> str:
    low = (location or "").lower()
    for code, hints in COUNTRY_HINTS.items():
        if any(hint in low for hint in hints):
            return code
    return (settings.apify_country or "in").strip().lower() or "in"


def _build_input(query: str, location: str, limit: int, country: str) -> dict:
    template = (settings.apify_input_json or "").strip()
    if template:
        raw = template
        for key, value in (
            ("query", query),
            ("location", location),
            ("limit", str(limit)),
            ("country", country),
        ):
            raw = raw.replace("{" + key + "}", json.dumps(value)[1:-1])
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApifyError(f"APIFY_INPUT_JSON is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ApifyError("APIFY_INPUT_JSON must be a JSON object.")
        return payload
    return {
        "country": country,
        "query": query,
        "location": location,
        "radiusKm": 25,
        "postedWithinDays": "",
        "count": limit,
    }


async def search_jobs(query: str, location: str = "Hyderabad, India",
                      limit: int | None = None) -> list[dict]:
    token = (settings.apify_token or "").strip()
    if not token:
        raise ApifyError("Apify is not configured. Set APIFY_API_KEY in backend/.env.")
    actor = actor_name()
    count = min(max(int(limit or settings.apify_max_items or 20), 1), 50)
    country = country_for(location)
    payload = _build_input(query, location, count, country)

    path = actor.replace("/", "~")
    url = f"{API_ROOT}/acts/{path}/run-sync-get-dataset-items"
    try:
        async with httpx.AsyncClient(timeout=240) as client:
            response = await client.post(
                url, params={"token": token, "format": "json"}, json=payload
            )
    except httpx.TimeoutException as exc:
        raise ApifyError("Apify timed out. Try again or ask for fewer results.") from exc
    except httpx.HTTPError as exc:
        raise ApifyError(f"Could not reach Apify: {exc}") from exc

    if response.status_code in (401, 403):
        raise ApifyError("Apify rejected the API token. Check APIFY_API_KEY.")
    if response.status_code >= 400:
        detail = (response.text or "").strip()[:200]
        raise ApifyError(f"Apify error {response.status_code}: {detail or 'no details'}")

    try:
        items = response.json()
    except ValueError as exc:
        raise ApifyError("Apify returned a non-JSON response.") from exc
    if isinstance(items, dict):
        items = items.get("items") or items.get("data") or []
    if not isinstance(items, list):
        raise ApifyError("Apify returned an unexpected dataset shape.")

    jobs: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            job = _normalize(item, country)
            if job:
                jobs.append(job)
    jobs = dedupe(jobs)
    jobs = [j for j in jobs if relevance(j, query) > 0.08]
    jobs.sort(key=lambda j: relevance(j, query), reverse=True)
    return jobs[:count]


def _posting_date(value) -> str | None:
    if isinstance(value, (int, float)) is False:
        return _date_str(value)
    stamp = float(value)
    if stamp > 100_000_000_000:
        stamp /= 1000.0
    return _date_str(stamp)


def _salary(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("formatted", "text", "value", "baseSalary"):
            found = value.get(key)
            if isinstance(found, str) and found.strip():
                return found.strip()
            if isinstance(found, dict):
                low = found.get("min") or found.get("minimum") or found.get("value")
                high = found.get("max") or found.get("maximum")
                if low and high:
                    return f"{low} - {high}"
                if low:
                    return str(low)
    return None


def _labels(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for entry in value:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            label = entry.get("label") or entry.get("name") or entry.get("value")
            if isinstance(label, str):
                out.append(label)
    return out


def _normalize(item: dict, country: str) -> dict | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None

    details = item.get("companyDetails") if isinstance(item.get("companyDetails"), dict) else {}
    company = (details.get("name") or item.get("companyName") or item.get("company") or "").strip()
    location = (
        item.get("formattedLocation")
        or item.get("location")
        or ", ".join(filter(None, [item.get("jobLocationCity"), item.get("jobLocationState")]))
        or ""
    ).strip()

    link = (item.get("viewJobLink") or "").strip()
    if link.startswith("/"):
        url = f"https://{country}.indeed.com{link}"
    elif link.startswith("http"):
        url = link
    else:
        url = (item.get("originalApplyUrl") or item.get("url") or "").strip()
    if not url:
        return None
    url = urljoin(f"https://{country}.indeed.com/", url)

    attributes = _labels(item.get("attributes"))
    tags = attributes + _labels(item.get("occupations"))
    tags = list(dict.fromkeys(t for t in tags if t))[:20]
    job_types = _labels(item.get("jobTypes"))
    employment_type = ", ".join(job_types)
    description = item.get("jobDescription") or item.get("jobDescriptionHTML") or ""
    if isinstance(description, str):
        description = _strip_html(description)

    remote = _is_remote(f"{title} {location} {employment_type}")
    return {
        "title": title,
        "company": company or None,
        "location": location or None,
        "job_type": "remote" if remote else None,
        "url": url,
        "description": description,
        "required_skills": "",
        "tags": tags,
        "salary": _salary(item.get("salary")),
        "experience": None,
        "posting_date": _posting_date(item.get("pubDate")),
        "source": "indeed (apify)",
        "seniority": _seniority_of(f"{title} {' '.join(tags)}"),
        "employment_type": employment_type,
        "verified": "unverified",
    }

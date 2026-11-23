"""Board quality gates.

Connectors occasionally return listings that are not roles the owner can
realistically pursue (for example Dutch marketing internships on a Python
board). Ranking them produces a misleading ~50% score, so the Matched Jobs
board hides them by default.

A job is kept when either:

* one of the resume skills appears in its title/description/tags, or
* a meaningful word from the owner's target role titles appears in its title.

On-site roles outside the owner's markets are also hidden unless the job is
explicitly remote. Every gate can be switched off from the API/UI.
"""
import re

STOP_WORDS = {
    "the", "and", "for", "with", "junior", "senior", "developer", "developers",
    "engineer", "engineers", "associate", "application", "applications",
    "technical", "solutions", "operations", "forward", "deployed",
}

INDIA_HINTS = (
    "india", "hyderabad", "bangalore", "bengaluru", "pune", "mumbai", "chennai",
    "delhi", "noida", "gurugram", "gurgaon", "kolkata", "ahmedabad", "jaipur",
)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", (text or "").lower()))


def _contains(text: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", text) is not None


def target_tokens(prefs: dict | None) -> set[str]:
    tokens: set[str] = set()
    for target in (prefs or {}).get("target_categories") or []:
        for word in _words(str(target)):
            if word in STOP_WORDS:
                continue
            if len(word) > 2 or word == "ai":
                tokens.add(word)
    return tokens


def is_relevant(job, skills: list[str], prefs: dict | None) -> bool:
    """True when the listing plausibly belongs on this person's board."""
    title = (job.title or "").lower()
    blob = " ".join(
        str(part or "")
        for part in (
            job.title,
            job.description,
            job.tags,
            job.required_skills,
            job.employment_type,
        )
    ).lower()

    if any(_contains(blob, skill) for skill in skills if skill):
        return True
    return bool(target_tokens(prefs) & _words(title))


def location_ok(job, prefs: dict | None) -> bool:
    """Remote roles always pass; on-site roles must be in a target market."""
    loc = f"{job.location or ''} {job.job_type or ''}".lower()
    if job.job_type == "remote" or re.search(r"\bremote\b", loc):
        return True
    if any(hint in loc for hint in INDIA_HINTS):
        return True
    for market in (prefs or {}).get("markets") or []:
        market = str(market).strip().lower()
        if not market or market == "remote worldwide":
            continue
        if market in loc:
            return True
    return False

"""Allow-list of sites JARVIS can open on the user's device.

JARVIS never navigates on its own. It returns a link and the UI requires a
user click, which is the approval step for opening a site.
"""
from urllib.parse import quote_plus

SITES = {
    "youtube": "https://www.youtube.com/results?search_query={query}",
    "youtube music": "https://music.youtube.com/search?q={query}",
    "google": "https://www.google.com/search?q={query}",
    "gmail": "https://mail.google.com/mail/u/0/",
    "linkedin": "https://www.linkedin.com/feed/",
    "github": "https://github.com/",
    "maps": "https://www.google.com/maps/search/{query}",
    "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={query}",
    "weather": "https://www.google.com/search?q=weather+{query}",
    "news": "https://news.google.com/search?q={query}",
    "amazon": "https://www.amazon.in/s?k={query}",
    "chatgpt": "https://chatgpt.com/",
    "whatsapp": "https://web.whatsapp.com/",
    "stackoverflow": "https://stackoverflow.com/search?q={query}",
}

ALIASES = {
    "yt": "youtube",
    "you tube": "youtube",
    "yt music": "youtube music",
    "ytmusic": "youtube music",
    "gmail mail": "gmail",
    "google maps": "maps",
    "google search": "google",
    "wiki": "wikipedia",
    "gh": "github",
    "linked in": "linkedin",
    "so": "stackoverflow",
    "stack overflow": "stackoverflow",
    "openai": "chatgpt",
    "ytb": "youtube",
}

STOP_WORDS = {
    "open", "launch", "go", "start", "browse", "search", "for", "on", "in", "the",
    "a", "please", "can", "you", "show", "me", "play", "take", "me", "to", "my",
    "of", "and", "then", "video", "videos", "song", "songs", "music", "site",
}


def normalize(name: str) -> str:
    return " ".join((name or "").strip().lower().replace("-", " ").split())


def resolve(site: str, query: str = "") -> dict | None:
    key = normalize(site)
    key = ALIASES.get(key, key)
    if key not in SITES:
        return None
    template = SITES[key]
    q = (query or "").strip()
    if "{query}" in template:
        template = template.replace("{query}", quote_plus(q) if q else "")
    return {"site": key, "url": template, "query": q}


def extract(message: str) -> dict | None:
    """Parse 'open youtube lofi mix' or 'play lofi on youtube' into a target."""
    low = " " + normalize(message) + " "
    for alias in sorted(ALIASES, key=len, reverse=True):
        if f" {alias} " in low:
            site = ALIASES[alias]
            query = low.replace(f" {alias} ", " ").replace("play", " ").replace("open", " ")
            words = [w for w in query.split() if w not in STOP_WORDS]
            return resolve(site, " ".join(words))
    for site in sorted(SITES, key=len, reverse=True):
        if f" {site} " in low:
            query = low.replace(f" {site} ", " ").replace("open", " ").replace("play", " ")
            words = [w for w in query.split() if w not in STOP_WORDS]
            return resolve(site, " ".join(words))
    return None

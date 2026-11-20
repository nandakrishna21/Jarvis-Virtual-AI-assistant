import hashlib, re
from app.database.session import SessionLocal
from app.database.models import HiringNews
from app.agents.hiring_news import connectors


def dedupe_key(item: dict) -> str:
    url = (item.get("application_url") or "").strip().lower()
    if url and not url.startswith("https://news.ycombinator.com/item"):
        return hashlib.sha256(url.encode()).hexdigest()[:32]
    base = f"{item.get('company','')}|{item.get('role','')}|{item.get('posting_date','')}".lower()
    return hashlib.sha256(base.encode()).hexdigest()[:32]


async def fetch_and_store(max_per_source: int = 25) -> dict:
    import httpx
    results, errors = [], []
    async with httpx.AsyncClient(headers=connectors.HEADERS, follow_redirects=True) as client:
        for src in connectors.SOURCES:
            name = src["name"]
            try:
                items = await connectors.fetch_source(src, client)
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue
            if not items:
                errors.append(f"{name}: no items parsed")
                continue
            for item in items:
                item["_kind"] = src.get("kind", "jobs")
            results.extend(items[:max_per_source])

    kept, skipped = [], []
    for item in results:
        text = f"{item.get('title','')} {item.get('description','')} {item.get('role','')}"
        relevance = connectors.item_relevance(item)
        if not relevance:
            skipped.append({"reason": "role not relevant", "title": item.get("title")})
            continue
        kind = item.pop("_kind", "jobs")
        if kind == "announcement" and not connectors.is_hiring_related(text):
            skipped.append({"reason": "not a hiring announcement", "title": item.get("title")})
            continue
        item["relevance"] = relevance
        item["is_current"] = connectors.is_fresh(item.get("posting_date"))
        kept.append(item)

    db = SessionLocal()
    inserted, updated = 0, 0
    try:
        for item in kept:
            key = dedupe_key(item)
            row = db.query(HiringNews).filter(HiringNews.dedupe_key == key).first()
            if row:
                row.title = item.get("title"); row.company = item.get("company")
                row.role = item.get("role"); row.location = item.get("location")
                row.experience = item.get("experience"); row.salary = item.get("salary")
                row.posting_date = item.get("posting_date"); row.source = item.get("source")
                row.official_source = item.get("official_source")
                row.relevance = item["relevance"]; row.is_current = item["is_current"]
                updated += 1
            else:
                db.add(HiringNews(
                    title=item.get("title") or "", company=item.get("company"), role=item.get("role"),
                    location=item.get("location"), experience=item.get("experience"),
                    salary=item.get("salary"), posting_date=item.get("posting_date"),
                    source=item.get("source"), official_source=item.get("official_source"),
                    application_url=item.get("application_url") or None, relevance=item["relevance"],
                    is_current=item["is_current"], dedupe_key=key))
                inserted += 1
        db.commit()
    finally:
        db.close()
    return {"inserted": inserted, "updated": updated, "skipped": len(skipped),
            "source_errors": errors, "fetched": len(results)}

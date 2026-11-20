# Hiring News & Company Research (Phase 5)

## What it does
Fetches public job and hiring feeds, extracts company, role, location, experience, salary, posting date and the original URL, scores each item for relevance, filters by freshness, deduplicates and stores everything in SQLite.

## Why required
You want current hiring signals, not old announcements. Every item carries its posting date, source and `is_current` flag so stale posts are never presented as live.

## Sources (public, permitted)
| Source | Kind | URL |
|---|---|---|
| Hacker News "Ask HN: Who is hiring?" | company announcement | `https://hn.algolia.com/api/v1/search_by_date` → thread items |
| We Work Remotely | job posting | `https://weworkremotely.com/remote-jobs.rss` |
| Remotive | job posting | `https://remotive.com/api/remote-jobs?limit=50` |
| Arbeitnow | job posting | `https://www.arbeitnow.com/api/job-board-api` |

The Hacker News thread is parsed from the pipe-separated first line of each comment (`Company | Role | Location | REMOTE | Full-time | Salary | URL`), which is how companies announce open roles there. Each comment becomes its own row with a permalink to the comment.

Add more feeds in `backend/app/agents/hiring_news/connectors.py` → `SOURCES`. A source is either `kind: "announcement"` (must contain hiring intent) or `kind: "jobs"` (the posting is itself the announcement).

## Filtering and ranking
- Relevance is weighted: `python`, `django`, `fastapi`, `generative ai` and `ai agent` count most, generic `developer` counts least. Title and role count double; body text adds only a small bonus.
- Senior titles (`senior`, `lead`, `manager`, `architect`, …) are penalised because your targets are entry/junior.
- Announcement sources must contain hiring intent (`hiring`, `join our team`, `open roles`, …).
- `is_current = True` only when the posting date is within 45 days (`FRESH_DAYS`).
- Salary and location are only captured when explicitly published — never guessed.
- Requests are retried with backoff on 429/5xx so a busy feed does not empty the whole run.

## Endpoints
- `POST /hiring-news/fetch` — fetch, filter, dedupe, store. Returns inserted/updated/skipped and source errors.
- `GET /hiring-news?current_only=true&limit=50` — stored items ordered by relevance.

## Verify
```powershell
curl -X POST http://127.0.0.1:8000/hiring-news/fetch
curl "http://127.0.0.1:8000/hiring-news?current_only=true"
```

## Common errors
- `source_errors: [...]` — feed unreachable or structure changed; check the URL in `SOURCES`.
- Empty results — the feed published few matching roles; add another source rather than lowering the freshness filter.
- Duplicate rows — prevented by `dedupe_key`; the `application_url` column is unique as well.

# Job Discovery (Phase 2)

## What it does
Searches permitted public job boards, dedupes, parses the resume, scores and ranks every result against your profile, stores the ranking in SQLite and returns the best matches. Every score is explainable: the dashboard shows the component breakdown and the skills you are missing.

## Scoring (spec weights)
Skills 35% + Experience 25% + Responsibilities 20% + Location/Remote 10% + Education 10%.

Every component is measured from real posting data, never invented:
- **Skills** are extracted from the title, tags and the full description, then compared with the skills on your resume. A skill you have boosts the score, a skill you lack is listed as a gap.
- **Experience** reads the seniority marker (`senior`, `junior`, `fresher`, `no experience required`, `1-3 years`) and compares it with your target levels. A senior role scores low when you target entry level; "no experience required" scores full marks.
- **Responsibilities** counts engineering verbs and skill mentions in the description.
- **Location** checks remote / your markets / India.
- **Education** looks for degree requirements and tells you what was found.

A role-fit score is also calculated for the title against your target categories and shown as a note.

## Feedback loop
Mark a match as **Good match** or **Not for me** (Matched Jobs page or `POST /jobs/{id}/feedback`). JARVIS counts the skills in the jobs you like and the jobs you reject, then boosts or penalises those skills in the skill component and re-scores every stored job. The learned weights are visible at `GET /jobs/feedback/weights` and shown above the list.

## Bulk decisions and export
- `POST /jobs/bulk-action` with `{"job_ids": [..], "action": "approve"|"reject"}` shortlists (approve) or rejects several jobs at once and records the decision in the application history.
- `GET /jobs/export.csv` downloads the ranked list with score, matching skills, gaps, status and URL.

## Endpoints
- POST /jobs/search {query, location}
- GET /jobs · GET /jobs/{id} · GET /jobs/top-matches · GET /jobs/matched
- POST /jobs/match-resume (multipart resume PDF)
- POST /jobs/bulk-action · POST /jobs/{id}/feedback · GET /jobs/feedback/weights
- GET /jobs/export.csv

## Sources
| Source | Type | Notes |
|---|---|---|
| Remotive | public JSON API | honours a search query |
| Arbeitnow | public JSON API | European + remote roles |
| RemoteOK | public JSON API | remote worldwide |
| Himalayas | public JSON API | honours a search query |
| Internshala | public listing pages | India junior / internship roles; filters on role-slug URLs, several slugs are tried |
| Wellfound / Hirist | public listing pages | fallback only, no auth or CAPTCHA bypass |

Jobs are marked `verified: unverified` until you open the source yourself. Live results depend on the public pages staying reachable; if a source changes shape, fewer jobs are returned for that source while the rest keep working.

## Privacy
Only public pages and key-free public APIs are read. Nothing is posted, and no account is ever automated.

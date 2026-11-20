# Government Exam Mentor (Phase 6)

## What it does
Syllabus database for SSC CGL, SSC CHSL, RBI Assistant, IBPS PO; daily study plans; topic teaching via your local Ollama model; practice questions with answers and explanations; answer evaluation; mastery tracking; weak-topic identification; progress reports.

## Why required
Turns JARVIS into a daily mentor loop: plan → teach → practise → evaluate → revise.

## Endpoints
- `GET /study/exams` — list supported exams (seeds topics on first call)
- `POST /study/seed` — seed syllabus topics into SQLite
- `POST /study/start` {exam, date?, topic?} — today's plan + LLM teaching for the focus topic
- `GET /study/question?topic=` — practice question (options only, answer hidden)
- `POST /study/answer` {exam, topic, answer} — evaluate, explain, update mastery
- `GET /study/progress?exam=` — accuracy, weak topics, strong topics
- `GET /study/topics?exam=` — topic list

## How it works
- Topics are stored in `study_topics` with `mastery`, `attempts`, `correct`.
- Daily plan = 3 topics chosen by lowest mastery first (weak-topic priority), stored in `study_plans` per date so it is stable for the day.
- Mastery = `100 * correct / attempts`. Accuracy = overall correct percentage.
- Practice questions come from a local verified question bank (`service.py` → `QUESTION_BANK`). The answer is never shown before you answer.

## Honesty rules
The syllabus is a study aid, not an official notification. JARVIS never states exam dates or official notifications without checking the official authority site.

## Verify
```powershell
curl http://127.0.0.1:8000/study/exams
curl -X POST http://127.0.0.1:8000/study/start -H "Content-Type: application/json" -d '{"exam":"SSC CGL"}'
curl "http://127.0.0.1:8000/study/question?topic=Percentage"
curl -X POST http://127.0.0.1:8000/study/answer -H "Content-Type: application/json" -d '{"exam":"SSC CGL","topic":"Percentage","answer":"B"}'
curl "http://127.0.0.1:8000/study/progress?exam=SSC CGL"
```

## Common errors
- `unsupported exam` — use one of the names from `/study/exams`.
- `no practice question stored for topic` — the bank has no item for that topic yet; teach it, or add a question to `QUESTION_BANK`.
- Slow first reply — the model loads on demand (about 15-25 s on this laptop); it is unloaded after 2 minutes idle.

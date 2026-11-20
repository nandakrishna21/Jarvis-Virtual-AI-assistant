# Document Studio — Tailored Resumes and Cover Letters

JARVIS can build job-specific resume and cover-letter drafts from your verified
resume data, store every generation as a numbered version, and let you download
it as a text file.

**Nothing is ever submitted to an employer.** Every document is a draft for you
to review and edit.

---

## 1. Structured resume sections

A tailored document is only as good as the structured data behind it. JARVIS
stores your resume in two forms:

| Form | Where it comes from | Used for |
|---|---|---|
| Raw text + extracted skills | The PDF/DOCX/TXT file you upload | Skill matching, job scoring |
| Structured sections | You (in Document Studio) | Document generation |

Section types:

- `summary` — a short professional summary
- `experience` — a job: title, organization, location, dates, what you did
- `education` — degree, school, dates
- `projects` — project name, stack, description
- `skills` — handled by the extracted-skill list
- `custom` — anything else

### Add a section

1. Open **Document Studio** in the sidebar.
2. Pick your resume in the top-left dropdown.
3. Fill the "Add a section" form at the bottom-left.
4. Click **Save section**.

Or via the API:

```powershell
curl -X POST http://127.0.0.1:8000/resumes/57/sections `
  -H "Content-Type: application/json" `
  -d '{"section_type":"experience","title":"Backend Developer","organization":"Acme","start_date":"2024-01","end_date":"2026-01","description":"Built FastAPI services with PostgreSQL."}'
```

---

## 2. Generating tailored documents

### From the UI

1. Choose your resume.
2. Choose the target job (optional — without one you get a general version).
3. Click **Generate**. JARVIS produces a tailored resume **and** a cover letter.
4. Click **View** to read it, or the download icon to save it.

### From chat (approval-first)

```
tailor my resume for job 3
generate a cover letter for job 3
```

JARVIS creates an **ActionProposal**. Nothing is written until you approve it
in the Assistant or Approvals panel.

### From the API

```powershell
curl -X POST http://127.0.0.1:8000/documents/generate `
  -H "Content-Type: application/json" `
  -d '{"resume_id":57,"job_id":3,"types":["resume","cover_letter"]}'
```

Response:

```json
{
  "resume_id": 57,
  "job_id": 3,
  "count": 2,
  "documents": [
    {"id": 45, "doc_type": "resume", "version": 1, "file_path": "C:/JARVIS/data/documents/resume_job3_v1_20261112_140000.txt"},
    {"id": 46, "doc_type": "cover_letter", "version": 1, "file_path": "..."}
  ],
  "warning": "Drafts only. Nothing was submitted to the employer."
}
```

---

## 3. How tailoring works

The generator is deliberately honest and deterministic — no hallucination:

1. **Skills are reordered** so the ones the posting asks for appear first.
2. **Only your own sections** are used. If you have no experience section, the
   document says so instead of inventing one.
3. **The match record is surfaced**: direct overlap and known gaps are printed
   in the resume footer and referenced in the cover letter.
4. **Gaps are acknowledged, not hidden.** The cover letter mentions missing
   requirements honestly instead of pretending you have them.
5. **A JARVIS footer** marks every file as a draft needing review.

---

## 4. Versions

Each generation increments a version number for that (resume, job, doc type)
combination. Nothing is ever overwritten — older versions stay available.

```powershell
curl "http://127.0.0.1:8000/documents?resume_id=57&job_id=3"
curl "http://127.0.0.1:8000/documents?resume_id=57&doc_type=cover_letter"
```

---

## 5. Download

```powershell
curl -o resume.txt http://127.0.0.1:8000/documents/45/download
```

Files are plain UTF-8 text under `C:\JARVIS\data\documents\`, so you can open
them in Word, Google Docs, or any editor.

---

## 6. API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/resumes/{resume_id}/sections` | List sections |
| POST | `/resumes/{resume_id}/sections` | Add a section |
| PATCH | `/sections/{section_id}` | Edit a section |
| DELETE | `/sections/{section_id}` | Remove a section |
| POST | `/documents/generate` | Generate versions (resume + cover letter) |
| GET | `/documents` | List versions (filter by `resume_id`, `job_id`, `doc_type`) |
| GET | `/documents/{id}` | Read one version |
| GET | `/documents/{id}/download` | Download the text file |

---

## 7. Safety rules

- Documents are drafts. JARVIS never submits an application.
- Content comes from your uploaded file and your structured sections only.
- The generator will not invent employers, dates, degrees, or achievements.
- The API-key guard (if enabled) also protects these write endpoints.

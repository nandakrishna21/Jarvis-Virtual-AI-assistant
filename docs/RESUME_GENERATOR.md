# Resume Generator

## What it does
Paste a job description, get a resume written from **your own old resume**. JARVIS parses the JD, checks every requirement against what your resume can actually prove, and rebuilds the resume around that job: the summary targets the role, the skills are ordered so the JD skills come first, and the bullets are sorted so the most relevant ones lead.

It also tells you the truth: requirements you cannot show evidence for are reported as **gaps** and are never written into the resume.

## How to use it
1. Open **Resume Generator** in the sidebar.
2. Paste the full job posting into the big text box.
3. Optionally set the target role and company (JARVIS also reads them from the JD).
4. Press **Preview resume** to see it, then **Save version** to store and download it.
5. Or ask JARVIS: *"generate resume from this job description: <paste JD>"* - that path goes through the normal approval card.

The optional **AI summary** switch lets the configured provider (NVIDIA by default, Ollama as fallback) rewrite only the summary paragraph. The rewrite is rejected if it mentions a technology that does not appear in your resume, so the model cannot invent skills.

## What it uses as your source
- The uploaded resume text and extracted skills of your **active** resume (Resume Intelligence page).
- The structured sections (summary, experience, education, projects) you added in Resume Intelligence / Document Studio.

If your stored resume is only a stub (fewer than 200 characters of text), the Resume Intelligence page warns you and offers a text editor - paste your real resume text there first and the generator gets much sharper.

## Coverage analysis
| Field | Meaning |
|---|---|
| `jd_title`, `jd_company` | parsed from the posting |
| `jd_skills` | technologies and role keywords found in the JD |
| `covered` | JD skills that appear in your resume (text or sections) |
| `gaps` | JD skills with no evidence in your resume |
| `coverage_pct` | covered / jd_skills as a percentage |
| `min_years` | years of experience the JD asks for |

## Endpoints
- `GET /resume-generator/jd?jd=<text>` - parse only, no generation.
- `POST /resume-generator/preview` - build and return without saving.
- `POST /resume-generator/save` - build and store a numbered version.
- `GET /resume-generator/versions` - saved versions.
- `GET /resume-generator/{id}/download` - download the text file.

## Limits, on purpose
- No invented employers, dates, metrics or skills.
- Gaps are shown, never padded into the resume.
- The output is a draft for you to edit; JARVIS never submits it anywhere.

import re
import csv, io

KNOWN_SKILLS = [
    "python","django","fastapi","flask","rest","graphql","api","postgresql","sqlite",
    "mysql","mongodb","redis","react","javascript","typescript","html","css","git",
    "docker","aws","linux","sql","pandas","numpy","tensorflow","pytorch","machine learning",
    "deep learning","celery","uvicorn","nginx",
]

def extract_text_from_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in r.pages)
    except Exception as e:
        return f"ERROR: {e}"

def extract_skills(text: str) -> list[str]:
    low = text.lower()
    return [s for s in KNOWN_SKILLS if s in low]

def parse_resume_csv(text: str) -> dict:
    return {"skills": extract_skills(text), "text_len": len(text)}

"""Restore the baseline resume profile after a data reset."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "jarvis.db"

conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("delete from app_settings where key = 'job_scoring_learned'")
count = cur.execute("select count(*) from resume_profiles").fetchone()[0]
if not count:
    cur.execute(
        "insert into resume_profiles (file_path, raw_text, extracted_skills) values (?,?,?)",
        ("C:/JARVIS/data/resumes/cv.pdf", "python django fastapi api sql",
         "python,django,fastapi,api,sql"),
    )
conn.commit()
print("resume_profiles:", list(cur.execute("select id, file_path, extracted_skills from resume_profiles")))
print("settings:", [r[0] for r in cur.execute("select key from app_settings")])
conn.close()

"""Reset operational tables that were polluted by test runs, keep user data.

Keeps: user_preferences, app_settings, hiring_news (real feed data).
Clears: jobs, matches, applications, approvals, proposals, notifications,
emails, tasks, reminders, interviews, agent runs and generated documents.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "jarvis.db"

KEEP = {"user_preferences", "app_settings", "hiring_news"}

conn = sqlite3.connect(str(DB))
cur = conn.cursor()
tables = [r[0] for r in cur.execute(
    "select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
cleared = []
for table in tables:
    if table in KEEP:
        continue
    try:
        count = cur.execute(f'select count(*) from "{table}"').fetchone()[0]
        if count:
            cur.execute(f'delete from "{table}"')
            cleared.append((table, count))
    except sqlite3.Error as exc:
        print(f"skip {table}: {exc}")
conn.commit()
conn.execute("vacuum")
conn.close()

print("cleared:")
for table, count in cleared:
    print(f"  {table}: {count} row(s)")
print("kept:", ", ".join(sorted(KEEP)))

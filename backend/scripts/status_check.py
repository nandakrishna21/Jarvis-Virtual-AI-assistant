import sqlite3

conn = sqlite3.connect("jarvis.db")
tables = [
    r[0]
    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
]
print("tables:", len(tables))
for t in tables:
    if t.startswith("sqlite_"):
        continue
    n = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"  {t:24} {n}")
conn.close()

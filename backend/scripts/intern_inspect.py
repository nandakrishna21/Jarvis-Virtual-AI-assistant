import re

html = open(r"C:\JARVIS\logs\intern_ok.html", encoding="utf-8").read()
m = re.search(r'id="individual_internship_(?P<id>\d+)"(?P<attrs>[^>]*)>', html)
print("card found:", bool(m))
body = html[m.start():m.start() + 3500]

print("\n--- EXPERIENCE META ---")
for x in re.finditer(r'internship_meta\s+experience_meta[\s\S]{0,300}', body):
    print(repr(x.group(0)[:300]))
    break

print("\n--- LOCATION ---")
for x in re.finditer(r'class="row-1-item\s+locations"[\s\S]{0,300}', body):
    print(repr(x.group(0)[:300]))
    break

print("\n--- SALARY ---")
for x in re.finditer(r'class="desktop"[\s\S]{0,200}', body):
    print(repr(x.group(0)[:200]))
    break

print("\n--- ABOUT ---")
for x in re.finditer(r'class="about_job"[\s\S]{0,400}', body):
    print(repr(x.group(0)[:400]))
    break

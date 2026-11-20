import re

html = open(r"C:\JARVIS\logs\intern_ok.html", encoding="utf-8").read()
m = re.search(r'id="individual_internship_(?P<id>\d+)"(?P<attrs>[^>]*)>', html)
body = html[m.start():m.start() + 4500]

out = []
for x in re.finditer(r'<(?P<tag>[a-z0-9]+)\s+class="(?P<cls>[^"]+)"[^>]*>(?P<txt>[^<]{0,160})', body):
    cls = x.group("cls")
    txt = re.sub(r"\s+", " ", x.group("txt")).strip()
    out.append(f"{x.group('tag')}.{cls}  ->  {txt.encode('ascii', 'replace').decode()}")

for line in out[:45]:
    print(line)

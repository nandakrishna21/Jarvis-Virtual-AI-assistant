import asyncio

from app.agents.job_discovery.connectors import _fetch_internshala, relevance

jobs = asyncio.run(_fetch_internshala("Python Backend Developer", "India"))
print("internshala parsed:", len(jobs))
for j in jobs[:8]:
    print(
        f"  rel={relevance(j, 'Python Backend Developer', True):.3f} "
        f"sen={j.get('seniority'):<10} | {j['title'][:44]:44} | {(j.get('company') or '')[:20]:20} "
        f"| {(j.get('location') or '')[:14]:14} | exp={j.get('experience')} | tags={j.get('tags')[:4]}"
    )

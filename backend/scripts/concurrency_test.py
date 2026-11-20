"""Verify JARVIS runs at most one AI job at a time (spec: max_concurrent_ai_jobs = 1).

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\concurrency_test.py
"""
import asyncio, sys, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.services import ollama
from app.config import settings


async def main():
    print(f"configured max_concurrent_ai_jobs = {settings.max_concurrent_ai_jobs}")
    prompts = [
        "Say A.",
        "Say B.",
        "Say C.",
        "Say D.",
    ]
    start = time.time()
    results = await asyncio.gather(*(ollama.chat(p) for p in prompts))
    total = round(time.time() - start, 2)
    print(f"4 concurrent AI requests finished in {total}s")
    for p, r in zip(prompts, results):
        print(f"  {p!r:12} ok={r.get('ok')} elapsed={r.get('elapsed')}s "
              f"tok/s={r.get('tokens_per_second')} error={str(r.get('error'))[:60]}")
    ok = all(r.get("ok") for r in results)
    print("all succeeded" if ok else "some failed")


if __name__ == "__main__":
    asyncio.run(main())

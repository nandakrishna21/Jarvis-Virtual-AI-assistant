"""Measure JARVIS resource usage and latency against a running backend.

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\performance_test.py [base_url]

The backend must already be running (uvicorn app.main:app).
"""
import sys, time, json, statistics, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx
import psutil

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def timed(label, method, path, **kwargs):
    start = time.time()
    r = httpx.request(method, f"{BASE}{path}", timeout=600, **kwargs)
    elapsed = round(time.time() - start, 2)
    return {"label": label, "method": method, "path": path, "status": r.status_code,
            "seconds": elapsed}


def main():
    proc = psutil.Process()
    results = []

    results.append(timed("health", "GET", "/health"))
    results.append(timed("system status", "GET", "/system/status"))
    results.append(timed("tasks list", "GET", "/tasks"))
    results.append(timed("productivity report", "GET", "/tasks/productivity"))
    results.append(timed("jobs list", "GET", "/jobs"))
    results.append(timed("top matches", "GET", "/jobs/top-matches"))
    results.append(timed("emails list", "GET", "/emails"))
    results.append(timed("hiring news", "GET", "/hiring-news"))
    results.append(timed("study progress", "GET", "/study/progress"))
    results.append(timed("approvals list", "GET", "/approvals"))
    results.append(timed("files list", "GET", "/files?subdir=docs"))
    results.append(timed("schedules", "GET", "/schedules"))
    results.append(timed("voice status", "GET", "/voice/status"))

    results.append(timed("developer analyze", "POST", "/developer/analyze",
                         json={"code": "def f(x):\n    return x + 1\n"}))
    results.append(timed("task create", "POST", "/tasks",
                         json={"title": "performance probe", "category": "job"}))

    light = [r for r in results if r["seconds"] < 5]
    latencies = [r["seconds"] for r in light]
    report = {
        "base_url": BASE,
        "results": results,
        "light_endpoint_avg_s": round(statistics.mean(latencies), 3) if latencies else None,
        "light_endpoint_max_s": round(max(latencies), 3) if latencies else None,
        "slowest": sorted(results, key=lambda r: -r["seconds"])[:5],
        "backend_process_rss_mb": round(proc.memory_info().rss / 1024**2, 1),
        "system_ram_percent": psutil.virtual_memory().percent,
        "system_ram_free_gb": round(psutil.virtual_memory().available / 1024**3, 2),
    }
    print(json.dumps(report, indent=2))
    out = pathlib.Path(r"C:\JARVIS\data\reports\performance_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()

"""Check which NVIDIA NIM models the configured key can use."""
import os
import sys
from pathlib import Path

import httpx

ENV = Path(__file__).resolve().parents[1] / ".env"


def load_key() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("NVIDIA_API_KEY="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("NVIDIA_API_KEY", "")


def main() -> int:
    key = load_key()
    if not key:
        print("no NVIDIA_API_KEY found in backend/.env")
        return 1
    base = "https://integrate.api.nvidia.com/v1"
    r = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    print("status:", r.status_code)
    if r.status_code != 200:
        print(r.text[:400])
        return 1
    ids = [m.get("id") for m in r.json().get("data", [])]
    print("model count:", len(ids))
    for wanted in ("meta/llama-3.1-8b-instruct", "meta/llama-3.3-70b-instruct",
                   "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
                   "nvidia/llama-3.1-nemotron-70b-instruct",
                   "meta/llama-3.2-3b-instruct", "qwen/qwen2.5-coder-32b-instruct"):
        print(("OK   " if wanted in ids else "no   "), wanted)
    print("sample:", ", ".join(ids[:15]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

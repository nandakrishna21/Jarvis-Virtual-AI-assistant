"""Try a chat completion against the configured NVIDIA models."""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nvidia_check import load_key  # noqa: E402

BASE = "https://integrate.api.nvidia.com/v1"
CANDIDATES = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "google/gemma-3-12b-it",
    "z-ai/glm-5.3-flash",
    "moonshotai/kimi-k3.1-pro",
]


def main() -> int:
    key = load_key()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for model in CANDIDATES:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a terse assistant."},
                {"role": "user", "content": "Reply with exactly: JARVIS ONLINE"},
            ],
            "temperature": 0.2,
            "max_tokens": 40,
        }
        try:
            r = httpx.post(f"{BASE}/chat/completions", json=payload, headers=headers, timeout=90)
            if r.status_code != 200:
                print(f"{model}: HTTP {r.status_code} {r.text[:200]}")
                continue
            data = r.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()
            print(f"{model}: OK -> {text[:120]}")
        except Exception as exc:  # noqa: BLE001
            print(f"{model}: ERR {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

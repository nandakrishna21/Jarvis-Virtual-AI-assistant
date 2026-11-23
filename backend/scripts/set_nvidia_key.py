"""Set the NVIDIA API key in backend/.env without echoing it to the screen.

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\set_nvidia_key.py

The key is typed in a hidden prompt and never appears in shell history,
logs or chat. After it succeeds, restart JARVIS:
    powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\stop_prod.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\start_prod.ps1
"""
import getpass
import pathlib
import sys

ENV_FILE = pathlib.Path(__file__).resolve().parents[1] / ".env"


def normalize(raw: str) -> str:
    """Remove smart quotes/non-ASCII and collapse accidentally repeated pastes."""
    cleaned = "".join(ch for ch in raw if 32 <= ord(ch) < 127).strip()
    if cleaned.count("nvapi-") > 1:
        # The key was pasted more than once (common when copying from a page
        # that shows it twice). Keep only the first copy.
        cleaned = "nvapi-" + cleaned.split("nvapi-")[1]
    return cleaned


def main() -> int:
    if not ENV_FILE.exists():
        print(f"No .env at {ENV_FILE}. Create it first with LLM_PROVIDER and NVIDIA_MODEL lines.")
        return 1

    raw = getpass.getpass("Paste the new NVIDIA API key (hidden): ").strip()
    if not raw:
        print("Nothing entered. Aborted.")
        return 1
    key = normalize(raw)
    if not key.startswith("nvapi-"):
        print("That does not look like an NVIDIA key (expected it to start with nvapi-). Aborted.")
        return 1
    if len(key) < 40:
        print("Key looks too short. Aborted.")
        return 1
    if key != raw.strip():
        print("Cleaned the pasted value (removed smart quotes / repeated paste).")

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith("NVIDIA_API_KEY="):
            lines[i] = f"NVIDIA_API_KEY={key}"
            replaced = True
    if not replaced:
        lines.append(f"NVIDIA_API_KEY={key}")

    if not any(line.startswith("LLM_PROVIDER=") for line in lines):
        lines.insert(0, "LLM_PROVIDER=nvidia")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated NVIDIA_API_KEY in {ENV_FILE} (value hidden).")
    print("Now revoke the old key at https://build.nvidia.com -> API Keys, then restart JARVIS:")
    print("  powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\stop_prod.ps1")
    print("  powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\start_prod.ps1")
    return 0


if __name__ == "__main__":
    sys.exit(main())

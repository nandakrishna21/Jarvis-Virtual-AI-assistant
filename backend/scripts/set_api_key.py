"""Set the JARVIS API key in backend/.env without echoing it to the screen.

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\set_api_key.py

Needed for LAN mode: when the server is reachable from a phone or another
device, every API call must carry the key. After it succeeds, restart JARVIS
in LAN mode:
    powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\stop_prod.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\start_prod.ps1 -Lan
"""
import getpass
import pathlib
import secrets
import sys

ENV_FILE = pathlib.Path(__file__).resolve().parents[1] / ".env"


def main() -> int:
    if not ENV_FILE.exists():
        print(f"No .env at {ENV_FILE}. Create it first with LLM_PROVIDER and NVIDIA_MODEL lines.")
        return 1

    key = getpass.getpass("Paste the JARVIS API key (hidden), or press Enter to generate one: ").strip()
    if not key:
        key = secrets.token_urlsafe(32)
        print("Generated a new random key.")

    if len(key) < 16:
        print("That key is too short. Use at least 16 characters.")
        return 1

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith("JARVIS_API_KEY="):
            lines[i] = f"JARVIS_API_KEY={key}"
            replaced = True
    if not replaced:
        lines.append(f"JARVIS_API_KEY={key}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated JARVIS_API_KEY in {ENV_FILE} (value hidden).")
    print("The phone asks for this key once and keeps it on the device.")
    print("Restart JARVIS in LAN mode:")
    print("  powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\stop_prod.ps1")
    print("  powershell -NoProfile -ExecutionPolicy Bypass -File C:\\JARVIS\\scripts\\start_prod.ps1 -Lan")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Run the Gmail OAuth flow locally.

Usage (PowerShell, from C:\\JARVIS\\backend):
    .\\.venv\\Scripts\\python scripts\\gmail_auth.py

Requires C:\\JARVIS\\credentials\\credentials.json (Desktop OAuth client).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.integrations import gmail_client

def main():
    scopes = gmail_client.SCOPES_READONLY
    if "--send" in sys.argv:
        print("Requesting Gmail send scope. JARVIS still requires per-message approval.")
        scopes = gmail_client.SCOPES_SEND
    print("Opening local OAuth flow on http://localhost:8765 ...")
    creds = gmail_client.run_local_flow(scopes)
    print("Authenticated. Token saved to", gmail_client.TOKEN_FILE)
    print("Scopes:", creds.scopes)

if __name__ == "__main__":
    main()

import os, pathlib
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_DIR = pathlib.Path(os.environ.get("JARVIS_CREDENTIALS_DIR", r"C:\JARVIS\credentials"))
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"

SCOPES_READONLY = ["https://www.googleapis.com/auth/gmail.readonly"]
SCOPES_SEND = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

def credentials_exist() -> bool:
    return CREDENTIALS_FILE.exists()

def token_exists() -> bool:
    return TOKEN_FILE.exists()

def load_credentials(scopes=SCOPES_READONLY):
    if not TOKEN_FILE.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return creds

def save_credentials(creds):
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_DIR.chmod(0o700)
    TOKEN_FILE.write_text(creds.to_json())

def run_local_flow(scopes=SCOPES_READONLY, port: int = 8765):
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}. See docs/GMAIL_SETUP.md")
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), scopes)
    creds = flow.run_local_server(port=port, open_browser=False)
    save_credentials(creds)
    return creds

def build_service(scopes=SCOPES_READONLY):
    from googleapiclient.discovery import build
    creds = load_credentials(scopes)
    if not creds:
        raise RuntimeError("Gmail not authenticated. Run scripts/gmail_auth.py first.")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

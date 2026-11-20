# Mobile App & Installable PWA

## What you can do
JARVIS is an installable progressive web app (PWA). It works on a phone or tablet, can be added to the home screen, and opens like a normal app (no browser bar).

## Two ways to reach it

### 1. On the same device (simplest)
Open `http://127.0.0.1:8000` in Chrome/Edge on the laptop. Use the browser menu - **Install app**. It installs to the desktop.

### 2. From your phone (LAN mode)
The server normally listens on `127.0.0.1` only, which is the safe default. To use it from a phone on the same Wi-Fi, start it in LAN mode:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\JARVIS\scripts\start_prod.ps1 -Lan
```

The script prints the phone URL, for example `http://192.168.1.14:8000`. Open it on the phone while both devices are on the same Wi-Fi.

### LAN mode needs an API key
With `-Lan` the server listens on every network interface, so every API call must carry the key:

```powershell
cd C:\JARVIS\backend
.\.venv\Scripts\python scripts\set_api_key.py
```

Put that key in `JARVIS_API_KEY` in `backend\.env`, restart JARVIS in LAN mode, then on the phone open the app - it shows an **Unlock JARVIS** screen, asks for the key once, and keeps it on the device (`localStorage`). The key is sent in the `X-API-Key` header.

Without `JARVIS_API_KEY`, LAN mode refuses API calls with `503 LAN mode needs an API key` instead of exposing your resume and inbox to the whole network.

## Installing on the phone
- **Android / Chrome**: open the URL -> menu -> **Install app** (or Add to Home screen).
- **iPhone / Safari**: open the URL -> Share -> **Add to Home Screen**.

The dashboard shows an **Install app** button once the browser reports the app can be installed.

### Important limitation
A full PWA install with offline support needs a **secure context** (HTTPS) or `localhost`.
- Over `http://192.168.x.x` the app still installs as a home-screen shortcut and works fully while the phone is on the same network, but the service worker will not register and offline caching stays off.
- For true offline install, put the server behind HTTPS (Cloudflare Tunnel, Tailscale with HTTPS, or a reverse proxy with a certificate) and open it over `https://`.

## What was built for mobile
- **Bottom navigation bar** on phones (Home, Ask, Voice, Matches, Generate) with the full menu in the drawer.
- **Safe-area padding** for notched phones (`env(safe-area-inset-bottom)`).
- **Touch-sized buttons** on the voice page and the install prompt.
- **Offline app shell**: the service worker caches the built app so it opens instantly and shows the shell without a network.
- **Never cached**: API responses. Job and email data is always fetched live, so the app never shows stale applications.
- **State kept on the device**: the voice conversation and the resume "My details" form are stored in Redux and saved to `localStorage`, so you can close the app mid-way and come back.

## State management (Redux Toolkit)
| Slice | What it holds |
| --- | --- |
| `app` | system status, pending approvals, LLM provider, Gmail connection |
| `ui` | sidebar state, install prompt, toast messages |
| `resume` | the "My details" form, entries, save state |
| `voice` | conversation turns, listening state, continuous/wake-word settings |

Store: `frontend/src/store/`. Typed hooks: `frontend/src/store/hooks.ts`.

## Endpoints used by the mobile app
- `GET /health` - used by the unlock gate to check the key
- `GET /system/status`, `GET /system/auth`, `GET /system/llm`
- `POST /voice/agent` - the conversational voice turn
- `GET /resumes`, `GET /resumes/{id}/details`, `PUT /resumes/{id}/details`
- `GET /jobs`, `/jobs/top-matches`, `/emails`, `/tasks`, `/actions`, `/analytics/overview`

## Troubleshooting
- **Phone shows "Unlock JARVIS"** - the key is missing or wrong. Copy it from `backend\.env` (`JARVIS_API_KEY`).
- **Phone cannot reach the server** - the phone and the PC must be on the same Wi-Fi, and the PC firewall must allow port 8000 on private networks.
- **"Install app" not shown** - the browser only offers it on HTTPS/localhost, or after the service worker has registered at least once.
- **Microphone does not work on the phone** - iOS Safari needs the page served over HTTPS for microphone access in some versions; Chrome on Android works over LAN HTTP.

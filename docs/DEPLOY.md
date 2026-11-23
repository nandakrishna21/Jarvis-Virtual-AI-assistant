# Deploying JARVIS (public resume demo)

JARVIS is a single FastAPI service that also serves the built React dashboard.
One container = one public URL, no CORS, no second service. This is the cheapest
and simplest shape for a resume link.

## Why this stack

| Option | Fit | Notes |
| --- | --- | --- |
| **Render (Docker, free)** | Recommended | Free web service, HTTPS, custom domains, secrets dashboard. Sleeps after 15 min idle. |
| Railway | Good | Simple Docker deploys, limited trial credit. |
| Fly.io | Good | Needs a credit card, scale-to-zero. |
| Vercel/Netlify | Not for this backend | Great for the static React build, but the Python API needs a separate host. |

The included `Dockerfile` builds the React app with Node and then runs the
FastAPI app with Python, so Render only needs to build one image.

## What gets deployed

- `backend/` FastAPI app + `frontend/dist` served from the same origin.
- No `.env`, Gmail tokens, SQLite data, resumes, logs, or `credentials/`
  (see `.dockerignore`).
- `DEMO_MODE=true` (set in `render.yaml`): visitors get chat, weather and
  read-only safe routes; Gmail, files, uploads, shell/host actions, schedules
  and automations return `403`. Every route is rate limited per IP.

## 1. Push the code

```powershell
cd C:\JARVIS
git add .
git commit -m "Production hardening: key rotation, rate limits, mobile fixes, deploy config"
git push origin master
```

Make sure `backend/.env` is **not** in the commit (`git status` should not list it).

## 2. Deploy on Render (blueprint)

1. Create a free account at <https://render.com> and connect GitHub.
2. **New +** → **Blueprint**.
3. Select the `Jarvis-Virtual-AI-assistant` repository.
4. Render reads `render.yaml` and shows a `jarvis-demo` web service.
5. When prompted for `NVIDIA_API_KEY`, paste the **new** `nvapi-...` value.
   Leave it as a secret (never put it in the repo).
6. Click **Apply** / **Create**. The first build takes ~4–8 minutes
   (Node build + Python install).
7. Wait for `Live`. Your URL looks like
   `https://jarvis-demo-xxxx.onrender.com`.

> Free instances sleep after ~15 minutes idle. The first visit after sleeping
> can take 30–60 seconds. The UI retries automatically.

## 3. Manual alternative (no blueprint)

1. Render → **New +** → **Web Service** → connect the repo.
2. Language: **Docker**. Dockerfile path: `./Dockerfile`. Plan: **Free**.
3. Health check path: `/health`.
4. Add environment variables:
   - `LLM_PROVIDER=nvidia`
   - `NVIDIA_API_KEY=<your new key>` (secret)
   - `NVIDIA_MODEL=nvidia/nemotron-3.5-bolt-e4b`
   - `DEMO_MODE=true`
   - `JARVIS_API_KEY=` (empty in demo mode)
   - `N8N_ENABLED=false`
   - `DATABASE_URL=sqlite:///./jarvis.db`
5. Create the service.

## 4. Verify the live URL

```powershell
$u = "https://YOUR-APP.onrender.com"
Invoke-RestMethod "$u/health"                      # { status: ok, demo: true }
Invoke-RestMethod "$u/api/assistant/greeting"      # greeting payload
Invoke-WebRequest "$u/api/files" -SkipHttpErrorCheck | Select-Object StatusCode  # 403
```

Then open the URL on a phone (Wi-Fi off, mobile data on) and check:

- Layout fits without horizontal scrolling.
- Typing in a field does not zoom the page (iOS).
- Ask JARVIS a question in the assistant; the reply arrives.
- Voice: Chrome on Android works on HTTPS; iOS Safari asks for the mic and
  should be tapped per turn.
- `https://YOUR-APP.onrender.com/manifest.webmanifest` loads and "Add to Home
  Screen" installs the PWA.

## 5. Rotate the NVIDIA key

1. Open <https://build.nvidia.com> → your profile → **API Keys**.
2. Delete the old key (`nvapi-1ayM...`) so it stops working.
3. Create a new key and put it only in:
   - local `backend/.env` (`NVIDIA_API_KEY=...`), and
   - the hosting dashboard secret (`NVIDIA_API_KEY`).
4. Never paste a key into frontend code, `VITE_*` variables, or git.

A leaked key should be revoked immediately; rotating it invalidates the old one.

## 6. Keep the private local instance private

The Windows production script already binds to `127.0.0.1`:

```powershell
C:\JARVIS\scripts\start_prod.ps1          # localhost only
C:\JARVIS\scripts\start_prod.ps1 -Lan     # LAN/Tailscale + API key required
```

Use Tailscale Serve for phone access to the real instance:

```powershell
tailscale serve --bg 8000
# https://<machine>.<tailnet>.ts.net -> http://127.0.0.1:8000
```

Do **not** enable Gmail on the public demo instance; the Gmail routes are
blocked in demo mode anyway.

## Environment variables

| Variable | Purpose | Demo value |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` / `nvidia` / `gemini` / `openrouter` | `nvidia` |
| `NVIDIA_API_KEY` | Server-side NVIDIA NIM key | secret |
| `NVIDIA_MODEL` | Model id | `nvidia/nemotron-3.5-bolt-e4b` |
| `DEMO_MODE` | Safe public mode, no local key | `true` |
| `JARVIS_API_KEY` | Key for the private/LAN instance | empty |
| `CORS_ORIGINS` | Comma-separated dev origins | empty |
| `RATE_LIMIT_CHAT_PER_MINUTE` | Chat turns per IP | `20` |
| `RATE_LIMIT_VOICE_PER_MINUTE` | Voice turns per IP | `15` |
| `RATE_LIMIT_API_PER_MINUTE` | Other API calls per IP | `180` |
| `DATABASE_URL` | SQLite path (ephemeral on free hosts) | `sqlite:///./jarvis.db` |
| `N8N_ENABLED` | Local automation bridge | `false` |

## Troubleshooting

- **Build fails on `npm ci`**: commit `frontend/package-lock.json`.
- **502 / app not booting**: check Render logs; usually a missing
  `NVIDIA_API_KEY` or a syntax error. `/health` needs no key.
- **Chat falls back to Ollama / times out**: the deployed host has no Ollama,
  so verify `LLM_PROVIDER=nvidia` and that the key is valid.
- **Voice says HTTPS required**: microphone capture only works on HTTPS or
  localhost. Render provides HTTPS automatically.
- **Data disappears after redeploy**: free hosts use an ephemeral filesystem.
  This is expected for a demo; the real instance keeps its local SQLite file.

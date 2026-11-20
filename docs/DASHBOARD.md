# JARVIS Dashboard (Phase 8)

## What it does
One responsive React dashboard for every JARVIS module: Dashboard, AI Chat, Jobs, Applications, Gmail, Hiring News, Exam Mentor, Tasks, Developer, Files, Approvals, System Monitor, Settings.

## Why required
One central interface instead of separate tools. Every page talks to the same FastAPI backend through a single API client.

## Stack
React 19 + Vite 8 + TypeScript 7 + Tailwind CSS 4. No UI framework, no extra state library.

## Run
```powershell
# terminal 1 - backend
cd C:\JARVIS\backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000

# terminal 2 - frontend
cd C:\JARVIS\frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173

## Build for production
```powershell
npm run build     # type-check + bundle into frontend\dist
npm run preview   # serve the built bundle
```

## How the frontend reaches the backend
`vite.config.ts` proxies `/api/*` to `http://127.0.0.1:8000/*`, so the browser only ever talks to 127.0.0.1. No CORS exposure, nothing exposed to the network.

## Structure
- `src/services/api.ts` — typed API client + all response types
- `src/hooks/useApi.ts` — fetch hook with loading/error state
- `src/components/ui.tsx` — Card, Stat, Badge, Button, Input, Loading, ErrorBox, Empty
- `src/components/Layout.tsx` — sidebar, live CPU/RAM/Ollama status header, mobile drawer
- `src/pages/*.tsx` — one file per module

## Safety in the UI
- Approvals page shows the exact snapshot and requires an explicit click.
- Job search results are labelled `unverified` until you open the original link.
- File browser is limited to `C:\JARVIS` (the backend enforces it).
- Delete task asks for browser confirmation.

## Verify
```powershell
curl http://127.0.0.1:5173/api/health          # proxy works
npm run build                                  # typecheck + build clean
npx oxlint                                     # lint clean
```

## Common errors
- Blank page → check the backend is running on port 8000; open browser console.
- `ERR_CONNECTION_REFUSED` on `/api` → backend not started.
- Port 5173 busy → Vite picks the next free port; use the URL it prints.
- Changes not appearing → Vite hot reload; hard refresh if a page is stale.

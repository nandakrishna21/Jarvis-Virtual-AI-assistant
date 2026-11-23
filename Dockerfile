# syntax=docker/dockerfile:1

# ---- Build the React dashboard ----
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
ENV NODE_OPTIONS=--max-old-space-size=768
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Runtime: FastAPI serves the API and the built SPA ----
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

RUN useradd --create-home --shell /usr/sbin/nologin jarvis \
    && chown -R jarvis:jarvis /app
USER jarvis

EXPOSE 8000
# /health is public and cheap, so it doubles as the platform health check.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

# syntax=docker/dockerfile:1

# --- Build the PWA ---------------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build

# --- Runtime ---------------------------------------------------------------
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r backend/requirements.txt
COPY backend/app backend/app
COPY --from=web /web/dist frontend/dist

RUN useradd --create-home --uid 1000 app && mkdir /data && chown app /data
USER app
WORKDIR /app/backend
# Fallbacks only — docker-compose passes the real values from .env.
ENV DATA_DIR=/data \
    CLAUDE_MODEL=claude-opus-5-5 \
    TIMEZONE=Asia/Seoul \
    AZURE_SPEECH_REGION=koreacentral \
    GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

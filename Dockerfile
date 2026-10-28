# syntax=docker/dockerfile:1

# --- Frontend build. Node is needed only here, never at runtime. ---
FROM node:24-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Runtime ---
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY app/ app/
COPY presets/ presets/
COPY locales/ locales/
# The client's logo, icon and photo, added to the upload by tools/deploy.py.
COPY brand/ brand/
COPY --from=frontend /build/dist frontend/dist

# The commit being deployed; /healthz reports it so a deploy can confirm
# that the new code, not the previous one, is answering.
ARG GIT_SHA=""
ENV GIT_SHA=${GIT_SHA}

# data/uploads: photos on a server of the client's own (deploy/vps). A volume
# mounted there starts with the app's ownership. Railway keeps them in a bucket.
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p data/uploads && chown -R app data
USER app

EXPOSE 8000
# Migrations run first: the app never serves against an outdated schema.
# Forwarded headers are trusted from any address because the container is
# reachable only through the hosting provider's proxy; they give the app the
# https scheme. Rate limits do not use the forwarded client address
# (undocumented on Railway, and the client's own text behind some proxies):
# they read CLIENT_IP_HEADER, X-Real-IP on Railway. No access log: it would
# write every visitor's address, which the privacy policy says is never stored;
# the app logs its own events with ids only.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --no-access-log"]

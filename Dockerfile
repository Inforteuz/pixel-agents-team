FROM node:24-bookworm-slim AS web
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIXEL_DATA_DIR=/srv/pixel-team/data
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && mkdir -p /srv/pixel-team/data /srv/pixel-team/briefs \
    && chown 10001:10001 /srv/pixel-team/data
COPY backend/ backend/
COPY web/public/ web/public/
COPY --from=web /build/web/dist/ web/dist/
USER 10001:10001
EXPOSE 8091
CMD ["uvicorn", "backend.entrypoint:app", "--host", "0.0.0.0", "--port", "8091", "--no-access-log"]

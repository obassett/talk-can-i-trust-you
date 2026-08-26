FROM python:3.12-slim

WORKDIR /app

# Install the package (spiffe_demo + deps) first for better layer caching.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# App code that runs from the working dir (namespace packages).
COPY services ./services
COPY scripts ./scripts

ENV PYTHONUNBUFFERED=1 \
    SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/api.sock

# Each service overrides `command:` in docker-compose.yml.

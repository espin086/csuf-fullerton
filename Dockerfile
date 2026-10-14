# syntax=docker/dockerfile:1.7
# Multi-stage: build a wheel with uv, run it as a non-root user on slim Python.
# The CLI is the entrypoint; `docker run <image> --version` is the smoke test.

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /usr/local/bin/uv
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN uv build --wheel --out-dir /dist

FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# Apply Debian security patches so Trivy's fixable CRITICAL/HIGH list is empty.
# hadolint ignore=DL3005
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl
USER 10001:10001
WORKDIR /home/app
ENTRYPOINT ["csuf-fullerton"]
CMD ["--help"]

LABEL org.opencontainers.image.source="https://github.com/espin086/template-python-cli" \
      org.opencontainers.image.licenses="MIT"

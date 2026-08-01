FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY backend/pyproject.toml backend/README.md /build/backend/
COPY backend /build/backend
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install /build/backend

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system frontierops \
    && useradd --system --gid frontierops --create-home frontierops

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY backend /app
RUN chown -R frontierops:frontierops /app
USER frontierops

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

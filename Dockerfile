# syntax=docker/dockerfile:1
###############################################################################
# Build stage: install Python dependencies into an isolated venv
###############################################################################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build tools are only needed at build time; they are not shipped in the final image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

###############################################################################
# Runtime stage: slim image with only what's needed to run the app
###############################################################################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=hydro.settings

# libpq5 is required at runtime for psycopg2 to connect to PostgreSQL/RDS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system django && useradd --system --gid django --home /app django

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY hydro/ /app/

RUN mkdir -p /app/staticfiles \
    && sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && chown -R django:django /app

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "hydro.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]

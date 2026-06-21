FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY migrations migrations
COPY scripts scripts

RUN useradd --create-home appuser \
    && mkdir -p backend/uploads backend/outputs \
    && chown -R appuser:appuser backend/uploads backend/outputs migrations scripts

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["sh", "-c", "python scripts/migrate.py && gunicorn backend.app.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 300 --graceful-timeout 30 --access-logfile - --error-logfile -"]

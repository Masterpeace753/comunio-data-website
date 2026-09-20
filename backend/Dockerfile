FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app migrations ./migrations
COPY --chown=app:app src ./src
COPY --chown=app:app tests/sample_snapshot.json ./tests/sample_snapshot.json

USER app
CMD ["python", "-m", "src.ingest.runner", "--run-type", "manual", "--mode", "snapshot"]
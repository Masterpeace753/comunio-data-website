FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app && adduser --system --ingroup app app

COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && python -m pip uninstall -y pip

COPY --chown=app:app migrations ./migrations
COPY --chown=app:app src ./src
COPY --chown=app:app tests/sample_snapshot.json ./tests/sample_snapshot.json

USER app
CMD ["python", "-m", "src.ingest.runner", "--run-type", "manual", "--mode", "snapshot"]
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production DATA_DIR=/app/data
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng libespeak1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[ml,voice]" && useradd --create-home --uid 10001 appuser && mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "ai_portfolio.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM python:3.11-slim

# Install curl for healthchecks add libpq5 for container sql library (staging benefit)
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    # Staging often mirrors production security
    # FLASK_DEBUG=0 lets pass this via the deploy in github actions workflow
    PATH="/home/myuser/.local/bin:${PATH}" \
    NEW_RELIC_LOG="stdout" \
    NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true \
    NEW_RELIC_BROWSER_MONITORING_AUTO_INSTRUMENT=true \
    NEW_RELIC_APPLICATION_LOGGING_ENABLED=true \
    NEW_RELIC_APPLICATION_LOGGING_FORWARDING_ENABLED=true \
    NEW_RELIC_APPLICATION_LOGGING_METRICS_ENABLED=true

WORKDIR /app

RUN useradd -m myuser
USER myuser

COPY --chown=myuser:myuser --chmod=440 requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

RUN pip install --no-cache-dir \
    "Jinja2>=3.1.6" \
    "cryptography>=46.0.5" \
    "urllib3>=2.6.3" \
    "setuptools>=78.1.1" \
    "wheel>=0.46.2" \
    "certifi>=2024.7.4" \
    "idna>=3.7" \
    "requests>=2.32.4" \
    && pip install --upgrade pip

COPY --chown=myuser:myuser --chmod=440 app.py .

COPY --chown=myuser:myuser templates/ ./templates/
COPY --chown=myuser:myuser static/ ./static/

# Verify the app is running
HEALTHCHECK --interval=1m --timeout=3s \
  CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80

CMD ["newrelic-admin", "run-program", "gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "--log-level", "warning", "app:app"]
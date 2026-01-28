FROM python:3.11-slim

# Install curl for healthchecks (staging benefit)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    # Staging often mirrors production security
    FLASK_DEBUG=1 \
    PATH="/home/myuser/.local/bin:${PATH}"

WORKDIR /app

RUN useradd -m myuser
USER myuser

COPY --chown=myuser:myuser --chmod=440 requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=myuser:myuser --chmod=440 app.py .

# Verify the app is running
HEALTHCHECK --interval=1m --timeout=3s \
  CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "--log-level", "debug", "app:app"]
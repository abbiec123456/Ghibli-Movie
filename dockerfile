FROM python:3.11-slim

# Install curl for healthchecks (staging benefit)
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=App.py \
    # Staging often mirrors production security
    FLASK_DEBUG=0 

WORKDIR /app

RUN useradd -m myuser
USER myuser

COPY --chown=myuser:myuser requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

ENV PATH="/home/myuser/.local/bin:${PATH}"

COPY --chown=myuser:myuser App.py .

# Verify the app is running
HEALTHCHECK --interval=1m --timeout=3s \
  CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "--log-level", "debug", "App:app"]
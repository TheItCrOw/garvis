FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN python -m pip install -U pip \
    && pip install -e .

# Copy the actual code
COPY . .

EXPOSE 8000

# Google ADC notes:
# - Provide credentials at runtime by mounting an Application Default Credentials file
#   and setting GOOGLE_APPLICATION_CREDENTIALS to its path.
# - Also set your quota/billing project via GOOGLE_CLOUD_QUOTA_PROJECT.
#
# Example in docker-compose:
#   environment:
#     - GOOGLE_APPLICATION_CREDENTIALS=/secrets/adc.json
#     - GOOGLE_CLOUD_QUOTA_PROJECT=your-project
#   volumes:
#     - ~/.config/gcloud/application_default_credentials.json:/secrets/adc.json:ro

CMD ["python", "-m", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]

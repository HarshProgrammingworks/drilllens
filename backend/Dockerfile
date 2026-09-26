FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libpq5 \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN python -m spacy download en_core_web_sm || echo "spaCy model download failed; regex rules remain active"

COPY backend /app
COPY scripts /scripts
COPY docs /docs

RUN mkdir -p /app/uploads/reports /app/uploads/processed /app/uploads/previews \
    && chmod +x /app/entrypoint.sh

ENV TESSERACT_PATH=/usr/bin/tesseract \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIRECTORY=/app/uploads

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

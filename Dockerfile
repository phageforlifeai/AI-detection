FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scigram/ ./scigram/
COPY static/ ./static/
COPY server.py README.md pyproject.toml ./

ENV PORT=8000
ENV SCIGRAM_MODEL_DIR=/app/.cache/scigram_models

EXPOSE 8000

CMD ["python3", "server.py"]

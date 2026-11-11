FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrape_pipeline/ ./scrape_pipeline/

ENTRYPOINT ["python", "-m", "scrape_pipeline"]

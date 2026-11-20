FROM python:3.12-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "moveinsync_ai:app", "--host", "0.0.0.0", "--port", "8000"]

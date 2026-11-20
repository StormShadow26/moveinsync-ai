FROM node:22-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=frontend-build /frontend/dist ./src/moveinsync_ai/frontend/dist
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "moveinsync_ai:app", "--host", "0.0.0.0", "--port", "8000"]

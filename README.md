# MoveInSync AI

Basic FastAPI service for the MoveInSync AI project.

## Run locally

Start the development server with reload enabled:

```bash
uv run uvicorn moveinsync_ai:app --reload
```

Or run the packaged entry point:

```bash
uv run moveinsync-ai
```

The API is available at `http://127.0.0.1:8000`. Interactive API docs are at
`http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /` returns a welcome/status message.
- `GET /health` returns `{"status": "ok"}`.

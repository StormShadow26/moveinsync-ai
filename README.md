# MoveInSync Ask Your Data

Ask transport questions against a company-scoped PostgreSQL dataset. The API returns the answer, final SQL, columns and rows; the web workspace shows them in a conversation.

## Run

Install Docker and Docker Compose. Copy `.env.example` to `.env` and set `GROQ_API_KEY` to a free-tier key for the live demo. Never commit the key. Start the stack:

```sh
docker compose up --build
```

Open http://localhost:8000. On an empty database startup creates the schema and seeds three synthetic companies. Sign in as `admin1@example.com`, `admin2@example.com`, `admin3@example.com`, or `ops@example.com`; in the default development configuration the OTP is printed in the API container logs (`docker compose logs api`). The operations user is assigned only companies 1 and 2. No real email is sent unless SMTP is configured. Existing nonempty databases are not seeded or reset.

The demo seed includes 15 company-scoped business tables, three companies, trips, routes, vehicles, bookings, rosters and invoices. Two invoice lines point to one trip to expose double-counting mistakes. The date values are fixed for repeatability. Data in an existing container is not automatically replaced by the seed. Use a separate empty database to reproduce the evaluation.

## Tests and evaluation

The regular tests use fake models and never require Groq:

```sh
docker compose exec -e SEED_DEMO=0 api python -m pytest -q
docker compose exec api python evaluation/run.py
```

The first command skips PostgreSQL integration tests unless `TEST_POSTGRES_ADMIN_URL` and `TEST_POSTGRES_APP_URL` point to an **empty, disposable** PostgreSQL database; those tests insert records and must never be run against an existing dataset. `evaluation/run.py` expects the pristine demo seed. It emits one JSON object per case in the required format; [evaluation/results.jsonl](evaluation/results.jsonl) contains the observed deterministic run. [evaluation/report.md](evaluation/report.md) records the method and limitations. To run the optional live schema comparison, use `docker compose exec api python evaluation/compare.py`; it makes model calls, so use a free-tier key.

For the full suite, create a new empty test database once and run:

```sh
docker compose exec db createdb -U moveinsync moveinsync_test
docker compose exec -e SEED_DEMO=0 -e TEST_POSTGRES_ADMIN_URL=postgresql+psycopg://moveinsync:moveinsync@db:5432/moveinsync_test -e TEST_POSTGRES_APP_URL=postgresql+psycopg://moveinsync_app:moveinsync_app@db:5432/moveinsync_test api python -m pytest -q
```

Use a different fresh database name on each run. The integration tests intentionally populate it.

## Design and trade-offs

* Login issues JWTs with the user role and allowed company IDs. Admins have one company; internal managers receive explicitly assigned companies. PostgreSQL RLS intersects that list with the thread's selected scope. Existing manager accounts need entries in `user_companies` to log in after this change.
* SQL runs as `moveinsync_query`, a separate NOLOGIN role with SELECT on approved transport tables only. A parser restricts SQL to one SELECT, approved tables and functions, and rejects cross joins and unsafe operations. The query executor sets transaction-local RLS context, switches to the query role and enforces a maximum 10-second timeout and 500 rows (defaults 10 and 100).
* Chroma indexes curated schema descriptions using local deterministic hashed word vectors; no embedding model or external embedding API is required. Relevant documents and reviewed join/metric rules are passed to Groq. This simple approach is reproducible but may miss synonyms or select unnecessary context.
* The LangGraph workflow permits at most two SQL generation calls, including one validation repair, plus one answer-generation call: **at most three LLM calls per question**. Deterministic validation and PostgreSQL enforce security, not the LLM.
* Conversation messages store the question, answer, SQL and summary. Rows are returned immediately but are not persisted; they disappear from the UI after a reload. Ambiguity handling currently asks about the definition of “active trips”; it is not a comprehensive semantic ambiguity detector.
* The bootstrap schema account must be able to create tables and the read-only role. The app role is separate. OTP logging and demo secrets are for local development only. This case study is not configured for production deployment.

# Two-minute demo script

Record the browser and your voice after starting the stack. Use only the synthetic demo accounts and data.

For the currently running isolated validation stack, use `docker compose -p codex-validation logs api` to find the OTP. For a normal `docker compose up --build` stack, use `docker compose logs api` instead.

* **0:00–0:15** — Introduce the goal: transport administrators ask plain-English questions and receive results from PostgreSQL.
* **0:15–0:35** — Sign in as `admin1@example.com`. Obtain the one-time code from `docker compose logs api`; do not show your API key or the contents of `.env`.
* **0:35–0:55** — Create a company-scoped chat and ask “How many trips are there?” Expand **View SQL** and show the returned row and explanation.
* **0:55–1:15** — Ask “How many no-shows?” Explain that the admin's JWT and PostgreSQL RLS limit the result to their assigned company.
* **1:15–1:35** — Sign out and sign in as `ops@example.com`. Create a chat for **All assigned companies** and repeat the trip-count question. This manager can see companies 1 and 2, but not company 3.
* **1:35–1:50** — Show `evaluation/results.jsonl` and `evaluation/report.md`. Explain that deterministic SQL tests are repeatable without a model, while the separate live comparison measures generated SQL.
* **1:50–2:00** — State the key trade-off and limitation: locally hashed schema embeddings are inexpensive and reproducible, but retrieval and ambiguity handling need broader evaluation.

If the free-tier model is unavailable, explain the error and show the saved evaluation results; do not claim a live query succeeded if it did not.

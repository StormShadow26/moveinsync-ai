# Evaluation report

## Method

The dataset is a fresh three-company demo seed, with a manager allowed companies 1 and 2 only. Expected results were calculated independently from the fixed seed records in `demo_seed.py`. `run.py` validates and executes a fixed SQL query for each question under the specified scope; the 11 results are in `results.jsonl`. These tests exercise the parser, read-only role, row-level policies and PostgreSQL results, but **do not measure the model's ability to generate SQL**. The invoice case includes two invoice lines for one trip and checks distinct trip counting.

`compare.py` runs each of those questions once using Groq with Chroma-selected context and once using full curated schema context. It validates and executes the generated SQL and compares the returned scalar or empty result with the independently calculated expectation. `comparison.jsonl` records each actual result and the schema-context character count. Context characters are a prompt-size proxy, not model token counts. Each mode uses one SQL generation call per case; this comparison does not exercise the graph's retry and summarization steps.

## Observed results

* Deterministic SQL: **11/11** cases passed, including the client cross-company and restricted-manager cases.
* One live Groq comparison: **Chroma 10/11**, mean schema context **481 characters**; **full schema 10/11**, 2,609 characters. On this small sample the retrieved context was approximately 82% shorter. These are single stochastic runs, not a reliable estimate of overall model accuracy.
* The full-schema model returned 0 instead of 1 for “How many trips does Acme have?” under the Acme scope. The raw results are retained rather than corrected after the fact.
* The Chroma-context model returned 0 instead of 1 for “How many trips use Fleet 1?” even after adding fleet-to-vendor terminology. Inspection showed it compared the name to the vendor code. After the recorded comparison, the registry was clarified to distinguish `vendors.name` and `vendors.code`; one follow-up returned the correct result, but the full comparison has not been rerun with that change. Earlier live testing also found that a generated occupancy query omitted the required aggregation for capacity; the curated metric context now supplies an example.
* PostgreSQL integration tests check company lists, prohibited company selection, thread ownership, query role privileges and answers for multiple scopes. The regular suite uses fake model responses, so Groq availability is not required for it.

## Limitations and trade-offs

Chroma uses local hashed-word vectors and curated relationships, not a trained semantic embedding model. It is cheap and reproducible, but synonyms and complex business questions can retrieve incomplete context. The small seeded dataset does not establish performance on production data or every join. The demo includes one fixed day and simple metrics; relative dates and broader ambiguous definitions need more coverage.

The service asks for a definition of “active trips”, but does not detect every ambiguous metric or unstated time period. A generated SQL query that parses but fails at execution produces a safe error rather than a SQL-repair retry. Rows are displayed for the current answer but are not persisted in history. This is a development prototype: demo OTP logging, bootstrap privileges and secrets require production hardening. Never use a production database for the evaluation tests.

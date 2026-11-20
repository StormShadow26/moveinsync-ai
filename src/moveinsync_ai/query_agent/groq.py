"""Groq implementation of the language-model contract."""

import json

from groq import Groq

from .contracts import QueryConfigurationError, QueryProviderError, QueryResult, SqlGenerator


class GroqSqlGenerator:
    def __init__(self, api_key: str | None, model: str):
        self._api_key = api_key
        self._model = model

    def generate_sql(self, question: str, schema_context: str, previous_error: str | None = None) -> str:
        repair = f"\nThe previous SQL was rejected: {previous_error}. Correct it." if previous_error else ""
        return self._complete(
            "You write one PostgreSQL SELECT statement for a transport analyst. "
            "Return SQL only: no Markdown, explanation, DDL, DML, SET commands, or company filter.\n\n"
            f"Schema:\n{schema_context}\n\nQuestion: {question}{repair}"
        )

    def summarize(self, question: str, result: QueryResult) -> str:
        payload = json.dumps(result.rows, default=str)
        return self._complete(
            "Answer the transport analyst's question using only these SQL result rows. "
            "Be concise. State when no matching data was returned. Do not claim information absent from the rows.\n\n"
            f"Question: {question}\nRows: {payload}"
        )

    def _complete(self, prompt: str) -> str:
        if not self._api_key:
            raise QueryConfigurationError("The data assistant is not configured. Set GROQ_API_KEY to enable it.")
        try:
            completion = Groq(api_key=self._api_key).chat.completions.create(
                model=self._model,
                temperature=0.1,
                messages=[{"role": "system", "content": "You are a precise data assistant."}, {"role": "user", "content": prompt}],
            )
        except Exception as error:
            raise QueryProviderError("The data assistant is temporarily unavailable.") from error
        return (completion.choices[0].message.content or "").strip()

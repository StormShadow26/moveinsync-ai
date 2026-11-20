"""Groq implementation of the language-model contract."""

import json

from groq import Groq

from .contracts import ChatModel, QueryConfigurationError, QueryProviderError, QueryResult


class GroqChatModel:
    def __init__(self, api_key: str | None, model: str):
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str, *, json_output: bool = False) -> str:
        if not self._api_key:
            raise QueryConfigurationError("The data assistant is not configured. Set GROQ_API_KEY to enable it.")
        try:
            completion = Groq(api_key=self._api_key).chat.completions.create(
                model=self._model,
                temperature=0.1,
                messages=[{"role": "system", "content": "You are a precise data assistant."}, {"role": "user", "content": prompt}],
                **({"response_format": {"type": "json_object"}} if json_output else {}),
            )
        except Exception as error:
            raise QueryProviderError("The data assistant is temporarily unavailable.") from error
        return (completion.choices[0].message.content or "").strip()


class GroqSqlGenerator:
    def __init__(self, model: ChatModel):
        self._model = model

    def generate_sql(self, question: str, schema_context: str, previous_error: str | None = None) -> str:
        repair = f"\nThe previous SQL was rejected: {previous_error}. Correct it." if previous_error else ""
        response = self._model.complete(
            "You write one PostgreSQL SELECT statement for a transport analyst. "
            "Return a JSON object with string fields sql and reasoning_summary. "
            "Use only the listed tables and joins; no cross joins, DDL, DML, SET commands, or company filter. "
            "Use standard aggregate and date functions only. If no time period is specified, do not invent one.\n\n"
            f"Schema:\n{schema_context}\n\nQuestion: {question}{repair}", json_output=True
        )
        try:
            data = json.loads(response)
            sql, summary = data["sql"], data["reasoning_summary"]
            if not isinstance(sql, str) or not sql.strip() or not isinstance(summary, str):
                raise ValueError("Invalid SQL response")
            return sql
        except (ValueError, KeyError, TypeError) as error:
            raise QueryProviderError("The data assistant returned an invalid SQL response.") from error

    def summarize(self, question: str, result: QueryResult) -> str:
        payload = json.dumps(result.rows, default=str)
        return self._model.complete(
            "Answer the transport analyst's question using only these SQL result rows. "
            "Be concise. State when no matching data was returned. Do not claim information absent from the rows.\n\n"
            f"Question: {question}\nRows: {payload}"
        )

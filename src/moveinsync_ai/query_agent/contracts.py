"""Contracts and value objects for the query workflow."""

from dataclasses import dataclass
from typing import Any, Protocol


class QueryAgentError(Exception):
    """A safe error raised while processing a data question."""


class QueryConfigurationError(QueryAgentError):
    """Raised when the query provider is not configured."""


class QueryProviderError(QueryAgentError):
    """Raised when the configured query provider cannot respond."""


class SqlValidationError(QueryAgentError):
    """Raised when generated SQL is not allowed."""


@dataclass(frozen=True)
class QueryScope:
    user_id: int
    company_id: int | None
    access_scope: str
    company_ids: list[int]


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class QueryAnswer:
    content: str
    generated_sql: str
    result_summary: str
    result: QueryResult


class ChatModel(Protocol):
    def complete(self, prompt: str, *, json_output: bool = False) -> str: ...


class SchemaContextRetriever(Protocol):
    def retrieve(self, question: str) -> str: ...


class SqlGenerator(Protocol):
    def generate_sql(self, question: str, schema_context: str, previous_error: str | None = None) -> str: ...

    def summarize(self, question: str, result: QueryResult) -> str: ...


class SqlValidator(Protocol):
    def validate(self, sql: str) -> str: ...


class SqlExecutor(Protocol):
    def execute(self, sql: str, scope: QueryScope) -> QueryResult: ...


class QueryAgent(Protocol):
    def ask(self, question: str, scope: QueryScope) -> QueryAnswer: ...

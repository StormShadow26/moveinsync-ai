"""Repository contracts for persisted chat conversations."""

from typing import Protocol

from ..models import QueryMessage, QueryMessageRole, QueryThread, QueryThreadScope


class QueryThreadRepository(Protocol):
    def create_thread(self, user_id: int, company_id: int | None, scope: QueryThreadScope, title: str) -> QueryThread: ...
    def list_threads(self, user_id: int) -> list[QueryThread]: ...
    def get_thread(self, thread_id: int, user_id: int) -> QueryThread | None: ...
    def create_message(
        self,
        thread: QueryThread,
        role: QueryMessageRole,
        content: str,
        generated_sql: str | None = None,
        result_summary: str | None = None,
    ) -> QueryMessage: ...
    def list_messages(self, thread_id: int, user_id: int) -> list[QueryMessage]: ...

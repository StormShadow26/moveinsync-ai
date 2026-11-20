"""Conversation workflow contracts."""

from dataclasses import dataclass
from typing import Protocol

from ..database.models import QueryMessage, QueryThread, QueryThreadScope, UserType


@dataclass(frozen=True)
class ThreadActor:
    user_id: int
    user_type: UserType
    access_scope: str
    company_id: int | None


class ThreadService(Protocol):
    def create_thread(self, actor: ThreadActor, scope: QueryThreadScope, company_id: int | None, title: str) -> QueryThread: ...
    def list_threads(self, actor: ThreadActor) -> list[QueryThread]: ...
    def list_messages(self, actor: ThreadActor, thread_id: int) -> list[QueryMessage] | None: ...
    def add_message(self, actor: ThreadActor, thread_id: int, content: str) -> QueryMessage | None: ...

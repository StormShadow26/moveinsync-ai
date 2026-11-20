"""SQLAlchemy conversation persistence implementation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import QueryMessage, QueryMessageRole, QueryThread, QueryThreadScope
from .contracts import QueryThreadRepository


class SqlAlchemyQueryThreadRepository:
    def __init__(self, session: Session):
        self._session = session

    def create_thread(self, user_id: int, company_id: int | None, scope: QueryThreadScope, title: str) -> QueryThread:
        thread = QueryThread(user_id=user_id, company_id=company_id, scope=scope, title=title)
        self._session.add(thread)
        self._session.flush()
        return thread

    def list_threads(self, user_id: int) -> list[QueryThread]:
        return list(self._session.scalars(select(QueryThread).where(QueryThread.user_id == user_id).order_by(QueryThread.created_at.desc())))

    def get_thread(self, thread_id: int, user_id: int) -> QueryThread | None:
        return self._session.scalar(select(QueryThread).where(QueryThread.id == thread_id, QueryThread.user_id == user_id))

    def create_message(
        self,
        thread: QueryThread,
        role: QueryMessageRole,
        content: str,
        generated_sql: str | None = None,
        result_summary: str | None = None,
    ) -> QueryMessage:
        message = QueryMessage(
            thread_id=thread.id,
            user_id=thread.user_id,
            company_id=thread.company_id,
            role=role,
            content=content,
            generated_sql=generated_sql,
            result_summary=result_summary,
        )
        self._session.add(message)
        self._session.flush()
        return message

    def list_messages(self, thread_id: int, user_id: int) -> list[QueryMessage]:
        return list(self._session.scalars(select(QueryMessage).where(QueryMessage.thread_id == thread_id, QueryMessage.user_id == user_id).order_by(QueryMessage.created_at)))

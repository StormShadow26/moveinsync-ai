"""Business rules for scoped chat threads."""

from sqlalchemy.orm import Session

from ..database.models import QueryMessage, QueryThread, QueryThreadScope, UserType
from ..database.repositories.contracts import QueryThreadRepository
from ..database.rls import TenantScopeSetter
from .contracts import ThreadActor, ThreadService


class ScopedThreadService:
    def __init__(self, session: Session, repository: QueryThreadRepository, scope_setter: TenantScopeSetter):
        self._session = session
        self._repository = repository
        self._scope_setter = scope_setter

    def create_thread(self, actor: ThreadActor, scope: QueryThreadScope, company_id: int | None, title: str) -> QueryThread:
        company_id = self._resolve_scope(actor, scope, company_id)
        self._apply_scope(actor, company_id, scope)
        thread = self._repository.create_thread(actor.user_id, company_id, scope, title)
        self._session.commit()
        return thread

    def list_threads(self, actor: ThreadActor) -> list[QueryThread]:
        self._apply_scope(actor, actor.company_id, QueryThreadScope.ALL_COMPANIES if actor.company_id is None else QueryThreadScope.COMPANY)
        return self._repository.list_threads(actor.user_id)

    def list_messages(self, actor: ThreadActor, thread_id: int) -> list[QueryMessage] | None:
        thread = self._thread(actor, thread_id)
        return self._repository.list_messages(thread_id, actor.user_id) if thread else None

    def add_message(self, actor: ThreadActor, thread_id: int, content: str) -> QueryMessage | None:
        thread = self._thread(actor, thread_id)
        if thread is None:
            return None
        message = self._repository.create_message(thread, content)
        self._session.commit()
        return message

    def _thread(self, actor: ThreadActor, thread_id: int) -> QueryThread | None:
        self._apply_scope(actor, actor.company_id, QueryThreadScope.ALL_COMPANIES if actor.company_id is None else QueryThreadScope.COMPANY)
        return self._repository.get_thread(thread_id, actor.user_id)

    def _apply_scope(self, actor: ThreadActor, company_id: int | None, scope: QueryThreadScope) -> None:
        access_scope = "all_companies" if scope == QueryThreadScope.ALL_COMPANIES else "single_company"
        self._scope_setter.apply(self._session, actor.user_id, company_id, access_scope)

    @staticmethod
    def _resolve_scope(actor: ThreadActor, scope: QueryThreadScope, company_id: int | None) -> int | None:
        if actor.user_type == UserType.CLIENT_TRANSPORT_ADMIN:
            if scope != QueryThreadScope.COMPANY or company_id != actor.company_id:
                raise PermissionError("Travel admins can create threads only for their company")
            return company_id
        if scope == QueryThreadScope.ALL_COMPANIES:
            return None
        if company_id is None:
            raise ValueError("A company-scoped thread requires a company ID")
        return company_id

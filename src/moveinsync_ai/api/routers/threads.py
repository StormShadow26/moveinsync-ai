"""Authenticated conversation thread endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ...database.models import UserType
from ...database.repositories.query_threads import SqlAlchemyQueryThreadRepository
from ...database.rls import tenant_scope_setter
from ...schemas.query import AddMessageRequest, CreateThreadRequest, MessageResponse, ThreadResponse
from ...services.contracts import ThreadActor, ThreadService
from ...services.thread_service import ScopedThreadService
from ...query_agent.contracts import QueryAgent, QueryAgentError, QueryConfigurationError, QueryProviderError, QueryScope
from ...query_agent.groq import GroqSqlGenerator
from ...query_agent.schema_retrieval import CuratedSchemaRetriever
from ...query_agent.service import LangGraphQueryAgent
from ...query_agent.sql_executor import RlsSqlExecutor
from ...query_agent.sql_validator import ReadOnlySqlValidator
from ..dependencies import SessionDependency, SettingsDependency
from .auth import token_claims

router = APIRouter(prefix="/query/threads", tags=["conversations"])


def thread_service(session: SessionDependency) -> ThreadService:
    return ScopedThreadService(session, SqlAlchemyQueryThreadRepository(session), tenant_scope_setter)


ThreadServiceDependency = Annotated[ThreadService, Depends(thread_service)]
ClaimsDependency = Annotated[dict, Depends(token_claims)]


def query_agent(session: SessionDependency, settings: SettingsDependency) -> QueryAgent:
    return LangGraphQueryAgent(
        CuratedSchemaRetriever(),
        GroqSqlGenerator(settings.groq_api_key, settings.groq_model),
        ReadOnlySqlValidator(),
        RlsSqlExecutor(session, tenant_scope_setter, settings.query_row_limit, settings.query_timeout_seconds),
    )


QueryAgentDependency = Annotated[QueryAgent, Depends(query_agent)]


def actor_from_claims(claims: dict) -> ThreadActor:
    return ThreadActor(int(claims["sub"]), UserType(claims["user_type"]), claims["access_scope"], claims["company_id"])


@router.get("", response_model=list[ThreadResponse])
def list_threads(claims: ClaimsDependency, service: ThreadServiceDependency) -> list[ThreadResponse]:
    return service.list_threads(actor_from_claims(claims))


@router.post("", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(request: CreateThreadRequest, claims: ClaimsDependency, service: ThreadServiceDependency) -> ThreadResponse:
    try:
        return service.create_thread(actor_from_claims(claims), request.scope, request.company_id, request.title)
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("/{thread_id}/messages", response_model=list[MessageResponse])
def list_messages(thread_id: int, claims: ClaimsDependency, service: ThreadServiceDependency) -> list[MessageResponse]:
    messages = service.list_messages(actor_from_claims(claims), thread_id)
    if messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return messages


@router.post("/{thread_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(thread_id: int, request: AddMessageRequest, claims: ClaimsDependency, service: ThreadServiceDependency) -> MessageResponse:
    message = service.add_message(actor_from_claims(claims), thread_id, request.content)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return message


@router.post("/{thread_id}/ask", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def ask_question(
    thread_id: int, request: AddMessageRequest, claims: ClaimsDependency, service: ThreadServiceDependency, agent: QueryAgentDependency
) -> MessageResponse:
    actor = actor_from_claims(claims)
    thread = service.get_thread(actor, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    service.add_message(actor, thread_id, request.content)
    scope = QueryScope(
        user_id=actor.user_id,
        company_id=thread.company_id,
        access_scope="all_companies" if thread.scope.value == "all_companies" else "single_company",
    )
    try:
        answer = agent.ask(request.content, scope)
    except QueryConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except QueryProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except QueryAgentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    message = service.add_assistant_message(actor, thread_id, answer.content, answer.generated_sql, answer.result_summary)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return message

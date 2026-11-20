"""Authenticated company-scope discovery endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from ...database.repositories.companies import CompanyDirectory, SqlAlchemyCompanyDirectory
from ...database.rls import tenant_scope_setter
from ...services.contracts import ThreadActor
from ..dependencies import SessionDependency
from .auth import token_claims
from .threads import actor_from_claims

router = APIRouter(prefix="/query/companies", tags=["conversations"])


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


def company_directory(session: SessionDependency) -> CompanyDirectory:
    return SqlAlchemyCompanyDirectory(session)


DirectoryDependency = Annotated[CompanyDirectory, Depends(company_directory)]
ClaimsDependency = Annotated[dict, Depends(token_claims)]


@router.get("", response_model=list[CompanyResponse])
def list_companies(claims: ClaimsDependency, directory: DirectoryDependency, session: SessionDependency) -> list[CompanyResponse]:
    actor: ThreadActor = actor_from_claims(claims)
    tenant_scope_setter.apply(session, actor.user_id, actor.company_id, actor.access_scope, actor.company_ids)
    return directory.list_companies()

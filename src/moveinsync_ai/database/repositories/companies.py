"""SQLAlchemy company-directory implementation."""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company


class CompanyDirectory(Protocol):
    def list_companies(self) -> list[Company]: ...


class SqlAlchemyCompanyDirectory:
    def __init__(self, session: Session):
        self._session = session

    def list_companies(self) -> list[Company]:
        return list(self._session.scalars(select(Company).order_by(Company.name)))

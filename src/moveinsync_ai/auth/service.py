"""SQLAlchemy implementation of authentication lookups."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.models import User
from .contracts import PasswordHasher


class SqlAlchemyAuthenticationService:
    """Authenticate persisted users through an injected password hasher."""

    def __init__(self, session: Session, password_hasher: PasswordHasher):
        self._session = session
        self._password_hasher = password_hasher

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self._session.scalar(select(User).where(User.email == email.lower()))
        return user if user and self._password_hasher.verify(password, user.password_hash) else None

    def get_user(self, user_id: int) -> Optional[User]:
        return self._session.get(User, user_id)

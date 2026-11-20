"""Small contracts that keep authentication implementations replaceable."""

from typing import Any, Dict, Optional, Protocol

from ..database.models import User


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class AccessTokenCodec(Protocol):
    def issue(self, user_id: int, user_type: str, company_id: Optional[int]) -> str: ...

    def decode(self, token: str) -> Optional[Dict[str, Any]]: ...


class AuthenticationService(Protocol):
    def authenticate(self, email: str, password: str) -> Optional[User]: ...

    def get_user(self, user_id: int) -> Optional[User]: ...

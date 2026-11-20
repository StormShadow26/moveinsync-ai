"""Small contracts that keep authentication implementations replaceable."""

from typing import Any, Dict, Optional, Protocol

from ..database.models import User


class OtpGenerator(Protocol):
    def generate(self) -> str: ...


class OtpHasher(Protocol):
    def hash(self, code: str) -> str: ...

    def verify(self, code: str, code_hash: str) -> bool: ...


class OtpDelivery(Protocol):
    def send(self, recipient: str, code: str) -> None: ...


class AccessTokenCodec(Protocol):
    def issue(self, user_id: int, user_type: str, company_id: Optional[int], company_ids: list[int]) -> str: ...

    def decode(self, token: str) -> Optional[Dict[str, Any]]: ...


class AuthenticationService(Protocol):
    def request_otp(self, email: str) -> bool: ...

    def verify_otp(self, email: str, code: str) -> Optional[User]: ...

    def get_user(self, user_id: int) -> Optional[User]: ...
    def company_ids(self, user: User) -> list[int]: ...

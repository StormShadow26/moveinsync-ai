"""SQLAlchemy implementation of provisioned-email authentication."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..database.models import LoginOtp, User, UserType
from .contracts import OtpDelivery, OtpGenerator, OtpHasher


class SqlAlchemyAuthenticationService:
    """Issue and verify OTPs only for provisioned client travel admins."""

    def __init__(
        self,
        session: Session,
        settings: Settings,
        generator: OtpGenerator,
        hasher: OtpHasher,
        delivery: OtpDelivery,
    ):
        self._session = session
        self._settings = settings
        self._generator = generator
        self._hasher = hasher
        self._delivery = delivery

    def request_otp(self, email: str) -> bool:
        user = self._session.scalar(select(User).where(User.email == email.lower()))
        if user is None or user.user_type != UserType.CLIENT_TRANSPORT_ADMIN:
            return False
        code = self._generator.generate()
        self._session.execute(delete(LoginOtp).where(LoginOtp.user_id == user.id, LoginOtp.used_at.is_(None)))
        self._session.add(
            LoginOtp(
                user_id=user.id,
                code_hash=self._hasher.hash(code),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=self._settings.otp_expire_minutes),
            )
        )
        self._session.commit()
        self._delivery.send(user.email, code)
        return True

    def verify_otp(self, email: str, code: str) -> Optional[User]:
        user = self._session.scalar(select(User).where(User.email == email.lower()))
        if user is None or user.user_type != UserType.CLIENT_TRANSPORT_ADMIN:
            return None
        otp = self._session.scalar(
            select(LoginOtp)
            .where(LoginOtp.user_id == user.id, LoginOtp.used_at.is_(None))
            .order_by(LoginOtp.created_at.desc())
        )
        if otp is None:
            return None
        now = datetime.now(timezone.utc)
        expires_at = otp.expires_at.replace(tzinfo=timezone.utc) if otp.expires_at.tzinfo is None else otp.expires_at
        if expires_at <= now or otp.failed_attempts >= 5:
            return None
        if not self._hasher.verify(code, otp.code_hash):
            otp.failed_attempts += 1
            self._session.commit()
            return None
        otp.used_at = now
        self._session.commit()
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        return self._session.get(User, user_id)

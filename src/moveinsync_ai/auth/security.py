"""Password hashing and JWT helpers."""

from datetime import datetime, timedelta, timezone
import hmac
import hashlib
import logging
import secrets
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

import jwt

from ..config import Settings
from .contracts import AccessTokenCodec, OtpDelivery, OtpGenerator, OtpHasher

logger = logging.getLogger(__name__)


class SecureOtpGenerator:
    """Generate an email-friendly six-digit verification code."""

    def generate(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"


class HmacOtpHasher:
    """Protect OTP values at rest with a server-held secret."""

    def __init__(self, secret: str):
        self._secret = secret.encode("utf-8")

    def hash(self, code: str) -> str:
        return hmac.new(self._secret, code.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, code: str, code_hash: str) -> bool:
        return hmac.compare_digest(self.hash(code), code_hash)


class SmtpOtpDelivery:
    """Deliver OTPs through the configured SMTP server."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def send(self, recipient: str, code: str) -> None:
        message = EmailMessage()
        message["Subject"] = "Your MoveInSync verification code"
        message["From"] = self._settings.smtp_sender_email
        message["To"] = recipient
        message.set_content(f"Your MoveInSync verification code is {code}. It expires in {self._settings.otp_expire_minutes} minutes.")
        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=10) as client:
            client.starttls()
            if self._settings.smtp_username and self._settings.smtp_password:
                client.login(self._settings.smtp_username, self._settings.smtp_password)
            client.send_message(message)


class LoggingOtpDelivery:
    """Development-only delivery that makes local OTP testing possible."""

    def send(self, recipient: str, code: str) -> None:
        logger.warning("Development OTP for %s: %s", recipient, code)


def otp_delivery(settings: Settings) -> OtpDelivery:
    """Select SMTP in configured environments, otherwise local log delivery."""
    return SmtpOtpDelivery(settings) if settings.smtp_host else LoggingOtpDelivery()


class JwtAccessTokenCodec:
    """AccessTokenCodec implementation that signs short-lived JWTs."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def issue(self, user_id: int, user_type: str, company_id: Optional[int], company_ids: list[int]) -> str:
        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "user_type": user_type,
            "access_scope": "all_companies" if company_id is None else "single_company",
            "company_id": company_id,
            "company_ids": company_ids,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self._settings.access_token_expire_minutes),
        }
        return jwt.encode(payload, self._settings.jwt_secret_key, algorithm=self._settings.jwt_algorithm)

    def decode(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm])
        except jwt.PyJWTError:
            return None


otp_generator: OtpGenerator = SecureOtpGenerator()

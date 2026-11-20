"""Password hashing and JWT helpers."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional

import jwt

from ..config import Settings
from .contracts import AccessTokenCodec, PasswordHasher

SCRYPT_COST = 2**14
SCRYPT_BLOCK_SIZE = 8
SCRYPT_PARALLELISM = 1
SCRYPT_KEY_LENGTH = 32


class ScryptPasswordHasher:
    """PasswordHasher implementation using Python's scrypt primitive."""

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        derived_key = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=SCRYPT_COST, r=SCRYPT_BLOCK_SIZE, p=SCRYPT_PARALLELISM, dklen=SCRYPT_KEY_LENGTH
        )
        return "scrypt${}${}${}${}${}".format(
            SCRYPT_COST, SCRYPT_BLOCK_SIZE, SCRYPT_PARALLELISM, base64.b64encode(salt).decode("ascii"), base64.b64encode(derived_key).decode("ascii")
        )

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, cost, block_size, parallelism, encoded_salt, encoded_key = password_hash.split("$")
            if algorithm != "scrypt":
                return False
            expected_key = base64.b64decode(encoded_key)
            derived_key = hashlib.scrypt(
                password.encode("utf-8"), salt=base64.b64decode(encoded_salt), n=int(cost), r=int(block_size), p=int(parallelism), dklen=len(expected_key)
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(derived_key, expected_key)


class JwtAccessTokenCodec:
    """AccessTokenCodec implementation that signs short-lived JWTs."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def issue(self, user_id: int, user_type: str, company_id: Optional[int]) -> str:
        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "user_type": user_type,
            "access_scope": "all_companies" if company_id is None else "single_company",
            "company_id": company_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self._settings.access_token_expire_minutes),
        }
        return jwt.encode(payload, self._settings.jwt_secret_key, algorithm=self._settings.jwt_algorithm)

    def decode(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, self._settings.jwt_secret_key, algorithms=[self._settings.jwt_algorithm])
        except jwt.PyJWTError:
            return None


password_hasher: PasswordHasher = ScryptPasswordHasher()

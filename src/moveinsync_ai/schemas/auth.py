"""Authentication request and response schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr

from ..database.models import UserType


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerification(OtpRequest):
    code: str


class OtpRequestResponse(BaseModel):
    message: str = "If the email is registered, a verification code has been sent."


class CurrentUser(BaseModel):
    user_id: int
    email: EmailStr
    user_type: UserType
    access_scope: str
    company_id: Optional[int]

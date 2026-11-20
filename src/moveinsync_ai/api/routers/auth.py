"""HTTP endpoints for issuing and validating access tokens."""

from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ...auth.contracts import AccessTokenCodec, AuthenticationService, OtpDelivery
from ...auth.security import HmacOtpHasher, JwtAccessTokenCodec, otp_delivery, otp_generator
from ...auth.service import SqlAlchemyAuthenticationService
from ...database.models import UserType
from ...schemas.auth import CurrentUser, OtpRequest, OtpRequestResponse, OtpVerification, TokenResponse
from ..dependencies import SessionDependency, SettingsDependency

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/otp/verify")


def get_otp_delivery(settings: SettingsDependency) -> OtpDelivery:
    return otp_delivery(settings)


OtpDeliveryDependency = Annotated[OtpDelivery, Depends(get_otp_delivery)]


def authentication_service(
    session: SessionDependency, settings: SettingsDependency, delivery: OtpDeliveryDependency
) -> AuthenticationService:
    return SqlAlchemyAuthenticationService(
        session, settings, otp_generator, HmacOtpHasher(settings.otp_secret_key), delivery
    )


def access_token_codec(settings: SettingsDependency) -> AccessTokenCodec:
    return JwtAccessTokenCodec(settings)


AuthenticationServiceDependency = Annotated[AuthenticationService, Depends(authentication_service)]
AccessTokenCodecDependency = Annotated[AccessTokenCodec, Depends(access_token_codec)]


def token_claims(token: Annotated[str, Depends(oauth2_scheme)], codec: AccessTokenCodecDependency) -> Dict:
    """Decode a token and reject invalid or expired credentials."""
    claims = codec.decode(token)
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")

    user_type = claims.get("user_type")
    company_id = claims.get("company_id")
    access_scope = claims.get("access_scope")
    company_ids = claims.get("company_ids")
    if not isinstance(claims.get("sub"), str) or user_type not in {
        UserType.INTERNAL_OPS_MANAGER.value,
        UserType.CLIENT_TRANSPORT_ADMIN.value,
    }:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token claims")
    if not isinstance(company_ids, list) or not company_ids or any(type(value) is not int or value <= 0 for value in company_ids):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token company list")
    if user_type == UserType.INTERNAL_OPS_MANAGER.value and (access_scope != "all_companies" or company_id is not None):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token scope")
    if user_type == UserType.CLIENT_TRANSPORT_ADMIN.value and company_ids != [company_id]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token company list")
    if user_type == UserType.CLIENT_TRANSPORT_ADMIN.value and (
        access_scope != "single_company" or not isinstance(company_id, int)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token scope")
    return claims


@router.post("/otp/request", response_model=OtpRequestResponse, status_code=status.HTTP_202_ACCEPTED)
def request_otp(
    request: OtpRequest,
    authentication: AuthenticationServiceDependency,
) -> OtpRequestResponse:
    """Send a verification code only to a provisioned application user."""
    try:
        authentication.request_otp(request.email)
    except OSError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Verification email is unavailable") from error
    return OtpRequestResponse()


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(
    verification: OtpVerification,
    authentication: AuthenticationServiceDependency,
    codec: AccessTokenCodecDependency,
) -> TokenResponse:
    """Exchange a valid, single-use verification code for a scoped JWT."""
    user = authentication.verify_otp(verification.email, verification.code)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code",
            headers={"WWW-Authenticate": "Bearer"},
        )
    is_internal_manager = user.user_type == UserType.INTERNAL_OPS_MANAGER
    if (is_internal_manager and user.company_id is not None) or (not is_internal_manager and user.company_id is None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has an invalid company scope")
    company_ids = authentication.company_ids(user)
    if not company_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no assigned companies")
    return TokenResponse(
        access_token=codec.issue(
            user.id,
            user.user_type.value,
            user.company_id,
            company_ids,
        )
    )


@router.get("/me", response_model=CurrentUser)
def read_current_user(
    claims: Annotated[dict, Depends(token_claims)], authentication: AuthenticationServiceDependency
) -> CurrentUser:
    """Return the authenticated identity after checking it still exists."""
    user = authentication.get_user(int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return CurrentUser(
        user_id=user.id,
        email=user.email,
        user_type=claims["user_type"],
        access_scope=claims["access_scope"],
        company_id=claims["company_id"],
    )

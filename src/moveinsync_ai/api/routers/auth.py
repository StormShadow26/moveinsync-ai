"""HTTP endpoints for issuing and validating access tokens."""

from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from ...auth.contracts import AccessTokenCodec, AuthenticationService
from ...auth.security import JwtAccessTokenCodec, password_hasher
from ...auth.service import SqlAlchemyAuthenticationService
from ...database.models import UserType
from ...schemas.auth import CurrentUser, TokenResponse
from ..dependencies import SessionDependency, SettingsDependency

router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def authentication_service(session: SessionDependency) -> AuthenticationService:
    return SqlAlchemyAuthenticationService(session, password_hasher)


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
    if not isinstance(claims.get("sub"), str) or user_type not in {
        UserType.INTERNAL_OPS_MANAGER.value,
        UserType.CLIENT_TRANSPORT_ADMIN.value,
    }:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token claims")
    if user_type == UserType.INTERNAL_OPS_MANAGER.value and (access_scope != "all_companies" or company_id is not None):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token scope")
    if user_type == UserType.CLIENT_TRANSPORT_ADMIN.value and (
        access_scope != "single_company" or not isinstance(company_id, int)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token scope")
    return claims


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    authentication: AuthenticationServiceDependency,
    codec: AccessTokenCodecDependency,
) -> TokenResponse:
    """Exchange an email and password for a short-lived scoped JWT."""
    user = authentication.authenticate(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    is_internal_manager = user.user_type == UserType.INTERNAL_OPS_MANAGER
    if (is_internal_manager and user.company_id is not None) or (
        not is_internal_manager and user.company_id is None
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has an invalid company scope")
    return TokenResponse(
        access_token=codec.issue(
            user.id,
            user.user_type.value,
            user.company_id,
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

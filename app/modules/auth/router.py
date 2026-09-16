"""
app/modules/auth/router.py
==========================
HTTP route handlers for authentication endpoints.

ENDPOINTS:
  POST  /api/v1/auth/login           → login and get JWT
  GET   /api/v1/auth/me              → get current user info
  POST  /api/v1/auth/logout          → logout (client-side token discard)
  POST  /api/v1/auth/change-password → change own password

HOW ROUTERS WORK:
- We create an APIRouter (like a mini-app) and register routes on it.
- In main.py, we include this router with the /api/v1/auth prefix.
- Routes here handle HTTP: parsing requests, calling service functions,
  returning responses.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.modules.auth import service
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    ChangePasswordRequest,
    LogoutResponse,
)
from app.schemas.user import UserResponse


# Create the router for auth endpoints
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],  # Groups these endpoints in Swagger docs
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description=(
        "Authenticate with your email and password. "
        "Returns a JWT bearer token. Include this token in subsequent requests "
        "as: `Authorization: Bearer <token>`"
    ),
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/v1/auth/login"""
    return service.authenticate_user(db=db, request=request)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user",
    description="Returns the profile of the currently authenticated user based on the JWT token.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """GET /api/v1/auth/me — requires Authorization: Bearer <token>"""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout (client-side token discard)",
    description=(
        "Informs the client to discard the JWT token. "
        "Since JWTs are stateless, the server cannot truly invalidate a token until it expires. "
        "The client must remove the token from storage. "
        "Server-side token revocation (blocklist) will be added in a future update."
    ),
)
def logout(
    current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    """POST /api/v1/auth/logout — requires valid JWT"""
    return LogoutResponse()


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change own password",
    description=(
        "Change the authenticated user's password. "
        "Must provide the correct current password for verification. "
        "New password must be at least 8 characters."
    ),
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """POST /api/v1/auth/change-password — requires Authorization: Bearer <token>"""
    service.change_password(
        db=db,
        current_user=current_user,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return {"message": "Password changed successfully."}

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import Permission, RoleName, has_permission
from app.core.security import decode_token
from app.models import RevokedToken, User

bearer = HTTPBearer(auto_error=False)

ROLE_ADMIN = RoleName.ADMIN.value
ROLE_ENGINEER = RoleName.DRILLING_ENGINEER.value
ROLE_VIEWER = RoleName.VIEWER.value


def _unauthorized(message: str = "Authentication is required.") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"message": message, "error_code": "UNAUTHORIZED"},
    )


def _forbidden(message: str = "You do not have permission to perform this action.") -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"message": message, "error_code": "FORBIDDEN"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _unauthorized("The session token is invalid or expired.") from exc
    jti = payload.get("jti")
    if jti and db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        raise _unauthorized("This session has been logged out.")
    try:
        user_id = UUID(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise _unauthorized() from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("The account is inactive or does not exist.")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        role_name = user.role.name if user.role else ""
        if role_name not in roles:
            raise _forbidden()
        return user

    return checker


def require_permissions(*permissions: Permission | str):
    """Enforce granular RBAC permissions on endpoints."""
    def checker(user: User = Depends(get_current_user)) -> User:
        role_name = user.role.name if user.role else ""
        for perm in permissions:
            if not has_permission(role_name, perm):
                raise _forbidden(f"Action requires '{perm.value if isinstance(perm, Permission) else perm}' permission.")
        return user

    return checker


def user_from_token_string(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise _unauthorized("The session token is invalid or expired.") from exc
    jti = payload.get("jti")
    if jti and db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        raise _unauthorized("This session has been logged out.")
    user = db.get(User, UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


def request_meta(request: Request) -> Request:
    return request

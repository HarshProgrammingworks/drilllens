from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.dependencies import ROLE_ADMIN, get_current_user, require_roles
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models import RevokedToken, User
from app.schemas.domain import (
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.services.auth_service import (
    check_password,
    consume_reset,
    create_user,
    find_login_user,
    issue_reset,
    public_user,
)
from app.utils.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = find_login_user(db, body.username)
    if user is None or not check_password(user, body.password):
        write_audit(db, user_id=None, action="LOGIN_FAILED", resource="auth", request=request, metadata={"username": body.username})
        db.commit()
        raise HTTPException(status_code=401, detail={"message": "Invalid username or password.", "error_code": "INVALID_CREDENTIALS"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"message": "This account is deactivated.", "error_code": "INACTIVE_USER"})
    token, jti, exp = create_access_token(user_id=str(user.id), role=user.role.name, remember=body.remember)
    user.last_login = datetime.now(timezone.utc)
    write_audit(db, user_id=user.id, action="LOGIN", resource="auth", resource_id=str(user.id), request=request)
    db.commit()
    return {
        "success": True,
        "data": {"access_token": token, "token_type": "bearer", "expires_at": exp.isoformat(), "user": public_user(user)},
        "message": None,
    }


@router.post("/register")
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if find_login_user(db, body.username) or find_login_user(db, body.email):
        raise HTTPException(status_code=409, detail={"message": "Username or email is already registered.", "error_code": "CONFLICT"})
    user = create_user(
        db,
        username=body.username,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role_name="VIEWER",
    )
    write_audit(db, user_id=user.id, action="REGISTER", resource="user", resource_id=str(user.id), request=request)
    db.commit()
    db.refresh(user)
    return {"success": True, "data": public_user(user), "message": "Account created with the Viewer role."}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"success": True, "data": public_user(user), "message": None}


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.core.security import decode_token

    auth = request.headers.get("authorization", "")
    token = auth.split(" ", 1)[1] if " " in auth else ""
    payload = decode_token(token)
    db.add(
        RevokedToken(
            jti=payload["jti"],
            user_id=user.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    )
    write_audit(db, user_id=user.id, action="LOGOUT", resource="auth", resource_id=str(user.id), request=request)
    db.commit()
    return {"success": True, "data": {"logged_out": True}, "message": "Session ended."}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    user = db.query(User).filter(User.email.ilike(body.email.strip())).one_or_none()
    token = None
    if user and user.is_active:
        token = issue_reset(db, user)
        write_audit(
            db,
            user_id=user.id,
            action="PASSWORD_RESET_REQUEST",
            resource="auth",
            resource_id=str(user.id),
            request=request,
        )
        db.commit()
    data = {"issued": True}
    if settings.is_development and settings.return_reset_token and token:
        data["development_reset_token"] = token
        data["notice"] = "DEVELOPMENT ONLY. Disable RETURN_RESET_TOKEN in production and deliver this token by email."
    return {
        "success": True,
        "data": data,
        "message": "If the account exists, a password reset token has been issued.",
    }


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    user = consume_reset(db, body.token, body.password)
    if user is None:
        raise HTTPException(status_code=400, detail={"message": "The reset token is invalid or expired.", "error_code": "INVALID_TOKEN"})
    write_audit(db, user_id=user.id, action="PASSWORD_RESET", resource="auth", resource_id=str(user.id), request=request)
    db.commit()
    return {"success": True, "data": {"reset": True}, "message": "Password updated."}


@router.post("/change-password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_password(user, body.current_password):
        raise HTTPException(status_code=400, detail={"message": "Current password is incorrect.", "error_code": "INVALID_CREDENTIALS"})
    from app.core.security import hash_password

    user.password_hash = hash_password(body.new_password)
    write_audit(db, user_id=user.id, action="PASSWORD_CHANGE", resource="user", resource_id=str(user.id), request=request)
    db.commit()
    return {"success": True, "data": {"changed": True}, "message": "Password updated."}


@router.get("/users")
def list_users(user: User = Depends(require_roles(ROLE_ADMIN)), db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.username).all()
    return {"success": True, "data": [public_user(row) for row in rows], "message": None}

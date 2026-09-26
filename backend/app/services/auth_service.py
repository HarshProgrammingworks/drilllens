import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import PasswordResetToken, Role, User


from app.core.rbac import get_role_permissions


def role_by_name(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).one_or_none()


def public_user(user: User) -> dict:
    role_name = user.role.name if user.role else None
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": role_name,
        "permissions": get_role_permissions(role_name),
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def find_login_user(db: Session, username_or_email: str) -> User | None:
    key = username_or_email.strip().lower()
    return (
        db.query(User)
        .filter((User.username.ilike(key)) | (User.email.ilike(key)))
        .one_or_none()
    )


def create_user(db: Session, *, username: str, email: str, password: str, full_name: str, role_name: str) -> User:
    role = role_by_name(db, role_name)
    if role is None:
        raise ValueError("Unknown role")
    user = User(
        username=username.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def issue_reset(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
    )
    return raw


def consume_reset(db: Session, token: str, new_password: str) -> User | None:
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == digest, PasswordResetToken.used_at.is_(None))
        .one_or_none()
    )
    if row is None or row.expires_at < datetime.now(timezone.utc):
        return None
    user = db.get(User, row.user_id)
    if user is None:
        return None
    user.password_hash = hash_password(new_password)
    row.used_at = datetime.now(timezone.utc)
    return user


def check_password(user: User, password: str) -> bool:
    return verify_password(password, user.password_hash)

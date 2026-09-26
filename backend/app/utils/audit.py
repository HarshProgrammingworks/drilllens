from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog

SENSITIVE_KEYS = {"password", "password_hash", "token", "secret", "authorization"}


def scrub(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    clean = {}
    for key, value in metadata.items():
        if key.lower() in SENSITIVE_KEYS:
            continue
        clean[key] = value
    return clean


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def write_audit(
    db: Session,
    *,
    user_id: UUID | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    request: Request | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=client_ip(request),
            metadata_json=scrub(metadata),
        )
    )

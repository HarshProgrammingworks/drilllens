from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.ml.inference.engine import RiskResult
from app.models import Alert, Notification, Well

OPEN_STATUSES = ("OPEN", "ACKNOWLEDGED", "REVIEWED", "ESCALATED")

SEVERITY_RANK = {"INFO": 1, "WARNING": 2, "HIGH_RISK": 3, "CRITICAL": 4}


def severity_for(level: str) -> str:
    return {
        "LOW": "INFO",
        "MODERATE": "WARNING",
        "HIGH": "HIGH_RISK",
        "CRITICAL": "CRITICAL",
    }.get(level, "INFO")


def upsert_alert(
    db: Session,
    *,
    well: Well,
    result: RiskResult,
    alert_min_score: float,
    cooldown_minutes: int,
) -> Alert | None:
    now = datetime.now(timezone.utc)
    if result.score < alert_min_score:
        active = (
            db.query(Alert)
            .filter(
                Alert.well_id == well.id,
                Alert.risk_category == result.category,
                Alert.status.in_(OPEN_STATUSES),
            )
            .all()
        )
        for alert in active:
            alert.status = "RESOLVED"
            alert.updated_at = now
            alert.score = result.score
        return None

    severity = severity_for(result.level)
    dedupe_key = f"{well.id}:{result.category}"
    existing = (
        db.query(Alert)
        .filter(Alert.dedupe_key == dedupe_key, Alert.status.in_(OPEN_STATUSES))
        .order_by(Alert.created_at.desc())
        .first()
    )
    description = " ".join(result.reasons)
    if existing:
        previous = existing.severity
        existing.score = result.score
        existing.description = description
        existing.updated_at = now
        existing.trigger_source = "RULE-BASED"
        if SEVERITY_RANK[severity] > SEVERITY_RANK.get(previous, 0):
            existing.severity = severity
            existing.escalated_at = now
            existing.status = "ESCALATED"
            db.add(
                Notification(
                    type="RISK_ESCALATION",
                    title=f"{result.label} escalated on {well.well_code}",
                    body=description,
                    link=f"/alerts/{existing.id}",
                )
            )
        return existing

    if existing is None:
        recent = (
            db.query(Alert)
            .filter(Alert.dedupe_key == dedupe_key, Alert.cooldown_until.isnot(None))
            .order_by(Alert.created_at.desc())
            .first()
        )
        if recent and recent.cooldown_until and recent.cooldown_until > now and recent.status != "FALSE_POSITIVE":
            recent.score = result.score
            recent.description = description
            recent.updated_at = now
            return recent

    alert = Alert(
        well_id=well.id,
        risk_category=result.category,
        severity=severity,
        title=f"{result.label} indicator is {result.level} on {well.well_code}",
        description=description,
        score=result.score,
        trigger_source="RULE-BASED",
        status="OPEN",
        dedupe_key=dedupe_key,
        cooldown_until=now + timedelta(minutes=cooldown_minutes),
    )
    db.add(alert)
    db.flush()
    db.add(
        Notification(
            type="ALERT",
            title=alert.title,
            body=description[:500],
            link=f"/alerts/{alert.id}",
        )
    )
    return alert


def apply_action(db: Session, alert: Alert, action: str, user_id: UUID, note: str | None) -> Alert:
    now = datetime.now(timezone.utc)
    alert.updated_at = now
    if note:
        alert.note = note
    if action == "acknowledge":
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = now
        alert.acknowledged_by = user_id
    elif action == "review":
        alert.status = "REVIEWED"
    elif action == "escalate":
        alert.status = "ESCALATED"
        alert.escalated_at = now
    elif action == "false_positive":
        alert.status = "FALSE_POSITIVE"
        alert.acknowledged_at = now
        alert.acknowledged_by = user_id
    elif action == "note":
        pass
    else:
        raise ValueError("Unsupported alert action")
    return alert

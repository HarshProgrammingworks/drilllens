import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")
TSVECTOR_TYPE = Text().with_variant(TSVECTOR, "postgresql")
UUID_TYPE = Uuid(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[Role] = relationship("Role")


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Formation(Base):
    __tablename__ = "formations"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Well(Base):
    __tablename__ = "wells"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    well_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRILLING")
    current_depth: Mapped[float | None] = mapped_column(Float)
    current_formation: Mapped[str | None] = mapped_column(String(200))
    current_operation: Mapped[str | None] = mapped_column(String(200))
    spud_date: Mapped[datetime | None] = mapped_column(Date)
    completion_date: Mapped[datetime | None] = mapped_column(Date)
    well_type: Mapped[str] = mapped_column(String(80), default="DEVELOPMENT")
    trajectory_type: Mapped[str] = mapped_column(String(80), default="VERTICAL")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="DEMO")
    simulate_sensors: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demo_scenario: Mapped[str] = mapped_column(String(40), default="normal")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    coordinate: Mapped["WellCoordinate | None"] = relationship(back_populates="well", uselist=False)
    trajectory: Mapped[list["WellTrajectory"]] = relationship(back_populates="well")


class WellCoordinate(Base):
    __tablename__ = "well_coordinates"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), unique=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    well: Mapped[Well] = relationship(back_populates="coordinate")


class WellTrajectory(Base):
    __tablename__ = "well_trajectories"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), index=True)
    station_index: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_depth: Mapped[float] = mapped_column(Float, nullable=False)
    tvd: Mapped[float] = mapped_column(Float, nullable=False)
    inclination: Mapped[float] = mapped_column(Float, default=0)
    azimuth: Mapped[float] = mapped_column(Float, default=0)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    well: Mapped[Well] = relationship(back_populates="trajectory")

    __table_args__ = (UniqueConstraint("well_id", "station_index", name="uq_traj_station"),)


class WellFormation(Base):
    __tablename__ = "well_formations"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), index=True)
    formation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("formations.id"), index=True)
    depth_top: Mapped[float] = mapped_column(Float, nullable=False)
    depth_bottom: Mapped[float] = mapped_column(Float, nullable=False)

    formation: Mapped[Formation] = relationship()


class DrillingParameter(Base):
    __tablename__ = "drilling_parameters"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    depth: Mapped[float | None] = mapped_column(Float)
    rop: Mapped[float | None] = mapped_column(Float)
    wob: Mapped[float | None] = mapped_column(Float)
    rpm: Mapped[float | None] = mapped_column(Float)
    torque: Mapped[float | None] = mapped_column(Float)
    standpipe_pressure: Mapped[float | None] = mapped_column(Float)
    mud_flow: Mapped[float | None] = mapped_column(Float)
    mud_weight: Mapped[float | None] = mapped_column(Float)
    pump_pressure: Mapped[float | None] = mapped_column(Float)
    hook_load: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(40), default="SIMULATED")
    provenance: Mapped[str] = mapped_column(String(40), default="SIMULATED")


class HistoricalReport(Base):
    __tablename__ = "historical_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wells.id"), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False, default="WCR")
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="UPLOADED", index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    report_date: Mapped[datetime | None] = mapped_column(Date)
    source_type: Mapped[str] = mapped_column(String(40), default="ENGINEER_ENTERED")
    error_message: Mapped[str | None] = mapped_column(Text)
    search_vector = mapped_column(TSVECTOR_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    well: Mapped[Well | None] = relationship()
    pages: Mapped[list["ReportPage"]] = relationship(back_populates="report")


class ReportPage(Base):
    __tablename__ = "report_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("historical_reports.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, default="")
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    search_vector = mapped_column(TSVECTOR_TYPE)

    report: Mapped[HistoricalReport] = relationship(back_populates="pages")

    __table_args__ = (UniqueConstraint("report_id", "page_number", name="uq_report_page"),)


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("historical_reports.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_pages.id", ondelete="SET NULL"))
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_ocr_text: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float | None] = mapped_column(Float)
    processing_time: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NlpEntity(Base):
    __tablename__ = "nlp_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("historical_reports.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_pages.id", ondelete="SET NULL"))
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(300))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    extractor: Mapped[str] = mapped_column(String(40), default="RULE")
    start_char: Mapped[int | None] = mapped_column(Integer)
    end_char: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DrillingEvent(Base):
    __tablename__ = "drilling_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wells.id"), index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("historical_reports.id"))
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_pages.id"))
    depth_start: Mapped[float | None] = mapped_column(Float)
    depth_end: Mapped[float | None] = mapped_column(Float)
    formation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("formations.id"))
    formation_name: Mapped[str | None] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    risk_category: Mapped[str | None] = mapped_column(String(40), index=True)
    event_date: Mapped[datetime | None] = mapped_column(Date)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source_type: Mapped[str] = mapped_column(String(40), default="NLP_EXTRACTED")
    search_vector = mapped_column(TSVECTOR_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    well: Mapped[Well | None] = relationship()
    report: Mapped[HistoricalReport | None] = relationship()


class RiskThreshold(Base):
    __tablename__ = "risk_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    low_max: Mapped[float] = mapped_column(Float, default=29)
    moderate_max: Mapped[float] = mapped_column(Float, default=59)
    high_max: Mapped[float] = mapped_column(Float, default=79)
    alert_min_score: Mapped[float] = mapped_column(Float, default=60)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    torque_rise_pct: Mapped[float] = mapped_column(Float, default=15)
    pressure_rise_pct: Mapped[float] = mapped_column(Float, default=10)
    flow_change_pct: Mapped[float] = mapped_column(Float, default=12)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id"), index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasons: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON_TYPE, default=list)
    inputs: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    features: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    engine: Mapped[str] = mapped_column(String(40), default="rule_based")
    engine_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    model_version: Mapped[str | None] = mapped_column(String(40))
    dataset_version: Mapped[str | None] = mapped_column(String(40))
    depth: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id"), index=True)
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("risk_predictions.id"))
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id"), index=True)
    risk_category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(40), default="RULE-BASED")
    status: Mapped[str] = mapped_column(String(40), default="OPEN", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(120), index=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    well: Mapped[Well] = relationship()


class WellSimilarity(Base):
    __tablename__ = "well_similarity"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), index=True)
    other_well_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    geographic_score: Mapped[float] = mapped_column(Float, nullable=False)
    formation_score: Mapped[float] = mapped_column(Float, nullable=False)
    depth_score: Mapped[float] = mapped_column(Float, nullable=False)
    trajectory_score: Mapped[float] = mapped_column(Float, nullable=False)
    event_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    weights: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    distance_m: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("well_id", "other_well_id", name="uq_similarity_pair"),)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("historical_reports.id"))
    page_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report_pages.id"))
    well_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wells.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drilling_events.id"))
    depth_start: Mapped[float | None] = mapped_column(Float)
    depth_end: Mapped[float | None] = mapped_column(Float)
    formation: Mapped[str | None] = mapped_column(String(200))
    text_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_location: Mapped[str | None] = mapped_column(String(300))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    search_vector = mapped_column(TSVECTOR_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    report: Mapped[HistoricalReport | None] = relationship()
    well: Mapped[Well | None] = relationship()
    event: Mapped[DrillingEvent | None] = relationship()


class EngineeringReview(Base):
    __tablename__ = "engineering_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    well_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wells.id"))
    alert_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alerts.id"))
    engineer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    risk_category: Mapped[str | None] = mapped_column(String(40))
    snapshot: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    engineer: Mapped[User] = relationship()
    alert: Mapped[Alert | None] = relationship()
    well: Mapped[Well | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(80))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[User | None] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(300))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


Index("ix_parameters_well_time", DrillingParameter.well_id, DrillingParameter.recorded_at)
Index("ix_events_well_depth", DrillingEvent.well_id, DrillingEvent.depth_start)
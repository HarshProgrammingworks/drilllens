import os
import sys
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import log


class Base(DeclarativeBase):
    pass


settings = get_settings()
db_url = settings.database_url or ""
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

is_cloud = bool(os.environ.get("RENDER") or os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

# Check if using default localhost DB in cloud environment without remote PostgreSQL configured
if is_cloud and ("localhost" in db_url or "127.0.0.1" in db_url or not db_url):
    sqlite_path = Path("/tmp/drilllens.db") if Path("/tmp").exists() else Path("drilllens.db").resolve()
    db_url = f"sqlite:///{sqlite_path}"
    log.info("Cloud environment detected without remote database; using embedded storage: %s", db_url)

if ("neon.tech" in db_url or "supabase.co" in db_url) and "sslmode" not in db_url:
    delimiter = "&" if "?" in db_url else "?"
    db_url = f"{db_url}{delimiter}sslmode=require"

is_sqlite = db_url.startswith("sqlite")
connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10

engine_kwargs = {
    "pool_pre_ping": True,
    "future": True,
    "connect_args": connect_args,
}

if is_serverless:
    engine_kwargs["poolclass"] = NullPool

try:
    engine = create_engine(db_url, **engine_kwargs)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as conn_err:
    log.warning("Primary database connection (%s) failed (%s); falling back to embedded SQLite.", db_url, conn_err)
    sqlite_path = Path("/tmp/drilllens.db") if Path("/tmp").exists() else Path("drilllens.db").resolve()
    db_url = f"sqlite:///{sqlite_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False}, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

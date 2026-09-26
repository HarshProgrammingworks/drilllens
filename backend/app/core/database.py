from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

import os
from sqlalchemy.pool import NullPool

is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

# Neon/Supabase SSL adjustments
connect_args = {"connect_timeout": 10}
if ("neon.tech" in db_url or "supabase.co" in db_url) and "sslmode" not in db_url:
    delimiter = "&" if "?" in db_url else "?"
    db_url = f"{db_url}{delimiter}sslmode=require"

engine_kwargs = {
    "pool_pre_ping": True,
    "future": True,
    "connect_args": connect_args,
}

if is_serverless:
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

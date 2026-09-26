from contextlib import asynccontextmanager
import asyncio

from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import alerts, auth, evidence, monitoring, reports, reviews, risk, search, system, wells
from app.core.config import get_settings
from app.core.logging import log
from app.workers.sensor_worker import sensor_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    task = None
    if not is_serverless:
        task = asyncio.create_task(sensor_loop())
    log.info("DrillLens API started")
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="DrillLens",
    description="DrillLens — Powered by eRTMAC-NWIS. Engineering intelligence and decision support. DrillLens does not control drilling equipment.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-DrillLens-Platform"] = "eRTMAC-NWIS"
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "Request failed")
        code = detail.get("error_code", "HTTP_ERROR")
    else:
        message = str(detail)
        code = "HTTP_ERROR"
    return JSONResponse(status_code=exc.status_code, content={"success": False, "data": None, "message": message, "error_code": code})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": {"errors": exc.errors()},
            "message": "Request validation failed.",
            "error_code": "VALIDATION_ERROR",
        },
    )


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "message": "An unexpected error occurred.", "error_code": "INTERNAL_ERROR"},
    )


for module in (auth, wells, reports, search, risk, alerts, evidence, reviews, system):
    app.include_router(module.router, prefix="/api")
app.include_router(monitoring.router)


@app.get("/health")
def health_alias():
    return {"success": True, "data": {"status": "ok", "service": "drilllens"}, "message": None}


@app.get("/health/database")
def health_database_alias(db: Session = Depends(get_db)):
    from sqlalchemy import text

    db.execute(text("SELECT 1"))
    try:
        postgis = db.execute(text("SELECT PostGIS_Version()")).scalar()
    except Exception:
        postgis = "spatial_fallback (haversine)"
    return {"success": True, "data": {"database": "ok", "postgis": postgis}, "message": None}


@app.get("/")
def root():
    return {
        "success": True,
        "data": {"name": "DrillLens", "platform": "eRTMAC-NWIS", "docs": "/docs"},
        "message": None,
    }

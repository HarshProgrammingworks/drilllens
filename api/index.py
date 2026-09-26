import os
import sys
from pathlib import Path

# Resolve all potential project directories
api_dir = Path(__file__).resolve().parent
project_root = api_dir.parent
backend_dir = project_root / "backend"

candidates = [
    str(backend_dir),
    str(project_root),
    str(api_dir),
    "/var/task/backend",
    "/var/task",
    str(Path.cwd() / "backend"),
    str(Path.cwd()),
]

for c in candidates:
    if c not in sys.path:
        sys.path.insert(0, c)

try:
    from app.main import app
except Exception as err1:
    try:
        from backend.app.main import app
    except Exception as err2:
        import traceback
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI(title="DrillLens Fallback Diagnostic")

        @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
        def fallback_handler(full_path: str):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "DrillLens backend initialization error on serverless runtime.",
                    "error_1": str(err1),
                    "error_2": str(err2),
                    "traceback_1": traceback.format_exception(err1),
                    "traceback_2": traceback.format_exception(err2),
                    "sys_path": sys.path,
                    "cwd": str(Path.cwd()),
                },
            )

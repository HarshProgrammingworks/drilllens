import os
import sys
from pathlib import Path

# Resolve project root and backend directory
api_dir = Path(__file__).resolve().parent
project_root = api_dir.parent
backend_dir = project_root / "backend"

# Ensure all potential search paths are registered
for p in [backend_dir, project_root, api_dir, Path("/var/task/backend"), Path("/var/task")]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from app.main import app
except ImportError:
    try:
        from backend.app.main import app
    except ImportError:
        # Fallback for alternative directory structures
        sys.path.append(str(Path.cwd() / "backend"))
        sys.path.append(str(Path.cwd()))
        from app.main import app


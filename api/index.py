import sys
from pathlib import Path

# Ensure backend directory is in python search path
root = Path(__file__).resolve().parent
backend_dir = root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

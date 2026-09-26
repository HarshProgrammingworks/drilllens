from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.search_service import search_all

router = APIRouter(tags=["search"])


@router.get("/search")
def search(q: str = Query(..., min_length=1, max_length=200), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"success": True, "data": search_all(db, q), "message": None}

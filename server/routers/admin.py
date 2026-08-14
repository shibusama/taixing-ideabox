"""Admin routes: health check only."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health():
    return {"ok": True}
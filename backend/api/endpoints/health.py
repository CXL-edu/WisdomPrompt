"""Health check endpoint for readiness/liveness."""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    """Return 200 with status ok."""
    return {"status": "ok"}

"""API route definitions."""
from fastapi import APIRouter

from backend.api.endpoints import health, workflow

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])

"""WisdomPrompt backend: FastAPI app entry, CORS, lifespan, routes."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.logging_config import configure_logging, get_logger
from backend.api.routes import api_router

configure_logging(json_logs=False)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("startup", msg="WisdomPrompt backend starting")
    yield
    logger.info("shutdown", msg="WisdomPrompt backend shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    origins = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    app = FastAPI(
        title="WisdomPrompt API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app


app = create_app()

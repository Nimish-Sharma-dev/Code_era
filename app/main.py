"""
FinAI Platform — FastAPI Application Entry Point.

Lifecycle:
  startup  → init DB pool, Neo4j constraints, Redis, configure logging
  shutdown → gracefully close all connections

The app is built to serve thousands of concurrent users via async I/O,
connection pooling, and Redis caching. Deploy with Uvicorn + Nginx.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.neo4j.connection import create_constraints_and_indexes, close_driver
from app.db.postgres.connection import dispose_engine
from app.db.postgres.redis_client import close_redis
from app.middleware.exception_handler import register_exception_handlers

configure_logging()
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.

    startup:  Initialise all infrastructure connections.
    shutdown: Drain all connections gracefully.
    """
    logger.info(
        "FinAI Platform starting",
        version=settings.app_version,
        environment=settings.app_env,
    )

    # Initialise Neo4j constraints + indexes (idempotent)
    try:
        await create_constraints_and_indexes()
    except Exception as exc:
        logger.warning("Neo4j init skipped (not connected?)", error=str(exc))

    logger.info("All services initialised — accepting requests")
    yield

    # Graceful shutdown
    logger.info("Shutting down FinAI Platform")
    await dispose_engine()
    await close_redis()
    await close_driver()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Application factory — returns a configured FastAPI instance."""
    app = FastAPI(
        title="FinAI Platform API",
        description=(
            "AI-powered Financial Intelligence & Wellness Platform. "
            "Combines personal finance management, market intelligence, "
            "ML predictions, and conversational AI for holistic financial health."
        ),
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Request ID + timing middleware
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        import uuid
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        logger.info(
            "HTTP request",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response

    # ── Exception Handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Prometheus Metrics ────────────────────────────────────────────────────
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/ready", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Root endpoint ─────────────────────────────────────────────────────────
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs",
        }

    return app


app = create_app()

"""FastAPI application factory and ``tap-server`` console entry point.

Routers are mounted under ``/v1`` per the OpenAPI contract in
``platform/api/openapi.yaml``. OpenTelemetry instrumentation wraps the whole
app; every request carries tenant context resolved from the OIDC bearer token.
"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from tap_platform import __version__
from tap_platform.api import agents, approvals, audit, marketplace, policies, runs, workspaces
from tap_platform.config import Settings, get_settings

API_PREFIX = "/v1"


def _configure_telemetry(settings: Settings) -> None:
    """Install a tracer provider exporting OTLP spans for every API request."""
    resource = Resource.create(
        {"service.name": settings.service_name, "service.version": __version__}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
    )
    trace.set_tracer_provider(provider)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open shared clients (DB engine, Redis, NATS, Temporal) on startup.

    Contract: construct the async SQLAlchemy engine, Redis pool, event bus
    connection, and Temporal client; stash them on ``app.state``; close all of
    them on shutdown. Service-layer dependencies resolve them from app state.
    """
    # Deep wiring is intentionally deferred in the skeleton.
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the TAP control-plane FastAPI application.

    Args:
        settings: Optional explicit settings (tests); defaults to env-derived.

    Returns:
        Configured FastAPI app with all v1 routers and OTel middleware.
    """
    settings = settings or get_settings()
    _configure_telemetry(settings)

    app = FastAPI(
        title="Terraform Agent Platform API",
        version=__version__,
        lifespan=_lifespan,
        # RFC 7807: error bodies are application/problem+json (see api/common.py).
        responses={500: {"content": {"application/problem+json": {}}}},
    )
    app.state.settings = settings

    for router in (
        runs.router,
        workspaces.router,
        agents.router,
        marketplace.router,
        policies.router,
        approvals.router,
        audit.router,
    ):
        app.include_router(router, prefix=API_PREFIX)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    FastAPIInstrumentor.instrument_app(app)
    return app


def serve() -> None:
    """``tap-server`` console script: parse args and run uvicorn."""
    import uvicorn

    parser = argparse.ArgumentParser(prog="tap-server", description="TAP control plane")
    parser.add_argument("--config", help="Path to a YAML config file (e.g. platform/config/dev.yaml)")
    args = parser.parse_args()

    if args.config:
        import os

        import yaml  # type: ignore[import-untyped]

        with open(args.config, "r", encoding="utf-8") as fh:
            loaded: dict[str, object] = yaml.safe_load(fh) or {}
        # YAML keys are injected as TAP_* env vars so Settings picks them up.
        for key, value in loaded.items():
            os.environ.setdefault(f"TAP_{key.upper()}", str(value))
        get_settings.cache_clear()

    settings = get_settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    serve()

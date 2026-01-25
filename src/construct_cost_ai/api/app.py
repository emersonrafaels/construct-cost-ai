"""
FastAPI application factory and configuration.

Este módulo cria e configura a aplicação FastAPI para validação de orçamentos.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2026, Verificador Inteligente de Orçamentos de Obras, DataCraft"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

from contextlib import asynccontextmanager

from fastapi import FastAPI

from construct_cost_ai import __version__
from construct_cost_ai.api.routes import router
from construct_cost_ai.infra.config import get_settings
from construct_cost_ai.infra.logging import logger

# Obtendo a instância de configurações
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Construct Cost AI API")
    yield
    # Shutdown
    logger.info("Shutting down Construct Cost AI API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.get("api.title", "Construct Cost AI - Budget Validation Service"),
        version=settings.get("api.version", __version__),
        description=(
            "AI-powered construction cost validation service. "
            "Validates budget estimates using deterministic rules and AI analysis."
        ),
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(router)

    logger.info(f"FastAPI app created: {app.title} v{app.version}")

    return app


app = create_app()

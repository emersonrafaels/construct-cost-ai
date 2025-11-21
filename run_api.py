"""Run script for starting the FastAPI server."""

import uvicorn

from construct_cost_ai.infra.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "construct_cost_ai.api.app:app",
        host=settings.get("api_host", "0.0.0.0"),
        port=settings.get("api_port", 8000),
        reload=settings.get("api_reload", True),
    )

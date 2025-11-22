"""
Run script for starting the FastAPI server.

Script de inicialização do servidor FastAPI da aplicação.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

import uvicorn

from construct_cost_ai.infra.config import get_settings

# Get settings instance
settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "construct_cost_ai.api.app:app",
        host=settings.get("api.host", "0.0.0.0"),
        port=settings.get("api.port", 8000),
        reload=settings.get("api.reload", True),
    )

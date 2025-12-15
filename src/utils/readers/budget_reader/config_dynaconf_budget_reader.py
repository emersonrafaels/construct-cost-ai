"""
Configuração do Dynaconf para gerenciamento de settings.

Este módulo configura o Dynaconf para carregar configurações de settings.toml
e variáveis de ambiente.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

import sys
from functools import lru_cache
from pathlib import Path

from dynaconf import Dynaconf

# Adjust import path for data functions
sys.path.insert(0, str(Path(__file__).parents[0]))

# Get current directory
CONFIG_PATH = Path(__file__).parent.resolve()


@lru_cache()
def get_settings() -> Dynaconf:
    """Get settings singleton instance."""

    settings = Dynaconf(
        settings_files=[str(Path(CONFIG_PATH, "settings.toml"))],
        environments=True,  # Enable multiple environments like development, production
        load_dotenv=False,  # Enable loading of .env files
    )

    return settings


if __name__ == "__main__":
    # Test settings loading
    settings = get_settings()

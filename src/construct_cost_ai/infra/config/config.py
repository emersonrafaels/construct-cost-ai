"""
Configuration management using Dynaconf.

Gerenciamento de configurações da aplicação usando Dynaconf.
"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Copyright 2025, Construct Cost AI"
__credits__ = ["Emerson V. Rafael"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael"
__email__ = "emersonssmile@gmail.com"
__status__ = "Production"

from functools import lru_cache
from pathlib import Path

from dynaconf import Dynaconf

# Get project root directory
PROJECT_ROOT = Path(__file__).parents[4].resolve()


@lru_cache()
def get_settings() -> Dynaconf:
    """Get settings singleton instance.
    
    Returns:
        Dynaconf: Settings instance configured with project files
    """
    settings = Dynaconf(
        envvar_prefix="CONSTRUCT_COST",
        settings_files=[
            Path(PROJECT_ROOT, "settings.toml"),
            Path(PROJECT_ROOT, ".secrets.toml"),
        ],
        environments=True,  # Enable multiple environments like development, production
        load_dotenv=True,  # Enable loading of .env files
        env_switcher="ENV_FOR_DYNACONF",
        merge_enabled=True,
    )
    
    return settings

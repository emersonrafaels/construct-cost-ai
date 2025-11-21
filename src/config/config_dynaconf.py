import sys
from functools import lru_cache
from pathlib import Path

from dynaconf import Dynaconf

# Adjust import path for data functions
sys.path.insert(0, str(Path(__file__).parents[2]))

# Get current directory
CONFIG_PATH = Path(__file__).parent.resolve()


@lru_cache()
def get_settings() -> Dynaconf:
    """Get settings singleton instance."""

    settings = Dynaconf(
        settings_files=[
            Path(CONFIG_PATH, "settings.toml"),
            Path(CONFIG_PATH, ".secrets.toml"),
        ],
        environments=True,  # Enable multiple environments like development, production
        load_dotenv=True,  # Enable loading of .env files
    )

    return settings


"""
# Validate required settings
settings.validators.register(
    Validator("stackspot_client_secret", must_exist=True)
)
"""

"""Configuration management using Dynaconf."""

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="CONSTRUCT_COST",
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    load_dotenv=True,
    env_switcher="ENV_FOR_DYNACONF",
    merge_enabled=True,
)

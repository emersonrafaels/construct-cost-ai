"""Configuration management for StackSpot settings."""

import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

# Adjust import path for data functions
sys.path.insert(0, str(Path(__file__).parents[2]))

from src.config.config_dynaconf import get_settings
from src.utils.url_utils import build_url


@lru_cache()
def get_stackspot_config() -> dict:
    """Get StackSpot configuration from settings.

    Returns:
        dict: Dictionary with StackSpot configuration
    """
    # Retrieve settings instance
    settings = get_settings()

    # Build auth URL with full path
    auth_url = build_url(
        settings.get("stackspot.auth.base_url", "https://idm.stackspot.com"),
        settings.get("stackspot_realm"),
        settings.get("stackspot.auth.oidc_resource", "oidc"),
        settings.get("stackspot.auth.oauth_resource", "oauth"),
        settings.get("stackspot.auth.token_resource", "token"),
    )

    # Build inference URL
    inference_url = build_url(
        settings.get(
            "stackspot.inference.base_url", "https://genai-inference-app.stackspot.com"
        ),
        settings.get("stackspot.inference.api_version", "v1"),
        settings.get("stackspot.inference.agent_resource", "agent"),
        settings.get("stackspot.agent_id"),
    )
    
    # Get agent id
    agent_id = settings.get("stackspot.agent_id")
    if not agent_id:
        raise ValueError("Missing required setting: stackspot.agent_id")

    # Get credentials with validation
    realm = settings.get("stackspot_realm")
    if not realm:
        raise ValueError("Missing required setting: stackspot.realm")

    client_id = settings.get("stackspot_client_id")
    if not client_id:
        raise ValueError("Missing required setting: stackspot.client_id")

    client_secret = settings.get("stackspot_client_secret")
    if not client_secret:
        raise ValueError("Missing required setting: stackspot.client_secret")

    return {
        "agent_id": agent_id,
        "realm": realm,
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_url": auth_url,  # Ex: https://idm.stackspot.com/your_realm/oidc/oauth/token
        "inference_url": inference_url,  # Ex: https://genai-inference-app.stackspot.com/v1/agent/id/chat
    }

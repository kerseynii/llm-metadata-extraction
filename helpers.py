"""
Helper functions for the application.
"""
import os
from typing import Optional


def get_env_variable(key: str, default: Optional[str] = None) -> str:
    """
    Get an environment variable value.
    
    Args:
        key: The environment variable key
        default: Default value if the key is not found
        
    Returns:
        The environment variable value or default
        
    Raises:
        ValueError: If the key is not found and no default is provided
    """
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable '{key}' is not set")
    return value


def format_coordinates(lat: float, lon: float) -> str:
    """
    Format coordinates as a human-readable string.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Formatted coordinate string
    """
    return f"{lat:.6f}°N, {lon:.6f}°E"

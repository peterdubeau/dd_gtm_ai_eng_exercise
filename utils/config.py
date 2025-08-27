"""Configuration management for the application."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Application Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    # Output Configuration
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "out")
    INPUT_DIR: str = os.getenv("INPUT_DIR", "in")

    # Sender Configuration
    SENDER_NAME: str = os.getenv("SENDER_NAME", "DroneDeploy")
    SENDER_TITLE: str = os.getenv("SENDER_TITLE", "AI Outreach Agent")

    # Testing Configuration
    MAX_SPEAKERS: int = int(os.getenv("MAX_SPEAKERS", 10))

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        required_keys = ["OPENAI_API_KEY"]
        missing_keys = [key for key in required_keys if not getattr(cls, key)]

        if missing_keys:
            logger.error(
                f"Missing required environment variables: {', '.join(missing_keys)}"
            )
            return False

        return True

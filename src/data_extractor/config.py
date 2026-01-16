"""
Configuration module for the Data Extractor.
Loads environment variables and provides configuration settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the data_extractor directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Configuration settings for the data extractor."""
    
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Supported document types
    SUPPORTED_DOCUMENT_TYPES: list[str] = [
        "dni",
        "passport",
        "driving_license",
        "nie",
        "nota_simple",
        "escritura",
    ]
    
    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")


config = Config()

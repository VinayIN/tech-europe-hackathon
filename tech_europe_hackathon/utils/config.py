"""
Centralized configuration management for the AI Text Modification System.
Loads environment variables and provides configuration constants.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables once at module level
load_dotenv()

class Config:
    """Configuration class for centralized environment variable management"""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
    ACI_API_KEY: Optional[str] = os.getenv("ACI_API_KEY")
    BRAVE_SEARCH_API_KEY: Optional[str] = os.getenv("BRAVE_SEARCH_API_KEY")
    
    # Weaviate Configuration
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    WEAVIATE_API_KEY: Optional[str] = os.getenv("WEAVIATE_API_KEY")
    
    # Model Configuration
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")
    DEFAULT_VOICE_MODEL: str = os.getenv("DEFAULT_VOICE_MODEL", "eleven_monolingual_v1")
    
    # Application Configuration
    MAX_WORD_COUNT: int = 200
    MIN_WORD_COUNT: int = 150
    
    # Audio Configuration
    SUPPORTED_AUDIO_FORMATS: list = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
    MIN_AUDIO_FILE_SIZE: int = 100  # bytes
    MAX_AUDIO_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    
    # Web Scraping Configuration
    MAX_SCRAPING_WORDS: int = 150  # Target summary length (increased from 100)
    REQUEST_TIMEOUT: int = 30  # seconds
    
    # ACI.dev Configuration
    LINKED_ACCOUNT_OWNER_ID: str = os.getenv("LINKED_ACCOUNT_OWNER_ID", "default_user")
    
# Global config instance
CONFIG = Config()
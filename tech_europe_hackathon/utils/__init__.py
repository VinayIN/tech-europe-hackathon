"""
Utility modules for the AI Text Modification System
"""
from .config import CONFIG
from .document import TextDocument, StorageManager
from .audio import AudioProcessor, get_supported_formats

__all__ = [
    'CONFIG',
    'TextDocument',
    'StorageManager',
    'AudioProcessor',
    'get_supported_formats'
]
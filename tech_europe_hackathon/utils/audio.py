"""
Simple audio processing using ElevenLabs - File Upload Mode Only
"""
from typing import Optional, Union
from pathlib import Path
from elevenlabs import ElevenLabs
from tech_europe_hackathon.utils.config import CONFIG


class AudioProcessor:
    """Simple audio processor for file-based transcription"""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> ElevenLabs:
        """Get ElevenLabs client"""
        if self._client is None:
            if not CONFIG.ELEVENLABS_API_KEY:
                raise ValueError("ElevenLabs API key not found")
            self._client = ElevenLabs(api_key=CONFIG.ELEVENLABS_API_KEY)
        return self._client
    
    def process_audio_file(self, file_path: Union[str, Path]) -> Optional[str]:
        """Process audio file and return transcribed text"""
        file_path = Path(file_path)

        if not file_path.exists() or file_path.suffix.lower() not in get_supported_formats():
            print(f"Unsupported file format or file not found: {file_path}")
            return None
        
        # Use the speech_to_text client correctly - pass file path directly
        transcript = self.client.speech_to_text.convert(file=str(file_path), model_id=CONFIG.ELEVENLABS_MODEL_ID)
        return transcript
    
    def close(self):
        """Close ElevenLabs client if needed"""
        if hasattr(self._client, 'close'):
            self._client.close()
        self._client = None


def get_supported_formats() -> list:
    """Get supported audio formats"""
    return CONFIG.SUPPORTED_AUDIO_FORMATS

"""
Configuration Module
Handles environment variables, API keys, and application constants
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Keys
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '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')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'sk-or-v1-44a810c5dfef0a41eb42f63ace8b04a745f05dccbca00feab2ae47ed63c5b23')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID')
    
    # File Paths
    CONVERSATION_FILE = "conversation_history.json"
    MEMORY_FILE = "memory.json"
    REMINDER_FILE = "reminders.json"
    FACE_DATA_FILE = "owner_face.pkl"
    IMAGES_DIR = "images"
    TTS_CACHE_DIR = "tts_cache"
    
    # Voice Settings
    LISTEN_WINDOW = int(os.getenv('LISTEN_WINDOW', '20'))
    
    # TTS Settings
    TTS_RATE = 150
    TTS_VOLUME = 1.0
    
    # Face Recognition Settings
    FACE_CHECK_INTERVAL = 2  # seconds
    ALERT_COOLDOWN = 5  # seconds
    FACE_RECOGNITION_THRESHOLD = 0.55
    
    # Speech Recognition Settings
    ENERGY_THRESHOLD = 300
    PAUSE_THRESHOLD = 1.0
    PHRASE_TIME_LIMIT = 10
    
    # Activation phrases
    ACTIVATION_PHRASES = ["hey venom", "hi venom", "venom", "வனம்", "dei venom", "dei", "dai", "day"]
    
    @classmethod
    def print_config(cls):
        """Print loaded configuration (masked sensitive data)"""
        print("=" * 50)
        print("CONFIGURATION LOADED")
        print("=" * 50)
        print(f"OpenRouter API key: {cls.OPENROUTER_API_KEY[:20]}...")
        print(f"Google API key: {cls.GOOGLE_API_KEY[:20]}...")
        print(f"ElevenLabs configured: {bool(cls.ELEVENLABS_API_KEY)}")
        print(f"Listen window: {cls.LISTEN_WINDOW}s")
        print("=" * 50)
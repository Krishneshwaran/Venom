"""
Configuration Module
Stores application settings and API keys
"""

import os
from pathlib import Path


class Config:
    """Application configuration"""
    
    # API Keys - IMPORTANT: Use environment variables in production
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyA2j-XcTTHATJkiv3rfOIsv05-Pwyhu0pU')
    
    # File paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    CONVERSATION_FILE = DATA_DIR / 'conversations.json'
    MEMORY_FILE = DATA_DIR / 'memory.json'
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    # Model settings
    DEFAULT_MODEL = "gemini-2.0-flash-exp"
    LIVE_MODEL = "gemini-2.0-flash-exp"
    
    # Performance settings
    MAX_HISTORY_LENGTH = 3  # Keep only recent conversations
    IMAGE_MAX_SIZE = 800  # Max width/height for images
    VIDEO_FPS = 30
    VIDEO_WIDTH = 640
    VIDEO_HEIGHT = 480
    
    # Audio settings
    AUDIO_RATE = 16000
    AUDIO_CHANNELS = 1
    AUDIO_CHUNK = 512
    
    # Response settings
    MAX_OUTPUT_TOKENS = 150
    TEMPERATURE = 0.7
"""
AI Module
Handles AI model interactions (Google Gemini)
"""

import base64
import io
from PIL import Image
from google import genai
from config import Config
from utils import log_success, log_error, log_info

class AIEngine:
    """AI processing engine using Google Gemini"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Gemini client"""
        try:
            if Config.GOOGLE_API_KEY:
                self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
                log_success("Google Gemini client initialized")
            else:
                log_error("Google API key not found")
        except Exception as e:
            log_error(f"Failed to initialize Gemini client: {e}")
    
    def ask_with_image(self, image_base64, query, memory_context=""):
        """
        Send image and query to Google Gemini
        
        Args:
            image_base64: Base64 encoded image
            query: User query
            memory_context: Optional memory context to include
        
        Returns:
            AI response text
        """
        log_info("=" * 50)
        log_info("SENDING TO GOOGLE GEMINI API...")
        log_info(f"Query: {query}")
        log_info("=" * 50)
        
        try:
            if not self.client:
                return "AI client not initialized. Please check API key."
            
            # Decode base64 to PIL Image
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            # Build prompt with memory context
            full_prompt = f"{query}{memory_context}. உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும் — நண்பரிடம் பேசுற மாதிரி. மரியாதையா பேசணும், எப்போதும் தமிழிலேயே பதில் சொல்லணும் (அதிகபட்சம் 2-3 வாக்கியங்கள்)."
            
            log_info(f"Sending request with image size: {len(image_base64)} characters")
            
            # Make API call
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    full_prompt,
                    image
                ]
            )
            
            log_success("API response received")
            return response.text
        
        except Exception as e:
            log_error(f"AI API Error: {e}")
            return f"Error getting AI response: {str(e)}"
    
    def ask_text_only(self, query, memory_context=""):
        """
        Send text-only query to AI
        
        Args:
            query: User query
            memory_context: Optional memory context
        
        Returns:
            AI response text
        """
        try:
            if not self.client:
                return "AI client not initialized. Please check API key."
            
            full_prompt = f"{query}{memory_context}. Keep your response short and conversational."
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[full_prompt]
            )
            
            return response.text
        
        except Exception as e:
            log_error(f"AI text query error: {e}")
            return f"Error: {str(e)}"

# Global AI engine instance
_ai_engine = None

def get_ai_engine():
    """Get or create AI engine instance"""
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine()
    return _ai_engine

def ask_ai(image_base64, query, memory_context=""):
    """Ask AI with image"""
    engine = get_ai_engine()
    return engine.ask_with_image(image_base64, query, memory_context)

def ask_ai_text(query, memory_context=""):
    """Ask AI text-only question"""
    engine = get_ai_engine()
    return engine.ask_text_only(query, memory_context)
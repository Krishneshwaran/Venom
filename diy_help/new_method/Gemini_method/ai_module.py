"""
AI Module - Enhanced Version
Handles AI model interactions with optimized performance
Supports both traditional image queries and live chat
"""

import base64
import io
import asyncio
from PIL import Image
from google import genai
from google.genai import types
from config import Config
from utils import log_success, log_error, log_info


class AIEngine:
    """AI processing engine using Google Gemini with performance optimizations"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
        self._cache_enabled = True
    
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
        Send image and query to Google Gemini (optimized version)
        
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
            
            # Decode and optimize image
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            # Optimize image size for faster processing
            if image.width > 800 or image.height > 800:
                image.thumbnail((800, 800), Image.Resampling.LANCZOS)
                log_info("Image resized for optimization")
            
            # Get conversation history (limited to reduce tokens)
            from conversation_module import get_conversation_history
            history = get_conversation_history(limit=3)  # Reduced from 5 to 3
            history_text = ""
            if history:
                history_text = "\n\nRecent context:\n"
                for conv in history[-3:]:
                    # Truncate long responses
                    q_short = conv['question'][:100]
                    r_short = conv['response'][:100]
                    history_text += f"Q: {q_short}\nA: {r_short}\n"
            
            # Build optimized prompt
            full_prompt = f"{query}{memory_context}{history_text}. உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும் — நண்பரிடம் பேசுற மாதிரி. மரியாதையா பேசணும், எப்போதும் தமிழிலேயே பதில் சொல்லணும் (அதிகபட்சம் 2-3 வாக்கியங்கள்)."
            
            log_info(f"Optimized request size: {len(image_base64)} chars")
            
            # Make API call with optimized model
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",  # Faster model
                contents=[
                    full_prompt,
                    image
                ],
                generation_config={
                    "max_output_tokens": 150,  # Limit response length
                    "temperature": 0.7,
                }
            )
            
            log_success("API response received")
            return response.text
        
        except Exception as e:
            log_error(f"AI API Error: {e}")
            return f"Error getting AI response: {str(e)}"
    
    def ask_text_only(self, query, memory_context=""):
        """
        Send text-only query to AI (optimized)
        
        Args:
            query: User query
            memory_context: Optional memory context
        
        Returns:
            AI response text
        """
        try:
            if not self.client:
                return "AI client not initialized. Please check API key."
            
            # Get conversation history (limited)
            from conversation_module import get_conversation_history
            history = get_conversation_history(limit=3)
            history_text = ""
            if history:
                history_text = "\n\nRecent context:\n"
                for conv in history[-3:]:
                    history_text += f"Q: {conv['question'][:80]}\nA: {conv['response'][:80]}\n"
            
            full_prompt = f"{query}{memory_context}{history_text}. Keep response brief (2-3 sentences)."
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[full_prompt],
                generation_config={
                    "max_output_tokens": 150,
                    "temperature": 0.7,
                }
            )
            
            return response.text
        
        except Exception as e:
            log_error(f"AI text query error: {e}")
            return f"Error: {str(e)}"
    
    async def ask_with_image_async(self, image_base64, query, memory_context=""):
        """Async version for better performance in concurrent scenarios"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.ask_with_image, image_base64, query, memory_context
        )
    
    async def ask_text_only_async(self, query, memory_context=""):
        """Async version of text query"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.ask_text_only, query, memory_context
        )
    
    def batch_process_images(self, image_query_pairs):
        """
        Process multiple images in batch (more efficient than sequential)
        
        Args:
            image_query_pairs: List of tuples [(image_base64, query), ...]
        
        Returns:
            List of responses
        """
        responses = []
        for image_base64, query in image_query_pairs:
            response = self.ask_with_image(image_base64, query)
            responses.append(response)
        return responses


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

async def ask_ai_async(image_base64, query, memory_context=""):
    """Async version - ask AI with image"""
    engine = get_ai_engine()
    return await engine.ask_with_image_async(image_base64, query, memory_context)

async def ask_ai_text_async(query, memory_context=""):
    """Async version - ask AI text-only"""
    engine = get_ai_engine()
    return await engine.ask_text_only_async(query, memory_context)
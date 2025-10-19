"""
Memory Management Functions for Venom AI Assistant
This module contains all memory-related functionality including:
- Saving memories to JSON file
- Searching/retrieving memories
- Detecting memory commands from user input
- AI integration for visual memory analysis
- Image processing and encoding
- Speech recognition for voice commands
"""

import os
import json
from datetime import datetime
import base64
import io
from PIL import Image
import cv2
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Memory file configuration
MEMORY_FILE = "memory.json"

# API Configuration
google_api_key = os.getenv('GOOGLE_API_KEY', '')


def encode_image(image):
    """Encode PIL Image to base64 string, ensuring under 4MB limit."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)  # Use JPEG for better compression
    size_mb = len(buffer.getvalue()) / (1024 * 1024)
    if size_mb > 4:
        # Resize and try again
        image = image.resize((640, 480))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def ask_ai(image_base64, query):
    """Send image and query to Google Gemini 2.5 Flash model with memory context."""
    print("=" * 50)
    print("SENDING TO GOOGLE GEMINI API...")
    print(f"Query: {query}")
    print("=" * 50)
    
    try:
        # First check if there are relevant memories
        relevant_memories = search_memories(query)
        memory_context = ""
        
        if relevant_memories:
            print(f"🧠 Found {len(relevant_memories)} relevant memories")
            memory_context = "\n\nRELEVANT MEMORIES:\n"
            for mem in relevant_memories[:5]:  # Top 5 memories
                memory_context += f"- {mem.get('memory', '')}\n"
            memory_context += "\nUse these memories to answer if relevant."
        
        print(f"Sending request with image size: {len(image_base64)} characters")
        
        # Decode base64 to bytes for PIL
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        client = genai.Client(api_key=google_api_key)
        
        # Include memory context in the prompt
        full_prompt = f"{query}{memory_context}. Keep your response short, natural, and conversational - like talking to a friend. Maximum 2-3 sentences."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                full_prompt,
                image
            ]
        )
        
        print("API response received")
        return response.text
    except Exception as e:
        print(f"API Error: {e}")
        return f"Error getting AI response: {str(e)}"


def process_frame_for_memory(frame, user_command):
    """Process camera frame to extract memory information using AI."""
    try:
        print("📸 Analyzing scene with camera for memory...")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        # Save image for reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        images_dir = "images"
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)
        
        img.save(f"{images_dir}/memory_{timestamp}.png")
        print(f"💾 Image saved: {images_dir}/memory_{timestamp}.png")
        
        # Resize for faster processing
        img = img.resize((256, 256))
        img_b64 = encode_image(img)
        
        # Ask AI to analyze what user wants to remember with context
        prompt = f"The user said: '{user_command}'. Analyze the image and describe what they want you to remember. Include what object it is and where it's located. Be specific and concise (1-2 sentences)."
        memory_text = ask_ai(img_b64, prompt)
        memory_text = memory_text.strip()
        
        return memory_text
    except Exception as e:
        print(f"❌ Error processing frame for memory: {e}")
        return None


def extract_memory_from_text(text):
    """Extract memory information from text command without camera."""
    text_lower = text.lower()
    memory_text = ""
    
    # Smart extraction based on patterns
    if 'my name is' in text_lower:
        # Extract "Kavin" from "remember my name is Kavin"
        parts = text_lower.split('my name is')
        if len(parts) > 1:
            memory_text = f"User's name is {parts[1].strip()}"
    elif 'my name as' in text_lower:
        # Extract "Kavin" from "remember my name as Kavin"
        parts = text_lower.split('my name as')
        if len(parts) > 1:
            memory_text = f"User's name is {parts[1].strip()}"
    elif 'my card number' in text_lower or 'card number' in text_lower:
        # Extract card info
        parts = text_lower.split('card number')
        if len(parts) > 1:
            memory_text = f"User's card number: {parts[1].replace('is', '').strip()}"
    else:
        # Try to extract after "remember" keyword
        for trigger in ['remember this', 'remember that', 'remember']:
            if trigger in text_lower:
                parts = text_lower.split(trigger)
                if len(parts) > 1:
                    extracted = parts[1].strip()
                    if extracted:
                        memory_text = extracted
                        break
    
    return memory_text if memory_text else None


def needs_visual_context(text):
    """Check if the memory command needs camera/visual context."""
    text_lower = text.lower()
    
    # Keywords that indicate visual objects or locations
    visual_keywords = ['keeping', 'kept', 'placed', 'put', 'this', 'that', 'here', 'there', 
                      'mobile', 'phone', 'laptop', 'keys', 'wallet', 'bottle', 'cup', 'book',
                      'where', 'location', 'position', 'bike', 'car', 'bag', 'watch']
    
    # Check if visual keywords are present
    needs_camera = any(keyword in text_lower for keyword in visual_keywords)
    
    # If text is very short or generic after removing trigger words, use camera
    text_without_trigger = text_lower.replace('remember', '').replace('i am', '').replace('this', '').replace('that', '').strip()
    if len(text_without_trigger) < 5:  # Very short/vague command
        needs_camera = True
    
    return needs_camera


def save_memory(memory_text, context=""):
    """Save a memory to the memory file."""
    try:
        # Load existing memories
        memories = []
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Only parse if file has content
                        memories = json.loads(content)
            except json.JSONDecodeError:
                print("⚠️ Memory file corrupted, initializing fresh...")
                memories = []
        
        # Add new memory
        memory_entry = {
            "id": len(memories) + 1,
            "timestamp": datetime.now().isoformat(),
            "memory": memory_text,
            "context": context
        }
        memories.append(memory_entry)
        
        # Save back to file
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)
        
        print(f"🧠 Memory saved to {MEMORY_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving memory: {e}")
        return False


def search_memories(query):
    """Search for relevant memories based on query."""
    try:
        if not os.path.exists(MEMORY_FILE):
            return []
        
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:  # Empty file
                return []
            memories = json.loads(content)
        
        # Simple keyword search
        query_lower = query.lower()
        query_words = query_lower.split()
        relevant_memories = []
        
        for memory in memories:
            memory_text = memory.get('memory', '').lower()
            # Check if any query word is in memory
            match_count = sum(1 for word in query_words if word in memory_text)
            if match_count > 0:
                # Add score for better matching
                memory['match_score'] = match_count
                relevant_memories.append(memory)
        
        # Sort by match score (best matches first)
        relevant_memories.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return relevant_memories
    except Exception as e:
        print(f"❌ Error searching memories: {e}")
        return []


def is_memory_command(text):
    """Check if the text is a memory-related command."""
    text_lower = text.lower()
    
    # Memory save commands - check if "remember" appears with something to remember
    save_triggers = ['remember this', 'remember that', 'save this', 'note this', 
                     'keep this in mind', 'don\'t forget', 'make a note', 'memorize this',
                     'remember my', 'remember i']
    
    # Memory recall commands
    recall_triggers = ['what do you remember', 'do you remember', 'recall', 
                      'what did i tell you', 'remind me about', 'what do you know about',
                      'tell me what you remember', 'what\'s my', 'what is my']
    
    for trigger in save_triggers:
        if trigger in text_lower:
            return "save"
    
    for trigger in recall_triggers:
        if trigger in text_lower:
            return "recall"
    
    return None


def get_all_memories():
    """Get all memories from the memory file."""
    try:
        if not os.path.exists(MEMORY_FILE):
            return []
        
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:  # Empty file
                return []
            memories = json.loads(content)
        
        return memories
    except Exception as e:
        print(f"❌ Error loading memories: {e}")
        return []


def delete_memory(memory_id):
    """Delete a specific memory by ID."""
    try:
        if not os.path.exists(MEMORY_FILE):
            return False
        
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return False
            memories = json.loads(content)
        
        # Filter out the memory with matching ID
        memories = [m for m in memories if m.get('id') != memory_id]
        
        # Save back to file
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memories, f, indent=2, ensure_ascii=False)
        
        print(f"🗑️ Memory {memory_id} deleted")
        return True
    except Exception as e:
        print(f"❌ Error deleting memory: {e}")
        return False


def clear_all_memories():
    """Clear all memories from the memory file."""
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        print("🗑️ All memories cleared")
        return True
    except Exception as e:
        print(f"❌ Error clearing memories: {e}")
        return False


def recall_memory_with_context(query, current_frame=None):
    """Recall memories with optional visual context from camera."""
    try:
        # Search memories
        relevant_memories = search_memories(query)
        
        if relevant_memories and current_frame is not None:
            # Use AI to generate natural response based on memories and current scene
            print("📸 Processing frame with memory context...")
            frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            images_dir = "images"
            if not os.path.exists(images_dir):
                os.makedirs(images_dir, exist_ok=True)
                
            img.save(f"{images_dir}/captured_{timestamp}.png")
            print(f"💾 Image saved: {images_dir}/captured_{timestamp}.png")
            
            img = img.resize((256, 256))
            img_b64 = encode_image(img)
            
            # Build memory context
            memory_context = "\n\nRELEVANT MEMORIES:\n"
            for mem in relevant_memories[:5]:
                memory_context += f"- {mem.get('memory', '')}\n"
            
            # Let AI answer naturally using memory context
            answer = ask_ai(img_b64, f"{query}{memory_context}\n\nAnswer the question naturally using these memories.")
            return answer
            
        elif relevant_memories:
            # No camera, just use memories
            memory_text = ", ".join([mem['memory'] for mem in relevant_memories[-3:]])
            return f"Based on what I remember: {memory_text}"
        else:
            return "I don't have any memories matching that. Try asking me to remember something first!"
            
    except Exception as e:
        print(f"❌ Error recalling memory: {e}")
        return "Sorry, I had trouble recalling that memory."


def process_memory_command(text, current_frame=None):
    """
    Main function to process memory commands (save or recall).
    
    Args:
        text: User's voice command
        current_frame: Optional camera frame for visual context
        
    Returns:
        tuple: (success: bool, response_message: str)
    """
    memory_cmd = is_memory_command(text)
    
    if memory_cmd == "save":
        # Extract what to remember
        user_context = text  # Keep the original command as context
        memory_text = extract_memory_from_text(text)
        
        # Check if we need camera for this memory
        if needs_visual_context(text) or not memory_text:
            if current_frame is not None:
                # Use camera to analyze the scene
                memory_text = process_frame_for_memory(current_frame, text)
            else:
                # No camera available and we need visual context
                return False, "I need to see what you're referring to, but camera is not available."
        
        # Save the memory
        if memory_text and save_memory(memory_text, f"User said: {user_context}"):
            return True, "Got it! I'll remember that."
        else:
            return False, "Sorry, I couldn't save that memory."
            
    elif memory_cmd == "recall":
        # Search and recall memories
        answer = recall_memory_with_context(text, current_frame)
        return True, answer
        
    else:
        return False, "Not a memory command."


if __name__ == "__main__":
    # Test the functions
    print("Testing memory functions...")
    
    # Test saving a memory
    save_memory("User's favorite color is blue", "User said: remember my favorite color is blue")
    
    # Test searching memories
    results = search_memories("favorite color")
    print(f"Search results: {results}")
    
    # Test getting all memories
    all_memories = get_all_memories()
    print(f"Total memories: {len(all_memories)}")
    
    # Test memory command detection
    print(f"'remember this' -> {is_memory_command('remember this')}")
    print(f"'what do you remember' -> {is_memory_command('what do you remember')}")
    print(f"'hello' -> {is_memory_command('hello')}")
    
    # Test text extraction
    print(f"\nText extraction test:")
    print(f"'remember my name is John' -> {extract_memory_from_text('remember my name is John')}")
    
    # Test visual context detection
    print(f"\nVisual context test:")
    print(f"'remember where I kept my phone' -> {needs_visual_context('remember where I kept my phone')}")
    print(f"'remember my name is John' -> {needs_visual_context('remember my name is John')}")

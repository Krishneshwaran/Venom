import mss
import base64
from PIL import Image
import speech_recognition as sr
import pyttsx3
import os
import cv2
from dotenv import load_dotenv
import threading
import queue
import time
import io
import sys
import requests
import json  # Import json for handling JSON data
from openai import OpenAI
from google import genai
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Set API keys
groq_api_key = os.getenv('GROQ_API_KEY', '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')
openrouter_api_key = os.getenv('OPENROUTER_API_KEY', 'sk-or-v1-44a810c5dfef0a41eb42f63ace8b04a745f05dccbca00feab2ae47ed63c5b23')
google_api_key = os.getenv('GOOGLE_API_KEY', '')

print(f"Loaded OpenRouter API key: {openrouter_api_key[:20]}...")
print(f"Loaded Google API key: {google_api_key[:20]}...")

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Adjust speech rate
engine.setProperty('volume', 1.0)  # Set volume to maximum

# Test if TTS is working
print("Testing text-to-speech engine...")
voices = engine.getProperty('voices')
if voices:
    # Use first available voice
    engine.setProperty('voice', voices[0].id)
    print(f"Using voice: {voices[0].name}")

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Global flag for graceful shutdown
shutdown_flag = False

# Global flag for processing state
processing_flag = False

# Global flag for voice activation
is_listening_active = False
activation_time = 0

# Conversation history file
CONVERSATION_FILE = "conversation_history.json"

def save_conversation(question, response):
    """Save question and response to JSON file."""
    try:
        # Load existing conversations
        if os.path.exists(CONVERSATION_FILE):
            with open(CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
        else:
            conversations = []
        
        # Add new conversation
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response
        }
        conversations.append(conversation_entry)
        
        # Save back to file
        with open(CONVERSATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Conversation saved to {CONVERSATION_FILE}")
    except Exception as e:
        print(f"❌ Error saving conversation: {e}")

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
    """Send image and query to Google Gemini 2.5 Flash model."""
    print("=" * 50)
    print("SENDING TO GOOGLE GEMINI API...")
    print(f"Query: {query}")
    print("=" * 50)
    
    try:
        print(f"Sending request with image size: {len(image_base64)} characters")
        
        # Decode base64 to bytes for PIL
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        client = genai.Client(api_key=google_api_key)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                f"{query}. Keep your response short, natural, and conversational - like talking to a friend. Maximum 2-3 sentences.",
                image
            ]
        )
        
        print("API response received")
        return response.text
    except Exception as e:
        print(f"API Error: {e}")
        return f"Error getting AI response: {str(e)}"

def speak(text, save_audio=False):
    """Convert text to speech without saving audio file."""
    try:
        print(f"🔊 Speaking: {text[:50]}...")
        
        # Use macOS native 'say' command which is more reliable
        import subprocess
        # Escape quotes in text
        text_escaped = text.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
        subprocess.run(['say', text_escaped], check=True)
        
        print("✅ Audio playback complete")
    except Exception as e:
        print(f"❌ Speech error: {e}")
        # Fallback to pyttsx3
        try:
            speech_engine = pyttsx3.init()
            speech_engine.setProperty('rate', 150)
            speech_engine.setProperty('volume', 1.0)
            speech_engine.say(text)
            speech_engine.runAndWait()
            speech_engine.stop()
        except:
            print("Failed to speak text")

def voice_listener(voice_queue):
    """Background thread for continuous voice listening."""
    global processing_flag, is_listening_active, activation_time  # Access global flags
    
    mic_list = sr.Microphone.list_microphone_names()
    print(f"Available microphones: {mic_list}")
    
    # Try to find the best microphone
    mic_index = None
    for i, mic_name in enumerate(mic_list):
        if "microphone" in mic_name.lower() and "speakers" not in mic_name.lower():
            mic_index = i
            break
    
    # If no microphone found, use default
    if mic_index is None:
        mic_index = None  # Use default microphone
    
    print(f"Using microphone: {mic_list[mic_index] if mic_index is not None and mic_index < len(mic_list) else 'Default'}")
    
    while not shutdown_flag:
        try:
            with sr.Microphone(device_index=mic_index) as source:
                print("Initializing microphone...")
                recognizer.adjust_for_ambient_noise(source, duration=2)
                recognizer.energy_threshold = 300
                recognizer.dynamic_energy_threshold = True
                recognizer.pause_threshold = 1.0  # Increased to detect pauses in speech
                print("Voice listener ready...")
                
                while not shutdown_flag:
                    if processing_flag:
                        time.sleep(0.1)  # Skip listening when processing
                        continue
                    
                    # Check if 10 seconds have passed since activation
                    if is_listening_active and time.time() - activation_time > 10:
                        is_listening_active = False
                        print("⏰ Listening window closed. Say 'hey venom' to activate again.")
                    
                    try:
                        print("🎤 Listening..." if is_listening_active else "💤 Waiting for 'hey venom'...")
                        # Listen for longer to capture complete sentences
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        print("🔊 Audio captured, recognizing...")
                        text = recognizer.recognize_google(audio)
                        print(f"✅ Recognized: '{text}'")
                        
                        text_lower = text.lower()
                        
                        # Check for activation phrase
                        if "hey venom" in text_lower or "hi venom" in text_lower:
                            is_listening_active = True
                            activation_time = time.time()
                            print("🟢 Venom activated! Listening for your command...")
                            # Don't queue the activation phrase itself
                            time.sleep(0.5)
                            continue
                        
                        # Only queue commands if listening is active
                        if is_listening_active and len(text.split()) > 0 and not processing_flag:
                            print(f"Voice: {text}")
                            voice_queue.put(text)
                            print(f"📤 Command queued: '{text}'")
                            # Wait briefly to avoid multiple captures
                            time.sleep(0.5)
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        if is_listening_active:
                            print("❌ Could not understand audio")
                        continue
                    except sr.RequestError as e:
                        print(f"❌ Google API error: {e}")
                        continue
                    except Exception as e:
                        print(f"❌ Voice recognition error: {e}")
                        continue
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            if mic_index is not None:
                print("Trying default microphone next time")
                mic_index = None
            time.sleep(2)  # Wait before retrying

def is_command(text):
    """Check if the text is a valid command or question."""
    question_words = ['what', 'where', 'when', 'why', 'how', 'who', 'which', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does', 'did']
    action_words = ['tell', 'show', 'explain', 'describe', 'identify', 'find', 'look', 'search', 'check', 'see', 'read', 'scan']
    text_lower = text.lower()
    
    # Check for exit command
    if "exit" in text_lower or "quit" in text_lower or "stop" in text_lower:
        return "exit"
    
    # Check for help command
    if "help me" in text_lower:
        return "help"
    
    # Check if it ends with a question mark
    if text_lower.endswith('?'):
        return "question"
    
    # Check if it starts with a question word
    words = text_lower.split()
    if words and words[0] in question_words:
        return "question"
    
    # Check if it contains action words
    if any(word in text_lower for word in action_words):
        return "question"
    
    # Check if it contains brand names or specific items (like "oneplus")
    brands = ['oneplus', 'iphone', 'samsung', 'xiaomi', 'oppo', 'vivo', 'nokia', 'motorola', 'lg', 'sony', 'huawei']
    if any(brand in text_lower for brand in brands):
        return "question"
    
    # Check if it's a single word or short phrase that might be a request
    if len(words) <= 3:
        return "question"
    
    # If nothing matches, still treat it as a question to be more permissive
    return "question"

def main():
    """Main loop for DIY help system with continuous camera feed."""
    global processing_flag, is_listening_active, activation_time  # Access global flags
    
    print("DIY Camera Helper started. Your personal AI vision assistant.")
    speak("Hey! I'm Venom, your AI assistant. Say 'hey venom' whenever you need me!")

    # Try to initialize camera
    cap = cv2.VideoCapture(0)
    camera_available = False
    
    if cap.isOpened():
        # Test camera by grabbing a frame
        ret, test_frame = cap.read()
        if ret:
            camera_available = True
            print("✅ Camera initialized successfully")
            speak("Camera's ready to go!")
        else:
            print("⚠️ Camera opened but cannot capture frames")
            cap.release()
    else:
        print("❌ Could not open camera. Please check camera permissions and connections.")
    
    if not camera_available:
        print("🔄 Starting in TEXT-ONLY mode (no camera)")
        speak("No camera found, but I can still help you out. Just describe what you need!")
        # Continue without camera
        cap = None

    # Start voice listening thread
    voice_queue = queue.Queue()
    voice_thread = threading.Thread(target=voice_listener, args=(voice_queue,), daemon=True)
    voice_thread.start()

    waiting_for_question = False
    current_frame = None
    camera_error_count = 0
    processing_command = False  # Flag to indicate when processing a command
    # Removed real-time processing variables

    while True:
        if camera_available and cap is not None:
            ret, frame = cap.read()
            if ret:
                camera_error_count = 0  # Reset error count on success
                
                # Add processing overlay if currently processing a command
                if processing_command:
                    cv2.putText(frame, "PROCESSING YOUR REQUEST...", (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, "Voice listening paused", (10, 60), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                cv2.imshow('Camera Feed - Say "hey venom" to activate', frame)
                current_frame = frame
                # Removed automatic real-time processing
            else:
                camera_error_count += 1
                print(f"⚠️ Camera frame grab failed ({camera_error_count}/5)")
                
                if camera_error_count >= 5:
                    print("❌ Camera failed 5 times. Switching to text-only mode...")
                    speak("Camera error. Switching to text-only mode.")
                    camera_available = False
                    if cap:
                        cap.release()
                        cap = None
        else:
            # Text-only mode - just wait for commands
            time.sleep(0.1)  # Small delay to prevent busy loop
        
        # Check for voice commands
        try:
            text = voice_queue.get_nowait()
            print(f"📥 Processing command: '{text}'")
            processing_command = True  # Set processing flag
            processing_flag = True  # Set global processing flag to stop voice listening
            
            # Process any recognized speech as a potential question/command
            if text.strip():  # Any non-empty text
                print(f"🤖 COMMAND DETECTED: {text}")
                print("🔄 Processing your request... (voice listening paused)")
                
                if camera_available and current_frame is not None:
                    print("📸 Processing frame...")
                    # Convert current frame to PIL Image
                    frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    # Save debug image
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    img.save(f"images/captured_{timestamp}.png")
                    print(f"💾 Image saved: images/captured_{timestamp}.png")
                    # Resize for faster processing and API limits
                    img = img.resize((256, 256))  # Smaller size
                    img_b64 = encode_image(img)
                    print(f"Base64 length: {len(img_b64)}")
                    # Test if base64 is valid
                    try:
                        test_decode = base64.b64decode(img_b64)
                        print(f"Base64 decode successful, size: {len(test_decode)} bytes")
                    except Exception as e:
                        print(f"Base64 decode failed: {e}")
                        return f"Image encoding error: {e}"
                    print("📤 Image encoded, sending to Gemini...")
                    
                    # Get AI response
                    answer = ask_ai(img_b64, text)
                    answer = answer.strip()
                    # Clean up response for better speech
                    answer = answer.replace('\n', ' ').replace('  ', ' ')
                    print(f"🤖 AI RESPONSE: {answer}")
                    
                    # Save conversation to JSON
                    save_conversation(text, answer)
                    
                    # Speak the response
                    speak(answer)
                    
                    # Reset activation after response
                    is_listening_active = True
                    activation_time = time.time()
                    
                    processing_command = False  # Reset processing flag
                    processing_flag = False  # Reset global processing flag
                    print("✅ Ready for next command within 10 seconds, or say 'hey venom' again.")
                else:
                    # Text-only response
                    print("📝 Processing text-only query...")
                    answer = f"I heard: '{text}'. Since camera is not available, I can help with general advice. Please describe what you need help with in more detail."
                    print(f"🤖 AI RESPONSE: {answer}")
                    
                    # Save conversation to JSON
                    save_conversation(text, answer)
                    
                    # Speak the response
                    speak(answer)
                    
                    processing_command = False  # Reset processing flag
                    processing_flag = False  # Reset global processing flag
                    print("✅ Ready for next command. Say 'help me' or ask a question.")
                    
        except queue.Empty:
            pass
        
        # Check for quit key (only if camera window is open)
        if camera_available and cv2.waitKey(1) & 0xFF == ord('q'):
            break

    if cap:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("⚠️ Keyboard interrupt received")
        print("✅ Application closed")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("✅ Application closed")
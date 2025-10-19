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
from google import genai
from datetime import datetime, timedelta
import face_recognition
import numpy as np
import pickle

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

# Listening/tts control globals
last_interaction_time = 0
# How long (seconds) to keep listening after activation or last command
LISTEN_WINDOW = int(os.getenv('LISTEN_WINDOW', '20'))
# Flag to avoid capturing assistant's own speech
speaking_flag = False

# --- TTS: async wrapper, cache and ElevenLabs support ---
TTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'tts_cache')
if not os.path.exists(TTS_CACHE_DIR):
    try:
        os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    except Exception:
        pass


def _do_speak(text, save_audio=False):
    """Internal blocking TTS routine (kept separate so speak() can be async)."""
    global speaking_flag
    try:
        print(f"🔊 Speaking: {text[:50]}...")

        # Try ElevenLabs TTS first if API key present
        eleven_key = os.getenv('ELEVENLABS_API_KEY')
        eleven_voice = os.getenv('ELEVENLABS_VOICE_ID')

        if eleven_key and eleven_voice:
            try:
                import tempfile
                import subprocess

                # If cached audio exists for this text, use it to save round trip time
                safe_name = "tts_" + str(abs(hash(text))) + ".mp3"
                cache_path = os.path.join(TTS_CACHE_DIR, safe_name)
                if os.path.exists(cache_path):
                    try:
                        subprocess.run(['afplay', cache_path], check=True)
                        print("✅ Spoken via ElevenLabs cache")
                        return
                    except Exception:
                        # if cache playback fails, fall through to regenerate
                        pass

                url = f"https://api.elevenlabs.io/v1/text-to-speech/{eleven_voice}"
                headers = {
                    'xi-api-key': eleven_key,
                    'Content-Type': 'application/json'
                }
                payload = {
                    'text': text,
                    'voice_settings': {
                        'stability': 0.5,
                        'similarity_boost': 0.75
                    }
                }

                resp = requests.post(url, headers=headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    # ElevenLabs returns audio bytes
                    suffix = '.mp3'
                    # write to cache path (or temp if not saving)
                    write_path = cache_path if save_audio else None
                    if write_path:
                        with open(write_path, 'wb') as f:
                            f.write(resp.content)
                        try:
                            subprocess.run(['afplay', write_path], check=True)
                            print("✅ Spoken via ElevenLabs (cached)")
                            return
                        except Exception:
                            pass
                    else:
                        with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
                            tmp.write(resp.content)
                            tmp.flush()
                            try:
                                subprocess.run(['afplay', tmp.name], check=True)
                                print("✅ Spoken via ElevenLabs")
                                return
                            except Exception:
                                pass
                else:
                    print(f"⚠️ ElevenLabs TTS failed: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"⚠️ ElevenLabs TTS error: {e}")

        # If ElevenLabs not configured or fails, use macOS native 'say' command
        try:
            import subprocess
            # Escape quotes in text
            text_escaped = text.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
            subprocess.run(['say', text_escaped], check=True)
            print("✅ Audio playback complete (say)")
            return
        except Exception as e:
            print(f"❌ Speech error with 'say': {e}")

        # Final fallback to pyttsx3
        try:
            speech_engine = pyttsx3.init()
            speech_engine.setProperty('rate', 150)
            speech_engine.setProperty('volume', 1.0)
            speech_engine.say(text)
            speech_engine.runAndWait()
            speech_engine.stop()
            print("✅ Audio playback complete (pyttsx3)")
        except Exception as e:
            print(f"Failed to speak text with pyttsx3: {e}")
    except Exception as e:
        print(f"Unexpected error in speak(): {e}")
    finally:
        # small buffer to avoid immediate re-capture of the assistant's voice
        try:
            time.sleep(0.12)
            speaking_flag = False
        except Exception:
            pass


def speak(text, save_audio=False, async_play=True):
    """Public speak API. By default runs async to avoid blocking the main loop.
    Set async_play=False to block until speech finishes."""
    global speaking_flag
    if async_play:
        try:
            speaking_flag = True
        except Exception:
            pass
        t = threading.Thread(target=_do_speak, args=(text, save_audio), daemon=True)
        t.start()
        return
    else:
        try:
            speaking_flag = True
        except Exception:
            pass
        return _do_speak(text, save_audio)

# --- end TTS ---

# Global flag for graceful shutdown
shutdown_flag = False

# Global flag for processing state
processing_flag = False

# Global flag for voice activation
is_listening_active = False
activation_time = 0

# Conversation history file
CONVERSATION_FILE = "conversation_history.json"
MEMORY_FILE = "memory.json"
REMINDER_FILE = "reminders.json"
FACE_DATA_FILE = "owner_face.pkl"

# Ensure images directory exists for saving captured frames
IMAGES_DIR = "images"
if not os.path.exists(IMAGES_DIR):
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        print(f"✅ Created images directory: {IMAGES_DIR}")
    except Exception as e:
        print(f"⚠️ Could not create images directory '{IMAGES_DIR}': {e}")

# Global for pending reminder info (when user says "remind me" without details)
pending_reminder = {"waiting_for": None, "task": None, "time": None}

# Global for face recognition
owner_face_encoding = None
home_security_active = False
last_face_check_time = 0
face_check_interval = 2  # Check faces every 2 seconds (faster detection)
last_alert_time = 0
alert_cooldown = 5  # Don't repeat alert within 5 seconds (for testing)

def save_reminder(task, remind_time):
    """Save a reminder to the reminders file."""
    try:
        # Load existing reminders
        reminders = []
        if os.path.exists(REMINDER_FILE):
            try:
                with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        reminders = json.loads(content)
            except json.JSONDecodeError:
                print("⚠️ Reminder file corrupted, initializing fresh...")
                reminders = []
        
        # Add new reminder
        reminder_entry = {
            "id": len(reminders) + 1,
            "task": task,
            "remind_time": remind_time.isoformat(),
            "created_at": datetime.now().isoformat(),
            "completed": False
        }
        reminders.append(reminder_entry)
        
        # Save back to file
        with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
            json.dump(reminders, f, indent=2, ensure_ascii=False)
        
        print(f"⏰ Reminder saved to {REMINDER_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving reminder: {e}")
        return False

def check_reminders():
    """Background thread to check for due reminders."""
    global shutdown_flag
    print("⏰ Reminder checker started...")
    
    while not shutdown_flag:
        try:
            if os.path.exists(REMINDER_FILE):
                with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        reminders = json.loads(content)
                        current_time = datetime.now()
                        
                        for reminder in reminders:
                            if not reminder.get('completed', False):
                                remind_time = datetime.fromisoformat(reminder['remind_time'])
                                
                                # Check if reminder is due
                                if current_time >= remind_time:
                                    task = reminder['task']
                                    print(f"\n🔔 REMINDER: {task}")
                                    speak(f"Reminder! {task}")
                                    
                                    # Mark as completed
                                    reminder['completed'] = True
                        
                        # Save updated reminders
                        with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
                            json.dump(reminders, f, indent=2, ensure_ascii=False)
            
            # Check every 10 seconds
            time.sleep(10)
        except Exception as e:
            print(f"❌ Error in reminder checker: {e}")
            time.sleep(10)

def monitor_faces_background(cap):
    """Background thread to monitor for strangers even in sleep mode."""
    global shutdown_flag, home_security_active, last_face_check_time, last_alert_time
    print("👁️ Face monitoring started...")
    
    owner_left = False  # Track if owner has actually left (no face for 5+ seconds)
    owner_welcomed = False  # Track if owner has been welcomed after leaving
    no_face_time = None  # Track when owner's face disappeared
    last_detection = None  # Track last detection to avoid flip-flopping
    detection_count = {"owner": 0, "stranger": 0}  # Count consecutive detections
    
    while not shutdown_flag:
        try:
            if home_security_active and cap is not None:
                current_time = time.time()
                
                # Check faces every N seconds
                if current_time - last_face_check_time >= face_check_interval:
                    try:
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            result = check_for_faces(frame)
                            
                            if result == "stranger":
                                detection_count["stranger"] += 1
                                detection_count["owner"] = 0
                                print(f"🚨 Stranger count: {detection_count['stranger']}/1")
                                
                                # Require only 1 consecutive stranger detection for faster response
                                if detection_count["stranger"] >= 1:
                                    # Alert for stranger
                                    if current_time - last_alert_time >= alert_cooldown:
                                        print("\n🚨 STRANGER DETECTED!")
                                        speak("Alert! Stranger intruded!")
                                        last_alert_time = current_time
                                        owner_welcomed = False  # Reset welcome flag
                                        owner_left = True
                                        no_face_time = None
                                        # Reset stranger count after alert
                                        detection_count["stranger"] = 0
                            
                            elif result == "owner":
                                detection_count["owner"] += 1
                                detection_count["stranger"] = 0
                                print(f"👋 Owner count: {detection_count['owner']}/3")
                                no_face_time = None  # Reset no-face timer
                                
                                # Require 3 consecutive owner detections for welcome
                                if detection_count["owner"] >= 3:
                                    # Welcome owner back only if they actually left
                                    if owner_left and not owner_welcomed:
                                        print("\n👋 OWNER DETECTED!")
                                        speak("Welcome back, bro!")
                                        owner_welcomed = True
                                        owner_left = False
                                        # DISABLE security monitoring until user leaves again
                                        home_security_active = False
                                        print("🏠 Security monitoring paused. Say 'I am leaving home' to activate again.")
                                        detection_count = {"owner": 0, "stranger": 0}
                                        break  # Exit the monitoring loop
                            
                            else:  # No face detected
                                detection_count["owner"] = 0
                                detection_count["stranger"] = 0
                                
                                # Start tracking no-face time
                                if no_face_time is None:
                                    no_face_time = current_time
                                
                                # If no face for 5+ seconds, consider owner has left
                                elif current_time - no_face_time >= 5:
                                    if not owner_left:
                                        print("👤 No face detected for 5 seconds - Owner considered left")
                                        owner_left = True
                                        owner_welcomed = False
                        else:
                            print("⚠️ Failed to read frame from camera")
                    except Exception as frame_error:
                        print(f"❌ Error processing frame: {frame_error}")
                        # Continue without crashing
                    
                    last_face_check_time = current_time
            
            # Longer sleep to reduce CPU load
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error in face monitoring: {e}")
            # Longer sleep on error to prevent rapid retries
            time.sleep(2)

def parse_time_duration(text):
    """Parse time duration from text like '5 minutes', '10 mins', '2 hours'."""
    text_lower = text.lower()
    
    # Extract number
    import re
    numbers = re.findall(r'\d+', text)
    if not numbers:
        return None
    
    duration = int(numbers[0])
    
    # Determine unit
    if 'hour' in text_lower:
        return duration * 3600  # seconds
    elif 'min' in text_lower:
        return duration * 60  # seconds
    elif 'sec' in text_lower:
        return duration
    else:
        # Default to minutes if no unit specified
        return duration * 60

def is_reminder_command(text):
    """Check if the text is a reminder-related command."""
    text_lower = text.lower()
    
    reminder_triggers = ['remind me', 'reminder', 'set a reminder', 'remind', 
                        'alert me', 'notify me']
    
    for trigger in reminder_triggers:
        if trigger in text_lower:
            return True
    
    return False

def save_owner_face(frame):
    """Save owner's face encoding."""
    global owner_face_encoding
    try:
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if not face_locations:
            print("❌ No face detected in frame")
            return False
        
        if len(face_locations) > 1:
            print("⚠️ Multiple faces detected, using the largest one")
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        if face_encodings:
            owner_face_encoding = face_encodings[0]
            
            # Save to file
            with open(FACE_DATA_FILE, 'wb') as f:
                pickle.dump(owner_face_encoding, f)
            
            print("✅ Owner face registered successfully")
            return True
        else:
            print("❌ Could not encode face")
            return False
    except Exception as e:
        print(f"❌ Error saving owner face: {e}")
        return False

def load_owner_face():
    """Load owner's face encoding from file."""
    global owner_face_encoding
    try:
        if os.path.exists(FACE_DATA_FILE):
            with open(FACE_DATA_FILE, 'rb') as f:
                owner_face_encoding = pickle.load(f)
            print("✅ Owner face loaded from file")
            return True
        else:
            print("⚠️ No owner face registered yet")
            return False
    except Exception as e:
        print(f"❌ Error loading owner face: {e}")
        return False

def check_for_faces(frame):
    """Check frame for faces and identify if owner or stranger - OPTIMIZED for speed."""
    global owner_face_encoding, last_alert_time
    
    if owner_face_encoding is None:
        return None
    
    try:
        # Resize frame for faster processing (smaller = faster)
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)  # Even smaller: 25%
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces with HOG (faster than CNN)
        face_locations = face_recognition.face_locations(rgb_frame, model="hog", number_of_times_to_upsample=0)
        
        if not face_locations:
            return None
        
        # Get face encodings - only for the first face (fastest)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)
        
        if not face_encodings:
            return None
        
        # Check only the first/closest face for speed
        face_encoding = face_encodings[0]
        
        # Calculate face distance (lower = more similar)
        face_distance = face_recognition.face_distance([owner_face_encoding], face_encoding)[0]
        
        # Threshold: 0.55
        if face_distance < 0.55:
            print(f"✓ Owner detected (distance: {face_distance:.2f})")
            return "owner"
        else:
            print(f"✗ Stranger detected (distance: {face_distance:.2f})")
            return "stranger"
    
    except Exception as e:
        print(f"❌ Error checking faces: {e}")
        return None

def is_leaving_home_command(text):
    """Check if user is leaving home."""
    text_lower = text.lower()
    triggers = ['i am leaving', 'i\'m leaving', 'leaving home', 'going out', 
                'i am going out', 'i\'m going out']
    
    for trigger in triggers:
        if trigger in text_lower:
            return True
    return False

def save_conversation(question, response):
    """Save question and response to JSON file."""
    try:
        # Load existing conversations
        conversations = []
        if os.path.exists(CONVERSATION_FILE):
            try:
                with open(CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Only parse if file has content
                        conversations = json.loads(content)
            except json.JSONDecodeError:
                print("⚠️ Conversation file corrupted, initializing fresh...")
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



def voice_listener(voice_queue):
    """Background thread for continuous voice listening."""
    global processing_flag, is_listening_active, activation_time, last_interaction_time  # Access global flags
    
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
                    # If assistant is processing a command or speaking, skip listening to avoid self-capture
                    if processing_flag or speaking_flag:
                        # when speaking, sleep shorter to resume quickly after speech ends
                        time.sleep(0.05 if speaking_flag else 0.1)
                        continue

                    # Use configured LISTEN_WINDOW to control how long Venom stays active
                    if is_listening_active and time.time() - last_interaction_time > LISTEN_WINDOW:
                        is_listening_active = False
                        print(f"⏰ Listening window closed after {LISTEN_WINDOW}s. Say 'hey venom' to activate again.")
                    
                    try:
                        print("🎤 Listening..." if is_listening_active else "💤 Waiting for 'hey venom'...")
                        # Listen for longer to capture complete sentences
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        print("🔊 Audio captured, recognizing...")
                        # Perform separate recognition for English and Tamil to support mixed-language speech
                        en_text = None
                        ta_text = None
                        try:
                            en_text = recognizer.recognize_google(audio, language='en-US')
                        except sr.UnknownValueError:
                            en_text = None
                        except sr.RequestError as e:
                            print(f"❌ Google API error during EN recognition: {e}")

                        try:
                            ta_text = recognizer.recognize_google(audio, language='ta-IN')
                        except sr.UnknownValueError:
                            ta_text = None
                        except sr.RequestError as e:
                            print(f"❌ Google API error during TA recognition: {e}")

                        # If neither recognized, try generic recognition as a last resort
                        text = None
                        if not en_text and not ta_text:
                            try:
                                text = recognizer.recognize_google(audio)
                            except sr.UnknownValueError:
                                raise
                            except sr.RequestError as e:
                                print(f"❌ Google API error during generic recognition: {e}")

                        # Merge results: prefer Tamil script preservation, include both if different
                        if ta_text and en_text:
                            # If both available and identical, use one
                            if ta_text.strip() == en_text.strip():
                                text = ta_text
                            else:
                                # Detect Tamil characters in ta_text
                                import re
                                tamil_char = re.search(r"[\u0B80-\u0BFF]", ta_text)
                                if tamil_char:
                                    # Preserve Tamil first then English
                                    text = f"{ta_text} | {en_text}"
                                else:
                                    # Fallback: prefer longer recognition
                                    text = ta_text if len(ta_text) > len(en_text) else en_text
                        elif ta_text:
                            text = ta_text
                        elif en_text:
                            text = en_text

                        if not text:
                            raise sr.UnknownValueError()

                        print(f"✅ Recognized: '{text}'")
                        text_lower = text.lower()

                        # Accept activation phrases in English and Tamil
                        activation_phrases = ["hey venom", "hi venom", 'வெனம்', 'ஹே வெனம்', 'ஹாய் வெனம்']
                        found_activation = any(phrase in text_lower for phrase in activation_phrases)
                        if found_activation:
                            is_listening_active = True
                            activation_time = time.time()
                            last_interaction_time = activation_time
                            print("🟢 Venom activated!")
                            # Remove activation phrases from the recognized text so we can process the remainder
                            import re
                            cleaned = text
                            for phrase in activation_phrases:
                                try:
                                    cleaned = re.sub(re.escape(phrase), '', cleaned, flags=re.IGNORECASE)
                                except Exception:
                                    cleaned = cleaned.replace(phrase, '')
                            cleaned = cleaned.strip()
                            if cleaned:
                                # treat the remaining text as the actual command
                                text = cleaned
                                text_lower = text.lower()
                                print(f"➡️ Activation phrase removed, processing remainder: '{text}'")
                                # fall through to processing the command below
                            else:
                                # No more content after activation -> wait for next speech
                                time.sleep(0.2)
                                continue
                        
                        # Only queue commands if listening is active
                        if is_listening_active and len(text.split()) > 0 and not processing_flag:
                            print(f"Voice: {text}")
                            voice_queue.put(text)
                            # Update last interaction to keep the listening window open
                            try:
                                last_interaction_time = time.time()
                            except Exception:
                                pass
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
    global processing_flag, is_listening_active, activation_time, last_interaction_time  # Access global flags
    
    print("DIY Camera Helper started. Your personal AI vision assistant.")
    # Start active so Venom is ready immediately on launch
    is_listening_active = True
    activation_time = time.time()
    try:
        last_interaction_time = activation_time
    except Exception:
        pass
    speak("Hey! I'm Venom, your AI assistant. Say 'hey venom' whenever you need me!")

    # Initialize reminders.json if it doesn't exist
    if not os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("✅ Reminders file initialized")

    # Start reminder checker thread (runs in background even in sleep mode)
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
    print("✅ Reminder system active")

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
    
    # Load owner face if registered
    load_owner_face()
    
    # Start face monitoring thread (runs in background even in sleep mode)
    if camera_available:
        face_thread = threading.Thread(target=monitor_faces_background, args=(cap,), daemon=True)
        face_thread.start()
        print("✅ Face monitoring system active")

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
                
                # Check if user is leaving home
                if is_leaving_home_command(text):
                    global home_security_active
                    
                    if camera_available and current_frame is not None:
                        # Register/update owner's face
                        if save_owner_face(current_frame):
                            home_security_active = True
                            answer = "Got it! Your face is registered. I'll watch for strangers while you're away. Stay safe!"
                            print("🔒 Security monitoring ACTIVATED - Watching for intruders...")
                        else:
                            answer = "I couldn't register your face. Please try again with better lighting."
                    else:
                        answer = "Camera not available. I can't enable security mode without seeing you."
                    
                    print(f"🤖 AI RESPONSE: {answer}")
                    save_conversation(text, answer)
                    speak(answer)
                    
                    # Reset flags
                    is_listening_active = True
                    activation_time = time.time()
                    processing_command = False
                    processing_flag = False
                    print("✅ Security mode activated. Ready for next command.")
                    continue
                
                # Check if this is a reminder command
                if is_reminder_command(text) or pending_reminder["waiting_for"] is not None:
                    text_lower = text.lower()
                    
                    # If we're waiting for task or time details
                    if pending_reminder["waiting_for"] == "task":
                        pending_reminder["task"] = text
                        pending_reminder["waiting_for"] = "time"
                        answer = "Got it! When should I remind you? Say something like '5 minutes' or '10 minutes'."
                        print(f"🤖 AI RESPONSE: {answer}")
                        speak(answer)
                        
                        # Reset flags but keep listening
                        is_listening_active = True
                        activation_time = time.time()
                        processing_command = False
                        processing_flag = False
                        continue
                    
                    elif pending_reminder["waiting_for"] == "time":
                        # Parse the time duration
                        duration_seconds = parse_time_duration(text)
                        if duration_seconds:
                            remind_time = datetime.now() + timedelta(seconds=duration_seconds)
                            task = pending_reminder["task"]
                            
                            if save_reminder(task, remind_time):
                                minutes = duration_seconds / 60
                                if minutes < 1:
                                    time_str = f"{duration_seconds} seconds"
                                elif minutes < 60:
                                    time_str = f"{int(minutes)} minutes"
                                else:
                                    time_str = f"{minutes/60:.1f} hours"
                                answer = f"Reminder set! I'll remind you about '{task}' in {time_str}."
                            else:
                                answer = "Sorry, I couldn't set the reminder."
                        else:
                            answer = "I didn't understand the time. Try saying '5 minutes' or '10 minutes'."
                        
                        # Clear pending reminder
                        pending_reminder["waiting_for"] = None
                        pending_reminder["task"] = None
                        
                        print(f"🤖 AI RESPONSE: {answer}")
                        save_conversation(text, answer)
                        speak(answer)
                        
                        # Reset flags
                        is_listening_active = True
                        activation_time = time.time()
                        processing_command = False
                        processing_flag = False
                        print("✅ Reminder set. Ready for next command.")
                        continue
                    
                    else:
                        # New reminder request
                        # Check if both task and time are in the same sentence
                        if 'to' in text_lower and any(word in text_lower for word in ['minute', 'min', 'hour', 'sec']):
                            # Try to extract task and time from single command
                            # e.g., "remind me to call John in 5 minutes"
                            duration_seconds = parse_time_duration(text)
                            if duration_seconds:
                                # Extract task (text before time expression)
                                import re
                                time_pattern = r'\s+in\s+\d+\s*(minute|min|hour|sec)'
                                parts = re.split(time_pattern, text_lower, flags=re.IGNORECASE)
                                
                                # Remove "remind me to" from the start
                                task = text_lower.replace('remind me to', '').replace('remind me', '').strip()
                                # Remove time part
                                task = re.sub(r'\s+in\s+\d+\s*(minutes?|mins?|hours?|secs?)\s*', '', task, flags=re.IGNORECASE).strip()
                                
                                if task:
                                    remind_time = datetime.now() + timedelta(seconds=duration_seconds)
                                    
                                    if save_reminder(task, remind_time):
                                        minutes = duration_seconds / 60
                                        if minutes < 1:
                                            time_str = f"{duration_seconds} seconds"
                                        elif minutes < 60:
                                            time_str = f"{int(minutes)} minutes"
                                        else:
                                            time_str = f"{minutes/60:.1f} hours"
                                        answer = f"Reminder set! I'll remind you to {task} in {time_str}."
                                    else:
                                        answer = "Sorry, I couldn't set the reminder."
                                    
                                    print(f"🤖 AI RESPONSE: {answer}")
                                    save_conversation(text, answer)
                                    speak(answer)
                                    
                                    # Reset flags
                                    is_listening_active = True
                                    activation_time = time.time()
                                    processing_command = False
                                    processing_flag = False
                                    print("✅ Reminder set. Ready for next command.")
                                    continue
                        
                        # If we reach here, ask for task
                        pending_reminder["waiting_for"] = "task"
                        answer = "Sure! What should I remind you about?"
                        print(f"🤖 AI RESPONSE: {answer}")
                        speak(answer)
                        
                        # Reset flags but keep listening
                        is_listening_active = True
                        activation_time = time.time()
                        processing_command = False
                        processing_flag = False
                        continue
                
                # Check if this is a memory command
                memory_cmd = is_memory_command(text)
                
                if memory_cmd == "save":
                    # Extract what to remember
                    text_lower = text.lower()
                    memory_text = ""
                    user_context = text  # Keep the original command as context
                    needs_camera = False
                    
                    # Smart extraction based on patterns
                    if 'my name is' in text_lower:
                        # Extract "Kavin" from "remember my name is Kavin"
                        parts = text_lower.split('my name is')
                        if len(parts) > 1:
                            memory_text = f"User's name is {parts[1].strip()}"
                        needs_camera = False  # Names don't need camera
                    elif 'my name as' in text_lower:
                        # Extract "Kavin" from "remember my name as Kavin"
                        parts = text_lower.split('my name as')
                        if len(parts) > 1:
                            memory_text = f"User's name is {parts[1].strip()}"
                        needs_camera = False  # Names don't need camera
                    elif 'my card number' in text_lower or 'card number' in text_lower:
                        # Extract card info
                        parts = text_lower.split('card number')
                        if len(parts) > 1:
                            memory_text = f"User's card number: {parts[1].replace('is', '').strip()}"
                        needs_camera = False  # Card numbers don't need camera
                    else:
                        # Check if this is about physical objects/locations (needs camera)
                        visual_keywords = ['keeping', 'kept', 'placed', 'put', 'this', 'that', 'here', 'there', 
                                         'mobile', 'phone', 'laptop', 'keys', 'wallet', 'bottle', 'cup', 'book',
                                         'where', 'location', 'position', 'bike', 'car', 'bag', 'watch']
                        needs_camera = any(keyword in text_lower for keyword in visual_keywords)
                        
                        # If text is very short or generic, use camera
                        text_without_trigger = text_lower.replace('remember', '').replace('i am', '').replace('this', '').replace('that', '').strip()
                        if len(text_without_trigger) < 5:  # Very short/vague command
                            needs_camera = True
                    
                    # If needs camera analysis or no memory text extracted, use AI to analyze the scene
                    if (needs_camera or not memory_text) and camera_available and current_frame is not None:
                        print("📸 Analyzing scene with camera for memory...")
                        frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        img.save(f"images/memory_{timestamp}.png")
                        print(f"💾 Image saved: images/memory_{timestamp}.png")
                        img = img.resize((256, 256))
                        img_b64 = encode_image(img)
                        
                        # Ask AI to analyze what user wants to remember with context
                        prompt = f"The user said: '{text}'. Analyze the image and describe what they want you to remember. Include what object it is and where it's located. Be specific and concise (1-2 sentences)."
                        memory_text = ask_ai(img_b64, prompt)
                        memory_text = memory_text.strip()
                    
                    # Save the memory
                    if memory_text and save_memory(memory_text, f"User said: {user_context}"):
                        answer = f"Got it! I'll remember that."
                    else:
                        answer = "Sorry, I couldn't save that memory."
                    
                    print(f"🤖 AI RESPONSE: {answer}")
                    save_conversation(text, answer)
                    speak(answer)
                    
                    # Reset flags
                    is_listening_active = True
                    activation_time = time.time()
                    processing_command = False
                    processing_flag = False
                    print("✅ Memory saved. Ready for next command.")
                    
                elif memory_cmd == "recall":
                    # Search memories and let AI respond naturally
                    relevant_memories = search_memories(text)
                    
                    if relevant_memories and camera_available and current_frame is not None:
                        # Use AI to generate natural response based on memories
                        print("📸 Processing frame with memory context...")
                        frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        img.save(f"images/captured_{timestamp}.png")
                        print(f"💾 Image saved: images/captured_{timestamp}.png")
                        
                        img = img.resize((256, 256))
                        img_b64 = encode_image(img)
                        
                        # Build memory context
                        memory_context = "\n\nRELEVANT MEMORIES:\n"
                        for mem in relevant_memories[:5]:
                            memory_context += f"- {mem.get('memory', '')}\n"
                        
                        # Let AI answer naturally using memory context
                        answer = ask_ai(img_b64, f"{text}{memory_context}\n\nAnswer the question naturally using these memories.")
                    elif relevant_memories:
                        # No camera, just use memories
                        memory_text = ", ".join([mem['memory'] for mem in relevant_memories[-3:]])
                        answer = f"Based on what I remember: {memory_text}"
                    else:
                        answer = "I don't have any memories matching that. Try asking me to remember something first!"
                    
                    print(f"🤖 AI RESPONSE: {answer}")
                    save_conversation(text, answer)
                    speak(answer)
                    
                    # Reset flags
                    is_listening_active = True
                    activation_time = time.time()
                    processing_command = False
                    processing_flag = False
                    print("✅ Memory recalled. Ready for next command.")
                    
                elif camera_available and current_frame is not None:
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
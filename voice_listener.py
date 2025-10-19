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
import requests
import json
from google import genai
import datetime

# Load environment variables from .env file
load_dotenv()

# Set API keys
google_api_key = os.getenv('GOOGLE_API_KEY', '')

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

# --- TTS: async wrapper ---
TTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), 'tts_cache')
if not os.path.exists(TTS_CACHE_DIR):
    try:
        os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    except Exception:
        pass

def _do_speak(text, save_audio=False):
    """Internal blocking TTS routine."""
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

                # If cached audio exists for this text, use it
                safe_name = "tts_" + str(abs(hash(text))) + ".mp3"
                cache_path = os.path.join(TTS_CACHE_DIR, safe_name)
                if os.path.exists(cache_path):
                    try:
                        subprocess.run(['afplay', cache_path], check=True)
                        print("✅ Spoken via ElevenLabs cache")
                        return
                    except Exception:
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
                    suffix = '.mp3'
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
        try:
            time.sleep(0.12)
            speaking_flag = False
        except Exception:
            pass

def speak(text, save_audio=False, async_play=True):
    """Public speak API. By default runs async to avoid blocking the main loop."""
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

# Global flag for graceful shutdown
shutdown_flag = False

# Global flag for processing state
processing_flag = False

# Global flag for voice activation
is_listening_active = False
activation_time = 0

# Ensure images directory exists for saving captured frames
IMAGES_DIR = "images"
if not os.path.exists(IMAGES_DIR):
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        print(f"✅ Created images directory: {IMAGES_DIR}")
    except Exception as e:
        print(f"⚠️ Could not create images directory '{IMAGES_DIR}': {e}")

def encode_image(image):
    """Encode PIL Image to base64 string, ensuring under 4MB limit."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    size_mb = len(buffer.getvalue()) / (1024 * 1024)
    if size_mb > 4:
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
        
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        client = genai.Client(api_key=google_api_key)
        
        full_prompt = f"{query}. Keep your response short, natural, and conversational - like talking to a friend. Maximum 2-3 sentences."
        
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
    global processing_flag, is_listening_active, activation_time, last_interaction_time
    
    mic_list = sr.Microphone.list_microphone_names()
    print(f"Available microphones: {mic_list}")
    
    mic_index = None
    for i, mic_name in enumerate(mic_list):
        if "microphone" in mic_name.lower() and "speakers" not in mic_name.lower():
            mic_index = i
            break
    
    if mic_index is None:
        mic_index = None
    
    print(f"Using microphone: {mic_list[mic_index] if mic_index is not None and mic_index < len(mic_list) else 'Default'}")
    
    while not shutdown_flag:
        try:
            with sr.Microphone(device_index=mic_index) as source:
                print("Initializing microphone...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                recognizer.energy_threshold = 400
                recognizer.dynamic_energy_threshold = False
                recognizer.pause_threshold = 1.0
                print("Voice listener ready...")
                
                while not shutdown_flag:
                    if processing_flag or speaking_flag:
                        time.sleep(0.05 if speaking_flag else 0.1)
                        continue

                    if is_listening_active and time.time() - last_interaction_time > LISTEN_WINDOW:
                        is_listening_active = False
                        print(f"⏰ Listening window closed after {LISTEN_WINDOW}s. Say 'hey venom' to activate again.")
                    
                    try:
                        print("🎤 Listening..." if is_listening_active else "💤 Waiting for 'hey venom'...")
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        print("🔊 Audio captured, recognizing...")
                        
                        if not is_listening_active:
                            # Try local recognition for wake word
                            try:
                                local_text = recognizer.recognize_sphinx(audio)
                                print(f"✅ Local recognized: '{local_text}'")
                                text_lower = local_text.lower()
                                
                                activation_phrases = ["hey venom", "hi venom", "venom"]
                                found_activation = any(phrase in text_lower for phrase in activation_phrases)
                                if found_activation:
                                    is_listening_active = True
                                    activation_time = time.time()
                                    last_interaction_time = activation_time
                                    print("🟢 Venom activated! 🔴 Listening for your command...")
                                    
                                    import re
                                    cleaned = local_text
                                    for phrase in activation_phrases:
                                        try:
                                            cleaned = re.sub(re.escape(phrase), '', cleaned, flags=re.IGNORECASE)
                                        except Exception:
                                            cleaned = cleaned.replace(phrase, '')
                                    cleaned = cleaned.strip()
                                    
                                    if cleaned and len(cleaned.split()) > 0:
                                        text = cleaned
                                        text_lower = text.lower()
                                        print(f"➡️ Activation + Command detected: '{text}'")
                                        if len(text.split()) > 0 and not processing_flag:
                                            print(f"Voice: {text}")
                                            voice_queue.put(text)
                                            try:
                                                last_interaction_time = time.time()
                                            except Exception:
                                                pass
                                            print(f"📤 Command queued: '{text}'")
                                            time.sleep(0.5)
                                    else:
                                        print("➡️ Pure activation - waiting for next command...")
                                        speak("Yes, I'm listening! What do you need?")
                                else:
                                    # Not activation, ignore
                                    pass
                            except sr.UnknownValueError:
                                pass
                            except Exception as e:
                                print(f"❌ Local recognition error: {e}")
                        else:
                            # Active, use Google API
                            en_text = None
                            try:
                                en_text = recognizer.recognize_google(audio, language='en-US')
                            except sr.UnknownValueError:
                                en_text = None
                            except sr.RequestError as e:
                                print(f"❌ Google API error during EN recognition: {e}")
                            
                            text = en_text
                            
                            if not text:
                                if is_listening_active:
                                    print("❌ Could not understand audio")
                                continue
                            
                            print(f"✅ Recognized: '{text}'")
                            text_lower = text.lower()
                            
                            if len(text.split()) > 0 and not processing_flag:
                                print(f"Voice: {text}")
                                voice_queue.put(text)
                                try:
                                    last_interaction_time = time.time()
                                except Exception:
                                    pass
                                print(f"📤 Command queued: '{text}'")
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
            time.sleep(2)

def is_command(text):
    """Check if the text is a valid command or question."""
    question_words = ['what', 'where', 'when', 'why', 'how', 'who', 'which', 'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does', 'did']
    action_words = ['tell', 'show', 'explain', 'describe', 'identify', 'find', 'look', 'search', 'check', 'see', 'read', 'scan']
    text_lower = text.lower()
    
    if "exit" in text_lower or "quit" in text_lower or "stop" in text_lower:
        return "exit"
    
    if "help me" in text_lower:
        return "help"
    
    if text_lower.endswith('?'):
        return "question"
    
    words = text_lower.split()
    if words and words[0] in question_words:
        return "question"
    
    if any(word in text_lower for word in action_words):
        return "question"
    
    if len(words) <= 3:
        return "question"
    
    return "question"

def main():
    """Main loop for Venom AI assistant with camera."""
    global processing_flag, is_listening_active, activation_time, last_interaction_time
    
    print("Venom AI Assistant started. Say 'hey venom' to activate.")
    is_listening_active = True
    activation_time = time.time()
    try:
        last_interaction_time = activation_time
    except Exception:
        pass
    speak("Hey! I'm Venom, your AI assistant. Say 'hey venom' whenever you need me!")

    # Initialize camera
    cap = cv2.VideoCapture(0)
    camera_available = False
    
    if cap.isOpened():
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
        cap = None

    # Start voice listening thread
    voice_queue = queue.Queue()
    voice_thread = threading.Thread(target=voice_listener, args=(voice_queue,), daemon=True)
    voice_thread.start()

    current_frame = None
    camera_error_count = 0
    processing_command = False

    while True:
        if camera_available and cap is not None:
            ret, frame = cap.read()
            if ret:
                camera_error_count = 0
                
                if processing_command:
                    cv2.putText(frame, "PROCESSING YOUR REQUEST...", (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, "Voice listening paused", (10, 60), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                cv2.imshow('Camera Feed - Say "hey venom" to activate', frame)
                current_frame = frame
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
            time.sleep(0.1)
        
        try:
            text = voice_queue.get_nowait()
            print(f"📥 Processing command: '{text}'")
            processing_command = True
            processing_flag = True
            
            if text.strip():
                print(f"🤖 COMMAND DETECTED: {text}")
                print("🔄 Processing your request... (voice listening paused)")
                
                if camera_available and current_frame is not None:
                    print("📸 Processing frame...")
                    frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    img.save(f"images/captured_{timestamp}.png")
                    print(f"💾 Image saved: images/captured_{timestamp}.png")
                    img = img.resize((256, 256))
                    img_b64 = encode_image(img)
                    print(f"Base64 length: {len(img_b64)}")
                    
                    try:
                        test_decode = base64.b64decode(img_b64)
                        print(f"Base64 decode successful, size: {len(test_decode)} bytes")
                    except Exception as e:
                        print(f"Base64 decode failed: {e}")
                    
                    print("📤 Image encoded, sending to Gemini...")
                    
                    answer = ask_ai(img_b64, text)
                    answer = answer.strip()
                    answer = answer.replace('\n', ' ').replace('  ', ' ')
                    print(f"🤖 AI RESPONSE: {answer}")
                    
                    speak(answer)
                    
                    is_listening_active = True
                    activation_time = time.time()
                    
                    processing_command = False
                    processing_flag = False
                    print("✅ Ready for next command within 10 seconds, or say 'hey venom' again.")
                else:
                    print("📝 Processing text-only query...")
                    answer = f"I heard: '{text}'. Since camera is not available, I can help with general advice. Please describe what you need help with in more detail."
                    print(f"🤖 AI RESPONSE: {answer}")
                    
                    speak(answer)
                    
                    processing_command = False
                    processing_flag = False
                    print("✅ Ready for next command. Say 'help me' or ask a question.")
                    
        except queue.Empty:
            pass
        
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
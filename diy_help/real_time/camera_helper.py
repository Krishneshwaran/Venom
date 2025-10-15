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

# Load environment variables from .env file
load_dotenv()

# Set API keys
groq_api_key = os.getenv('GROQ_API_KEY', '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')
openrouter_api_key = os.getenv('OPENROUTER_API_KEY', 'sk-or-v1-44a810c5dfef0a41eb42f63ace8b04a745f05dccbca00feab2ae47ed63c5b23')

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Adjust speech rate

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Global flag for graceful shutdown
shutdown_flag = False

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
    """Send image and query to Claude 3.5 Haiku model using direct API call."""
    print("=" * 50)
    print("SENDING TO OPENROUTER API WITH CLAUDE 3.5 SONNET...")
    print(f"Query: {query}")
    print("=" * 50)
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json"
    }
    
    # Claude vision format for OpenRouter
    data = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Look at this image from my camera. {query}. Please analyze what's visible and provide helpful, specific advice. Format your response to be natural and conversational, as if speaking to someone - keep it concise but informative."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    
    # Debug output to verify payload structure
    print(f"Payload content types: {[item.get('type') for item in data['messages'][0]['content']]}")
    print(f"Image URL preview: {data['messages'][0]['content'][1]['image_url']['url'][:50]}...")
    
    try:
        print(f"Sending request with image size: {len(image_base64)} characters")
        response = requests.post(url, headers=headers, json=data)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            return f"API Error: {response.status_code} - {response.text}"
            
        result = response.json()
        print("API response received")
        print(f"Full response: {json.dumps(result, indent=2)}")
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"API Error: {e}")
        return f"Error getting AI response: {str(e)}"

def speak(text, save_audio=False):
    """Convert text to speech and optionally save as audio file."""
    try:
        if save_audio:
            # Save to audio file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            audio_filename = f"audio_responses/response_{timestamp}.wav"
            
            # Create audio directory if it doesn't exist
            os.makedirs("audio_responses", exist_ok=True)
            
            # Save audio file
            engine.save_to_file(text, audio_filename)
            engine.runAndWait()
            
            print(f"🔊 Audio saved: {audio_filename}")
        else:
            # Just speak without saving
            engine.say(text)
            engine.runAndWait()
    except Exception as e:
        print(f"Speech error: {e}")
        # Fallback
        engine.say(text)
        engine.runAndWait()

def voice_listener(voice_queue):
    """Background thread for continuous voice listening."""
    mic_list = sr.Microphone.list_microphone_names()
    print(f"Available microphones: {mic_list}")
    
    # Try to find the best microphone
    mic_index = None
    for i, mic_name in enumerate(mic_list):
        if "microphone" in mic_name.lower() and "realtek" in mic_name.lower():
            mic_index = i
            break
    
    # If no specific mic found, use the default
    if mic_index is None and len(mic_list) > 0:
        mic_index = 1  # Often the second microphone is better than the first
    
    print(f"Using microphone: {mic_list[mic_index] if mic_index < len(mic_list) else 'Default'}")
    
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
                    try:
                        print("🎤 Listening for voice command...")
                        # Listen for longer to capture complete sentences
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        print("🔊 Audio captured, recognizing...")
                        text = recognizer.recognize_google(audio)
                        print(f"✅ Recognized: '{text}'")
                        if len(text.split()) > 0:  # Any speech with words
                            print(f"Voice: {text}")
                            voice_queue.put(text)
                            print(f"📤 Command queued: '{text}'")
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
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
    print("DIY Camera Helper started. Camera feed will show continuously.")
    speak("DIY Camera Helper ready. Ask me any question about what you see.")

    # Try to initialize camera
    cap = cv2.VideoCapture(0)
    camera_available = False
    
    if cap.isOpened():
        # Test camera by grabbing a frame
        ret, test_frame = cap.read()
        if ret:
            camera_available = True
            print("✅ Camera initialized successfully")
            speak("Camera ready")
        else:
            print("⚠️ Camera opened but cannot capture frames")
            cap.release()
    else:
        print("❌ Could not open camera. Please check camera permissions and connections.")
    
    if not camera_available:
        print("🔄 Starting in TEXT-ONLY mode (no camera)")
        speak("Camera not available. Starting in text-only mode. Say help me for assistance.")
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
                
                cv2.imshow('Camera Feed - Say "help me" for AI assistance', frame)
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
            # Text-only mode - just wait for commands
            time.sleep(0.1)  # Small delay to prevent busy loop
        
        # Check for voice commands
        try:
            text = voice_queue.get_nowait()
            print(f"📥 Processing command: '{text}'")
            processing_command = True  # Set processing flag
            
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
                    print("📤 Image encoded, sending to Claude 3.5 Haiku...")
                    
                    # Get AI response
                    answer = ask_ai(img_b64, text)
                    answer = answer.strip()
                    # Clean up response for better speech
                    answer = answer.replace('\n', ' ').replace('  ', ' ')
                    print(f"🤖 AI RESPONSE: {answer}")
                    speak(answer)  # Speak the response without saving
                    
                    processing_command = False  # Reset processing flag
                    print("✅ Ready for next command. Say 'help me' or ask a question.")
                else:
                    # Text-only response
                    print("📝 Processing text-only query...")
                    answer = f"I heard: '{text}'. Since camera is not available, I can help with general advice. Please describe what you need help with in more detail."
                    print(f"🤖 AI RESPONSE: {answer}")
                    speak(answer)  # Speak the response without saving
                    
                    processing_command = False  # Reset processing flag
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
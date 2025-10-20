"""
Voice Recognition Module
Handles speech recognition, voice activation, and command queuing
"""

import time
import threading
import queue
import speech_recognition as sr
from config import Config
from tts_module import speak, is_speaking
from utils import log_success, log_error, log_warning, log_info

# Import API server for frontend communication
try:
    from api_server import update_state
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    def update_state(*args, **kwargs):
        pass  # No-op if API not available

class VoiceListener:
    """Voice recognition and command processing"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.voice_queue = queue.Queue()
        self.is_listening_active = False
        self.activation_time = 0
        self.last_interaction_time = 0
        self.processing_flag = False
        self.shutdown_flag = False
        
        # Configure recognizer
        self.recognizer.energy_threshold = Config.ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.pause_threshold = Config.PAUSE_THRESHOLD
    
    def _find_microphone(self):
        """Find the best available microphone"""
        print("Using default microphone")
        return None
    
    def _recognize_speech(self, audio):
        """Recognize speech in multiple languages"""
        en_text = None
        ta_text = None
        
        # Try English
        try:
            en_text = self.recognizer.recognize_google(audio, language='en-US')
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            log_error(f"Google API error during EN recognition: {e}")
        
        # Try Tamil
        try:
            ta_text = self.recognizer.recognize_google(audio, language='ta-IN')
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            log_error(f"Google API error during TA recognition: {e}")
        
        # Fallback to generic
        if not en_text and not ta_text:
            try:
                return self.recognizer.recognize_google(audio)
            except sr.UnknownValueError:
                raise
            except sr.RequestError as e:
                log_error(f"Google API error during generic recognition: {e}")
                raise
        
        # Merge results
        if ta_text and en_text:
            if ta_text.strip() == en_text.strip():
                return ta_text
            else:
                import re
                if re.search(r"[\u0B80-\u0BFF]", ta_text):
                    return f"{ta_text} | {en_text}"
                else:
                    return ta_text if len(ta_text) > len(en_text) else en_text
        elif ta_text:
            return ta_text
        elif en_text:
            return en_text
        
        raise sr.UnknownValueError()
    
    def _check_activation(self, text):
        """Check if text contains activation phrase"""
        text_lower = text.lower()
        for phrase in Config.ACTIVATION_PHRASES:
            if phrase in text_lower:
                return True
        return False
    
    def _listen_loop(self):
        """Background listening loop"""
        mic_index = self._find_microphone()
        
        while not self.shutdown_flag:
            try:
                with sr.Microphone(device_index=mic_index) as source:
                    print("Initializing microphone...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    log_success("Voice listener ready...")
                    
                    while not self.shutdown_flag:
                        # Skip listening if processing or speaking
                        if self.processing_flag or is_speaking():
                            time.sleep(0.05 if is_speaking() else 0.1)
                            continue
                        
                        # Check listen window timeout
                        if self.is_listening_active and time.time() - self.last_interaction_time > Config.LISTEN_WINDOW:
                            self.is_listening_active = False
                            print(f"⏰ Listening window closed after {Config.LISTEN_WINDOW}s. Say 'hey venom' to activate again.")
                            
                            # Notify frontend - eyes closed
                            update_state(is_active=False, is_listening=False)
                        
                        try:
                            status = "🎤 Listening..." if self.is_listening_active else "💤 Waiting for 'hey venom'..."
                            print(status)
                            
                            audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=Config.PHRASE_TIME_LIMIT)
                            print("🔊 Audio captured, recognizing...")
                            
                            text = self._recognize_speech(audio)
                            
                            if not text:
                                raise sr.UnknownValueError()
                            
                            log_success(f"Recognized: '{text}'")
                            
                            # Check for activation
                            if self._check_activation(text):
                                self.is_listening_active = True
                                self.activation_time = time.time()
                                self.last_interaction_time = self.activation_time
                                print("🟢 Venom activated! 🔴 Listening...")
                                
                                # Notify frontend - eyes open
                                update_state(is_active=True, is_listening=True)
                                
                                speak("Yes, I'm listening!")
                                continue
                            
                            # Queue commands if active
                            if self.is_listening_active and len(text.split()) > 0 and not self.processing_flag:
                                print(f"Voice: {text}")
                                self.voice_queue.put(text)
                                self.last_interaction_time = time.time()
                                print(f"📤 Command queued: '{text}'")
                                time.sleep(0.5)
                        
                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            if self.is_listening_active:
                                log_error("Could not understand audio")
                            continue
                        except sr.RequestError as e:
                            log_error(f"Google API error: {e}")
                            continue
                        except Exception as e:
                            log_error(f"Voice recognition error: {e}")
                            continue
            
            except Exception as e:
                log_error(f"Microphone error: {e}")
                if mic_index is not None:
                    log_warning("Trying default microphone next time")
                    mic_index = None
                time.sleep(2)
    
    def start(self):
        """Start voice listening in background thread"""
        listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        listener_thread.start()
        log_success("Voice listener started")
    
    def get_command(self, block=False, timeout=None):
        """Get command from queue"""
        try:
            if block:
                return self.voice_queue.get(block=True, timeout=timeout)
            else:
                return self.voice_queue.get_nowait()
        except queue.Empty:
            return None
    
    def set_processing(self, is_processing):
        """Set processing flag to pause/resume listening"""
        self.processing_flag = is_processing
    
    def activate_listening(self):
        """Manually activate listening mode"""
        self.is_listening_active = True
        self.activation_time = time.time()
        self.last_interaction_time = self.activation_time
    
    def shutdown(self):
        """Shutdown voice listener"""
        self.shutdown_flag = True

# Global voice listener instance
_voice_listener = None

def get_voice_listener():
    """Get or create voice listener instance"""
    global _voice_listener
    if _voice_listener is None:
        _voice_listener = VoiceListener()
    return _voice_listener

def start_voice_listener():
    """Start the voice listener"""
    listener = get_voice_listener()
    listener.start()

def get_voice_command(block=False, timeout=None):
    """Get a voice command from the queue"""
    listener = get_voice_listener()
    return listener.get_command(block, timeout)

def set_processing_state(is_processing):
    """Set processing state"""
    listener = get_voice_listener()
    listener.set_processing(is_processing)
"""
Text-to-Speech Module
Handles all text-to-speech operations with multiple TTS engines
"""

import os
import time
import threading
import tempfile
import subprocess
import requests
import pyttsx3
from config import Config
from utils import ensure_directory, log_success, log_error, log_warning

class TTSEngine:
    """Text-to-Speech Engine with multiple backends"""
    
    def __init__(self):
        self.speaking_flag = False
        ensure_directory(Config.TTS_CACHE_DIR)
        self._init_pyttsx3()
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', Config.TTS_RATE)
            self.engine.setProperty('volume', Config.TTS_VOLUME)
            
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
                print(f"Using voice: {voices[0].name}")
        except Exception as e:
            log_error(f"Failed to initialize pyttsx3: {e}")
            self.engine = None
    
    def _speak_elevenlabs(self, text, save_audio=False):
        """Speak using ElevenLabs API"""
        if not Config.ELEVENLABS_API_KEY or not Config.ELEVENLABS_VOICE_ID:
            return False
        
        try:
            # Check cache first
            safe_name = "tts_" + str(abs(hash(text))) + ".mp3"
            cache_path = os.path.join(Config.TTS_CACHE_DIR, safe_name)
            
            if os.path.exists(cache_path):
                try:
                    subprocess.run(['afplay', cache_path], check=True)
                    log_success("Spoken via ElevenLabs cache")
                    return True
                except Exception:
                    pass
            
            # Make API request
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.ELEVENLABS_VOICE_ID}"
            headers = {
                'xi-api-key': Config.ELEVENLABS_API_KEY,
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
                write_path = cache_path if save_audio else None
                
                if write_path:
                    with open(write_path, 'wb') as f:
                        f.write(resp.content)
                    subprocess.run(['afplay', write_path], check=True)
                    log_success("Spoken via ElevenLabs (cached)")
                else:
                    with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as tmp:
                        tmp.write(resp.content)
                        tmp.flush()
                        subprocess.run(['afplay', tmp.name], check=True)
                        log_success("Spoken via ElevenLabs")
                return True
            else:
                log_warning(f"ElevenLabs TTS failed: {resp.status_code}")
                return False
        except Exception as e:
            log_warning(f"ElevenLabs TTS error: {e}")
            return False
    
    def _speak_macos_say(self, text):
        """Speak using macOS 'say' command"""
        try:
            text_escaped = text.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
            subprocess.run(['say', text_escaped], check=True)
            log_success("Audio playback complete (say)")
            return True
        except Exception as e:
            log_error(f"Speech error with 'say': {e}")
            return False
    
    def _speak_pyttsx3(self, text):
        """Speak using pyttsx3 engine"""
        if not self.engine:
            return False
        
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            self.engine.stop()
            log_success("Audio playback complete (pyttsx3)")
            return True
        except Exception as e:
            log_error(f"Failed to speak with pyttsx3: {e}")
            return False
    
    def _do_speak(self, text, save_audio=False):
        """Internal blocking TTS routine"""
        try:
            print(f"🔊 Speaking: {text[:50]}...")
            
            # Try ElevenLabs first
            if self._speak_elevenlabs(text, save_audio):
                return
            
            # Try macOS 'say' command
            if self._speak_macos_say(text):
                return
            
            # Fallback to pyttsx3
            self._speak_pyttsx3(text)
            
        except Exception as e:
            log_error(f"Unexpected error in speak(): {e}")
        finally:
            time.sleep(0.12)
            self.speaking_flag = False
    
    def speak(self, text, save_audio=False, async_play=True):
        """
        Public speak API
        
        Args:
            text: Text to speak
            save_audio: Whether to save audio to cache
            async_play: Whether to play asynchronously (non-blocking)
        """
        if async_play:
            self.speaking_flag = True
            t = threading.Thread(target=self._do_speak, args=(text, save_audio), daemon=True)
            t.start()
        else:
            self.speaking_flag = True
            self._do_speak(text, save_audio)
    
    def is_speaking(self):
        """Check if currently speaking"""
        return self.speaking_flag

# Global TTS instance
_tts_engine = None

def get_tts_engine():
    """Get or create TTS engine instance"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine

def speak(text, save_audio=False, async_play=True):
    """Convenience function to speak text"""
    engine = get_tts_engine()
    engine.speak(text, save_audio, async_play)

def is_speaking():
    """Check if TTS is currently speaking"""
    engine = get_tts_engine()
    return engine.is_speaking()
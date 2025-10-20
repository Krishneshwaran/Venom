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
import platform
from config import Config
from utils import ensure_directory, log_success, log_error, log_warning

# Import Windows-compatible audio player
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️  pygame not available. Install with: pip install pygame")

class TTSEngine:
    """Text-to-Speech Engine with multiple backends"""
    
    def __init__(self):
        self.speaking_flag = False
        ensure_directory(Config.TTS_CACHE_DIR)
        self._init_pyttsx3()
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine"""
        try:
            print("🎤 Initializing pyttsx3 TTS engine...")
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', Config.TTS_RATE)
            self.engine.setProperty('volume', Config.TTS_VOLUME)
            
            voices = self.engine.getProperty('voices')
            if voices:
                print(f"📢 Available voices: {len(voices)}")
                for i, voice in enumerate(voices[:3]):  # Show first 3 voices
                    print(f"  {i}: {voice.name}")
                self.engine.setProperty('voice', voices[0].id)
                print(f"✅ Using voice: {voices[0].name}")
            else:
                print("⚠️  No voices available!")
        except Exception as e:
            log_error(f"Failed to initialize pyttsx3: {e}")
            self.engine = None
    
    def _play_audio_file(self, file_path):
        """Play audio file using platform-specific method"""
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['afplay', file_path], check=True)
                return True
            elif platform.system() == 'Windows':
                if PYGAME_AVAILABLE:
                    # Use pygame for Windows - with proper initialization
                    try:
                        # Initialize pygame mixer with specific settings for better compatibility
                        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                        pygame.mixer.music.load(file_path)
                        pygame.mixer.music.set_volume(1.0)
                        pygame.mixer.music.play()
                        
                        # Wait for playback to finish
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                        time.sleep(0.1)  # Small delay to ensure cleanup
                        return True
                    except Exception as e:
                        log_error(f"Pygame playback error: {e}")
                        pygame.mixer.quit()
                        # Try fallback
                        os.system(f'start /min wmplayer "{file_path}" /close')
                        time.sleep(3)
                        return True
                else:
                    # Fallback to Windows Media Player command line
                    os.system(f'start /min wmplayer "{file_path}" /close')
                    # Wait a bit for playback (not perfect but works)
                    time.sleep(len(file_path) * 0.05 + 2)
                    return True
            else:
                # Linux - try common players
                for player in ['mpg123', 'ffplay', 'play']:
                    try:
                        subprocess.run([player, file_path], check=True, 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
                        return True
                    except FileNotFoundError:
                        continue
                return False
        except Exception as e:
            log_error(f"Audio playback error: {e}")
            return False
    
    def _speak_elevenlabs(self, text, save_audio=False):
        """Speak using ElevenLabs API"""
        if not Config.ELEVENLABS_API_KEY or not Config.ELEVENLABS_VOICE_ID:
            return False
        
        try:
            # Check cache first
            safe_name = "tts_" + str(abs(hash(text))) + ".mp3"
            cache_path = os.path.join(Config.TTS_CACHE_DIR, safe_name)
            
            if os.path.exists(cache_path):
                if self._play_audio_file(cache_path):
                    log_success("Spoken via ElevenLabs cache")
                    return True
            
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
                # Save to cache
                with open(cache_path, 'wb') as f:
                    f.write(resp.content)
                
                # Play the audio
                if self._play_audio_file(cache_path):
                    log_success("Spoken via ElevenLabs")
                    return True
                else:
                    log_warning("Failed to play ElevenLabs audio")
                    return False
            else:
                log_warning(f"ElevenLabs TTS failed: {resp.status_code}")
                return False
        except Exception as e:
            log_warning(f"ElevenLabs TTS error: {e}")
            return False
    
    def _speak_macos_say(self, text):
        """Speak using macOS 'say' command"""
        # Only available on macOS
        if platform.system() != 'Darwin':
            return False
        
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
        try:
            # Reinitialize engine for each speech on Windows (threading issue workaround)
            if platform.system() == 'Windows':
                engine = pyttsx3.init()
                engine.setProperty('rate', Config.TTS_RATE)
                engine.setProperty('volume', Config.TTS_VOLUME)
                
                # List available voices and use the first one
                voices = engine.getProperty('voices')
                if voices:
                    engine.setProperty('voice', voices[0].id)
                    print(f"🔊 Using voice: {voices[0].name}")
                
                print(f"🔊 Speaking with pyttsx3: {text[:50]}...")
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                log_success("Audio playback complete (pyttsx3)")
                return True
            else:
                # Use existing engine on non-Windows systems
                if not self.engine:
                    return False
                
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
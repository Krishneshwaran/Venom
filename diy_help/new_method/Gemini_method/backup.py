import os
import cv2
import base64
import pyaudio
import wave
import speech_recognition as sr
from google import genai
from google.genai import types
import threading
import time
import requests
import hashlib
import tempfile
import platform
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play as play_audio
import json
from datetime import datetime



class GeminiLiveChat:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.camera = cv2.VideoCapture(0)
        self.recognizer = sr.Recognizer()
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.audio_frames = []

    def capture_frame(self):
        ret, frame = self.camera.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer
        return None

    def record_audio(self, duration=5):
        print("🎤 Listening... (speak now)")

        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        frames = []
        for _ in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        temp_audio = "temp_audio.wav"
        wf = wave.open(temp_audio, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        return temp_audio

    def transcribe_audio(self, audio_file):
        try:
            with sr.AudioFile(audio_file) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data, language="ta-IN")
                return text
        except sr.UnknownValueError:
            print("❌ Could not understand Tamil audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
    
    def _get_conversation_context(self, max_records=5):
        """Load last few conversation records to provide context"""
        history_file = "conversation_history.json"
        context_text = ""
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                # Take last N records
                for record in history[-max_records:]:
                    context_text += f"பழைய உரையாடல்: பயனர்: {record['question']} \n Gemini: {record['response']}\n"
            except:
                pass
        return context_text
        


    def send_to_gemini(self, frame_buffer, question):
        """Send frame and question to Gemini with history context"""
        print(f"\n📤 Sending to Gemini: '{question}'")

        try:
            # Load last few messages for context
            conversation_context = self._get_conversation_context(max_records=5)

            system_prompt = (
                    "உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும் — நண்பரிடம் பேசுற மாதிரி. "
                    "மரியாதையா பேசணும், எப்போதும் தமிழிலேயே பதில் சொல்லணும் (அதிகபட்சம் 2-3 வாக்கியங்கள்). "
                    "குறிப்பாக 'நெய்பகம் இருக்கா?', 'அது எங்கு வச்சது என்று தெரியுமா?' போன்ற கேள்விகள் வந்தால் மட்டும் "
                    "பழைய தொடர்புகளைப் பார்த்து பதில் தயாரிக்கவும்.\n\n"
                f"{conversation_context}"
            )

            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=system_prompt),
                            types.Part.from_bytes(
                                data=frame_buffer.tobytes(),
                                mime_type="image/jpeg"
                            ),
                            types.Part.from_text(text=question)
                        ]
                    )
                ]
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    def send_to_gemini_without_history(self, frame_buffer, question):
        """Send frame and question to Gemini WITHOUT history context"""
        print(f"\n📤 Sending to Gemini (no history): '{question}'")

        try:
            system_prompt = (
                "உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும் — நண்பரிடம் பேசுற மாதிரி. "
                "மரியாதையா பேசணும், எப்போதும் தமிழிலேயே பதில் சொல்லணும் (அதிகபட்சம் 2-3 வாக்கியங்கள்)."
            )

            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=system_prompt),
                            types.Part.from_bytes(
                                data=frame_buffer.tobytes(),
                                mime_type="image/jpeg"
                            ),
                            types.Part.from_text(text=question)
                        ]
                    )
                ]
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

    
    def _save_conversation(self, question, response):
        """Append the conversation to a JSON history file"""
        history_file = "conversation_history.json"
        record = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response
        }

        # Load existing history
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []
        else:
            history = []

        history.append(record)

        # Save back
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


    def _speak_pyttsx3(self, text):
        """Speak using pyttsx3 engine (Windows-safe version)"""
        try:
            if platform.system() == 'Windows':
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                engine.setProperty('volume', 1.0)
                voices = engine.getProperty('voices')
                if voices:
                    engine.setProperty('voice', voices[0].id)
                    print(f"🔊 Using voice: {voices[0].name}")

                print(f"🔊 Speaking with pyttsx3: {text[:50]}...")
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                time.sleep(0.2)
                print("✅ Audio playback complete (pyttsx3)")
                return True
            else:
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                time.sleep(0.2)
                print("✅ Audio playback complete (pyttsx3)")
                return True
        except Exception as e:
            print(f"❌ pyttsx3 speak error: {e}")
            return False

    def _speak_elevenlabs(self, text, save_audio=False):
        voice_id = "g5YdRy5HTKnrMIqKRe98"
        api_key = self.eleven_api_key

        if not api_key or not voice_id:
            print("⚠️ Missing ElevenLabs API key or voice ID")
            return False

        try:
            cache_dir = os.path.join(os.getcwd(), "tts_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, "tts_" + str(abs(hash(text))) + ".mp3")

            if os.path.exists(cache_path):
                audio = AudioSegment.from_file(cache_path, format="mp3")
                play_audio(audio)
                print("🔊 Played from cache (ElevenLabs)")
                return True

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                with open(cache_path, "wb") as f:
                    f.write(resp.content)
                audio = AudioSegment.from_file(cache_path, format="mp3")
                play_audio(audio)
                print("✅ Spoken via ElevenLabs TTS")
                return True
            else:
                print(f"❌ ElevenLabs TTS failed: {resp.status_code}")
                return False

        except Exception as e:
            print(f"⚠️ ElevenLabs TTS error: {e}")
            print("➡️ Switching to pyttsx3 fallback...")
            return self._speak_pyttsx3(text)

    def voice_video_chat(self):
        print("=" * 60)
        print("🎥 Gemini Voice + Video Chat")
        print("=" * 60)
        print("Press 'SPACE' to ask with conversation history")
        print("Press 'c' to ask WITHOUT conversation history")
        print("Press 'q' to quit")
        print("=" * 60)

        while True:
            ret, frame = self.camera.read()
            if not ret:
                break

            cv2.imshow('Gemini Video Chat', frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n👋 Exiting...")
                break

            elif key == ord(' '):
                frame_buffer = self.capture_frame()
                if frame_buffer is None:
                    print("❌ Failed to capture frame")
                    continue

                audio_file = self.record_audio(duration=5)
                print("🔄 Transcribing...")
                question = self.transcribe_audio(audio_file)

                if question:
                    print(f"✅ You asked: '{question}'")
                    response = self.send_to_gemini(frame_buffer, question)

                    print("\n" + "=" * 60)
                    print("🤖 Gemini Response (with history):")
                    print("-" * 60)
                    print(response)
                    print("=" * 60 + "\n")

                    # Save conversation history
                    self._save_conversation(question, response)

                    # Speak response
                    if not self._speak_elevenlabs(response):
                        self._speak_pyttsx3(response)

            elif key == ord('c'):
                frame_buffer = self.capture_frame()
                if frame_buffer is None:
                    print("❌ Failed to capture frame")
                    continue

                audio_file = self.record_audio(duration=5)
                print("🔄 Transcribing...")
                question = self.transcribe_audio(audio_file)

                if question:
                    print(f"✅ You asked: '{question}'")
                    response = self.send_to_gemini_without_history(frame_buffer, question)

                    print("\n" + "=" * 60)
                    print("🤖 Gemini Response (no history):")
                    print("-" * 60)
                    print(response)
                    print("=" * 60 + "\n")

                    # Save conversation history
                    self._save_conversation(question, response)

                    # Speak response
                    if not self._speak_elevenlabs(response):
                        self._speak_pyttsx3(response)

        self.cleanup()

    def cleanup(self):
        self.camera.release()
        cv2.destroyAllWindows()
        self.audio.terminate()
        print("✅ Resources cleaned up")


if __name__ == "__main__":
    gemini_api_key = "AIzaSyA2j-XcTTHATJkiv3rfOIsv05-Pwyhu0pU"
    eleven_api_key = "sk_407c22ae03988e1b1201c291358a1ed05dac792258acd03a"

    chat = GeminiLiveChat(api_key=gemini_api_key)
    chat.eleven_api_key = eleven_api_key
    chat.voice_video_chat()

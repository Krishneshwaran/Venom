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
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure



class GeminiLiveChat:
    def __init__(self, api_key, mongo_uri=None):
        self.client = genai.Client(api_key=api_key)
        self.camera = cv2.VideoCapture(0)
        self.recognizer = sr.Recognizer()
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.audio_frames = []

        # MongoDB setup
        self.mongo_client = None
        self.db = None
        self.state_collection = None
        if mongo_uri:
            self._setup_mongodb(mongo_uri)

    def _setup_mongodb(self, mongo_uri):
        """Initialize MongoDB connection"""
        try:
            self.mongo_client = MongoClient(mongo_uri)
            # Test connection
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client['venom']
            self.state_collection = self.db['state']
            print("✅ Connected to MongoDB Atlas")
            # Initialize state as inactive
            self._update_state(is_active=False)
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
        except Exception as e:
            print(f"❌ MongoDB setup error: {e}")

    def _update_state(self, is_active):
        """Update the is_active state in MongoDB"""
        if self.state_collection is None:
            return

        try:
            # Update or insert the state document with only is_active
            state_data = {
                "is_active": is_active
            }

            self.state_collection.update_one(
                {},  # Match any document (or first one)
                {"$set": state_data},
                upsert=True  # Create if doesn't exist
            )
            status = "active" if is_active else "inactive"
            print(f"✅ MongoDB state updated: {status}")
        except Exception as e:
            print(f"❌ Failed to update MongoDB state: {e}")

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

    def _get_memory_data(self):
        """Load memory.json for static knowledge base"""
        memory_file = "memory.json"
        memory_text = ""
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    memory = json.load(f)
                # Format the memory data as readable text
                memory_text = json.dumps(memory, ensure_ascii=False, indent=2)
            except:
                pass
        return memory_text



    def send_to_gemini(self, frame_buffer, question):
        """Send frame and question to Gemini with history context"""
        print(f"\n📤 Sending to Gemini: '{question}'")

        try:
            # Load last few messages for context
            conversation_context = self._get_conversation_context(max_records=5)

            system_prompt = (
                    "உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும் — நண்பரிடம் பேசுற மாதிரி. "
                    "மரியாதையா பேசணும், எப்போதும் தமிழிலேயே பதில் சொல்லணும் (அதிகபட்சம் 5-6 வாக்கியங்கள்). "
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
            # Load memory data for reference when needed
            memory_data = self._get_memory_data()

            system_prompt = (
                "உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும் — நண்பரிடம் பேசுற மாதிரி. "
                "மரியாதையா பேசணும், எப்போதும் தமிழிலேயே பதில் சொல்லணும் (அதிகபட்சம் 5-6 வாக்கியங்கள்). "
                "\n\n**முக்கிய வழிமுறைகள்:**\n"
                "1. யூசர் Vijay TV நிகழ்ச்சி, Pitch It On நிகழ்ச்சி, நிகழ்ச்சியில் பங்கேற்பது பற்றி, "
                "எதற்காக பங்கேற்க வேண்டும், நிகழ்ச்சியின் விவரங்கள் போன்ற கேள்விகள் கேட்டா — "
                "கீழே உள்ள மெமரி டேட்டாவை பார்த்து தெளிவாக பதில் சொல்லணும்.\n"
                "2. யூசர் 'பக்கத்துல இருக்குற கடை', 'சுற்றுலா இடங்கள்', 'அருகில் என்ன இருக்கு' கேட்டா — "
                "இணையத்திலிருந்து தேடி உடனே சொல்லணும்.\n"
                "3. யூசர் ஊர்ல இருந்து இன்னொரு ஊருக்கு போக எவ்வளவு நேரம் ஆகும், ஆட்டோ/கார் கட்டணம் என்ன கேட்டா — "
                "இணையத்திலிருந்து சரியான நேரமும் விலையும் தேடி தமிழில் சொல்லணும். மறுத்துச் சொல்லக்கூடாது.\n"
                "4. எப்பவும் உதவியா இருக்கணும், 'தெரியாது' 'தேடி சொல்றேன்' மாதிரி பதில் தர கூடாது.\n\n"
                "**மெமரி டேட்டா (நிகழ்ச்சி தகவல்களுக்காக):**\n"
                f"{memory_data}\n"
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
                # Set MongoDB state to active when SPACE is pressed
                self._update_state(is_active=True)

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
                # Set MongoDB state to active when 'c' is pressed
                self._update_state(is_active=True)

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
        # Set MongoDB state to inactive before cleanup
        self._update_state(is_active=False)

        self.camera.release()
        cv2.destroyAllWindows()
        self.audio.terminate()

        # Close MongoDB connection
        if self.mongo_client:
            self.mongo_client.close()
            print("✅ MongoDB connection closed")

        print("✅ Resources cleaned up")


if __name__ == "__main__":
    gemini_api_key = "AIzaSyCR-twDtb6rlgfFA66E76VJlq2eGJzGNMc"
    eleven_api_key = "sk_407c22ae03988e1b1201c291358a1ed05dac792258acd03a"
    mongo_uri = "mongodb+srv://krish:krish@study.po9dv.mongodb.net/"

    chat = GeminiLiveChat(api_key=gemini_api_key, mongo_uri=mongo_uri)
    chat.eleven_api_key = eleven_api_key
    chat.voice_video_chat()

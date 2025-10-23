import os
import cv2
import base64
import asyncio
import pyaudio
import websockets
import json
from google import genai
from google.genai import types

# IMPORTANT: Use environment variable for API key
API_KEY = os.getenv('GOOGLE_API_KEY')  # Set this in your environment
# For now, since you shared it: API_KEY = "your-NEW-key-here"

class GeminiLiveChat:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.camera = cv2.VideoCapture(0)
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.audio_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
    
    def capture_frame(self):
        """Capture a frame from webcam"""
        ret, frame = self.camera.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            return base64.b64encode(buffer).decode('utf-8')
        return None
    
    async def audio_chat_session(self):
        """Real-time audio conversation with Gemini"""
        config = {
            "generation_config": {
                "response_modalities": ["AUDIO"]
            }
        }
        
        async with self.client.aio.live.connect(
            model="gemini-2.0-flash-exp",
            config=config
        ) as session:
            
            # Audio input task
            async def send_audio():
                while True:
                    audio_data = self.audio_stream.read(1024, exception_on_overflow=False)
                    await session.send(audio_data, mime_type="audio/pcm")
                    await asyncio.sleep(0.01)
            
            # Receive responses
            async def receive_responses():
                async for response in session.receive():
                    if response.data:
                        # Play audio response
                        print("Received audio response")
                        # You can play the audio here
            
            await asyncio.gather(send_audio(), receive_responses())
    
    def video_chat_with_frames(self):
        """Chat with periodic video frames (not true streaming)"""
        print("Starting video chat. Press 'q' to quit, 's' to send frame")
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                break
            
            cv2.imshow('Gemini Video Chat', frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Capture and send frame to Gemini
                _, buffer = cv2.imencode('.jpg', frame)
                jpg_base64 = base64.b64encode(buffer).decode('utf-8')
                
                prompt = input("What do you want to ask about this frame? ")
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_bytes(
                                    data=buffer.tobytes(),
                                    mime_type="image/jpeg"
                                ),
                                types.Part.from_text(text=prompt)
                            ]
                        )
                    ]
                )
                print(f"\nGemini: {response.text}\n")
        
        self.cleanup()
    
    def cleanup(self):
        """Release resources"""
        self.camera.release()
        cv2.destroyAllWindows()
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.audio.terminate()

# Usage
if __name__ == "__main__":
    # SECURITY: Get new API key and use environment variable
    api_key = "AIzaSyA2j-XcTTHATJkiv3rfOIsv05-Pwyhu0pU"  # Replace after revoking the old one
    
    chat = GeminiLiveChat(api_key)
    
    # Option 1: Video frames with text
    chat.video_chat_with_frames()
    
    # Option 2: Real-time audio (uncomment to use)
    # asyncio.run(chat.audio_chat_session())
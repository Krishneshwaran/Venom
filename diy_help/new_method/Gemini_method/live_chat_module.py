"""
Live Chat Module
Handles real-time video and audio chat using Google Gemini 2.0 Flash
Optimized for minimal latency and efficient processing
"""

import asyncio
import base64
import io
import cv2
import pyaudio
import numpy as np
from PIL import Image
from google import genai
from google.genai import types
from config import Config
from utils import log_success, log_error, log_info
from conversation_module import save_conversation


class LiveChatEngine:
    """Real-time video and audio chat engine using Gemini 2.0 Flash"""
    
    def __init__(self):
        self.client = None
        self.camera = None
        self.audio = None
        self.audio_stream = None
        self.is_running = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Gemini client"""
        try:
            if Config.GOOGLE_API_KEY:
                self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
                log_success("Gemini Live Chat client initialized")
            else:
                log_error("Google API key not found")
        except Exception as e:
            log_error(f"Failed to initialize client: {e}")
    
    def start_camera(self):
        """Initialize webcam"""
        try:
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            log_success("Camera started")
            return True
        except Exception as e:
            log_error(f"Failed to start camera: {e}")
            return False
    
    def start_audio(self):
        """Initialize audio input"""
        try:
            self.audio = pyaudio.PyAudio()
            self.audio_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=512,
                stream_callback=None
            )
            log_success("Audio started")
            return True
        except Exception as e:
            log_error(f"Failed to start audio: {e}")
            return False
    
    def capture_frame_optimized(self):
        """Capture and encode frame efficiently"""
        try:
            ret, frame = self.camera.read()
            if not ret:
                return None
            
            # Resize for faster processing
            frame_resized = cv2.resize(frame, (320, 240))
            
            # Encode as JPEG with quality optimization
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            _, buffer = cv2.imencode('.jpg', frame_resized, encode_param)
            
            return buffer.tobytes(), frame  # Return both encoded and original
        except Exception as e:
            log_error(f"Frame capture error: {e}")
            return None, None
    
    async def live_multimodal_session(self, mode="video"):
        """
        Start live multimodal session with Gemini
        
        Args:
            mode: "video", "audio", or "both"
        """
        if not self.client:
            log_error("Client not initialized")
            return
        
        # Initialize camera and audio before starting session
        if mode in ["video", "both"]:
            if not self.start_camera():
                log_error("Failed to start camera")
                return
        
        if mode in ["audio", "both"]:
            if not self.start_audio():
                log_error("Failed to start audio")
                return
        
        self.is_running = True
        
        try:
            # Configure for live session
            config = types.LiveConnectConfig(
                response_modalities=["TEXT", "AUDIO"] if mode in ["audio", "both"] else ["TEXT"],
            )
            
            log_info(f"Starting live {mode} session...")
            
            async with self.client.aio.live.connect(
                model="gemini-2.0-flash-exp",
                config=config
            ) as session:
                
                log_success("Live session connected!")
                
                # Start tasks based on mode
                tasks = []
                
                if mode in ["video", "both"]:
                    tasks.append(self._video_sender(session))
                
                if mode in ["audio", "both"]:
                    tasks.append(self._audio_sender(session))
                
                tasks.append(self._response_receiver(session))
                
                await asyncio.gather(*tasks)
        
        except Exception as e:
            log_error(f"Live session error: {e}")
        finally:
            self.is_running = False
            self.cleanup()
    
    async def _video_sender(self, session):
        """Send video frames to Gemini"""
        frame_count = 0
        send_interval = 2  # Send every 2 seconds for efficiency
        
        while self.is_running:
            try:
                encoded_frame, display_frame = self.capture_frame_optimized()
                
                if encoded_frame and frame_count % (30 * send_interval) == 0:
                    # Send frame to Gemini
                    await session.send(
                        types.LiveClientContent(
                            turns=[
                                types.LiveClientTurn(
                                    parts=[
                                        types.Part.from_bytes(
                                            data=encoded_frame,
                                            mime_type="image/jpeg"
                                        )
                                    ]
                                )
                            ]
                        )
                    )
                    log_info("Frame sent to Gemini")
                
                # Display frame
                if display_frame is not None:
                    cv2.putText(display_frame, "Live Chat Active", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow('Gemini Live Chat', display_frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.is_running = False
                        break
                
                frame_count += 1
                await asyncio.sleep(0.033)  # ~30 FPS
            
            except Exception as e:
                log_error(f"Video sender error: {e}")
                await asyncio.sleep(0.1)
    
    async def _audio_sender(self, session):
        """Send audio to Gemini"""
        while self.is_running:
            try:
                audio_data = self.audio_stream.read(512, exception_on_overflow=False)
                
                await session.send(
                    types.LiveClientContent(
                        turns=[
                            types.LiveClientTurn(
                                parts=[
                                    types.Part.from_bytes(
                                        data=audio_data,
                                        mime_type="audio/pcm"
                                    )
                                ]
                            )
                        ]
                    )
                )
                
                await asyncio.sleep(0.01)
            
            except Exception as e:
                log_error(f"Audio sender error: {e}")
                await asyncio.sleep(0.1)
    
    async def _response_receiver(self, session):
        """Receive and process responses from Gemini"""
        while self.is_running:
            try:
                async for response in session.receive():
                    if response.text:
                        log_success(f"Gemini: {response.text}")
                        print(f"\n🤖 Gemini: {response.text}\n")
                    
                    if response.data:
                        # Audio response received
                        log_info("Received audio response")
                        # You can play audio here if needed
            
            except Exception as e:
                log_error(f"Response receiver error: {e}")
                await asyncio.sleep(0.1)
    
    async def optimized_video_qa(self, tamil_mode=True):
        """
        Optimized Q&A with live video feed
        User can ask questions via keyboard, camera continuously runs
        """
        if not self.start_camera():
            return
        
        self.is_running = True
        log_info("Starting optimized video Q&A mode")
        print("\n🎥 Camera is live! Type your question and press Enter.")
        print("Commands: 'q' to quit, 'c' to clear screen\n")
        
        try:
            # Start display task
            display_task = asyncio.create_task(self._display_video())
            
            while self.is_running:
                # Get user input asynchronously
                query = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Your question: "
                )
                
                if query.lower() in ['q', 'quit', 'exit']:
                    self.is_running = False
                    break
                
                if query.lower() == 'c':
                    print("\n" * 50)
                    continue
                
                if not query.strip():
                    continue
                
                # Capture current frame
                encoded_frame, _ = self.capture_frame_optimized()
                
                if encoded_frame:
                    # Send to Gemini
                    response = await self._quick_image_query(encoded_frame, query, tamil_mode)
                    print(f"\n🤖 {response}\n")
                    
                    # Save conversation
                    save_conversation(query, response)
        
        except KeyboardInterrupt:
            log_info("Interrupted by user")
        finally:
            self.is_running = False
            display_task.cancel()
            self.cleanup()
    
    async def _display_video(self):
        """Continuously display video feed"""
        while self.is_running:
            try:
                _, display_frame = self.capture_frame_optimized()
                if display_frame is not None:
                    cv2.putText(display_frame, "Q&A Mode - Type below", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow('Live Feed', display_frame)
                    cv2.waitKey(1)
                
                await asyncio.sleep(0.033)
            except Exception as e:
                log_error(f"Display error: {e}")
    
    async def _quick_image_query(self, image_bytes, query, tamil_mode=True):
        """Quick image query without full session"""
        try:
            # Get conversation history
            from conversation_module import get_conversation_history
            history = get_conversation_history(limit=3)
            history_text = ""
            if history:
                history_text = "\n\nRecent context:\n"
                for conv in history[-3:]:
                    history_text += f"Q: {conv['question'][:50]}...\nA: {conv['response'][:50]}...\n"
            
            # Build prompt
            if tamil_mode:
                full_prompt = f"{query}{history_text}. உன் பதில் சுருக்கமாகவும் தெளிவாகவும் தமிழில் இருக்கட்டும் (2-3 வாக்கியங்கள்)."
            else:
                full_prompt = f"{query}{history_text}. Keep response brief and clear (2-3 sentences)."
            
            # Make async API call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        types.Part.from_text(text=full_prompt)
                    ]
                )
            )
            
            return response.text
        
        except Exception as e:
            log_error(f"Quick query error: {e}")
            return f"Error: {str(e)}"
    
    def cleanup(self):
        """Release all resources"""
        try:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
            if self.audio_stream is not None:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            if self.audio is not None:
                self.audio.terminate()
                self.audio = None
            cv2.destroyAllWindows()
            log_success("Resources cleaned up")
        except Exception as e:
            log_error(f"Cleanup error: {e}")


# Global instance
_live_chat_engine = None

def get_live_chat_engine():
    """Get or create live chat engine instance"""
    global _live_chat_engine
    if _live_chat_engine is None:
        _live_chat_engine = LiveChatEngine()
    return _live_chat_engine


async def start_live_video_chat():
    """Start live video chat session"""
    engine = get_live_chat_engine()
    await engine.live_multimodal_session(mode="video")


async def start_live_audio_chat():
    """Start live audio chat session"""
    engine = get_live_chat_engine()
    await engine.live_multimodal_session(mode="audio")


async def start_live_multimodal_chat():
    """Start both video and audio chat"""
    engine = get_live_chat_engine()
    await engine.live_multimodal_session(mode="both")


async def start_optimized_qa():
    """Start optimized Q&A mode (recommended for your use case)"""
    engine = get_live_chat_engine()
    await engine.optimized_video_qa(tamil_mode=True)
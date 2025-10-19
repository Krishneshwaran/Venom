"""
Venom AI Assistant - FastAPI Application (macOS Compatible)
REST API wrapper - Run video_viewer.py separately for camera feed
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import base64
import io
import cv2
from PIL import Image
from datetime import datetime, timedelta
import uvicorn

# Import all modules
from config import Config
from utils import log_success, log_error, log_info
from tts_module import speak, get_tts_engine
from vision_module import get_vision_system
from ai_module import ask_ai, ask_ai_text
from memory_module import (
    save_memory, search_memories, is_memory_command,
    extract_memory_content, needs_visual_context, get_memory_system
)
from reminder_module import (
    save_reminder, parse_time_duration, is_reminder_command,
    extract_reminder_parts, get_reminder_system, start_reminder_system
)
from security_module import (
    save_owner_face, activate_security, get_security_system,
    is_leaving_home_command
)
from conversation_module import (
    save_conversation, get_conversation_history,
    clear_conversation_history, is_command, classify_intent
)

# Initialize FastAPI app
app = FastAPI(
    title="Venom AI Assistant API",
    description="REST API for Venom AI Assistant - Use video_viewer.py for camera display",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TextRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

class MemorySaveRequest(BaseModel):
    memory_text: str
    context: Optional[str] = ""
    image_base64: Optional[str] = None

class MemorySearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

class ReminderRequest(BaseModel):
    task: str
    time_description: str

class AIQueryRequest(BaseModel):
    query: str
    image_base64: Optional[str] = None
    include_memory_context: Optional[bool] = True

class ConversationEntry(BaseModel):
    question: str
    response: str

class TTSRequest(BaseModel):
    text: str
    save_audio: Optional[bool] = False

class SecurityActivateRequest(BaseModel):
    image_base64: str

class AudioTestRequest(BaseModel):
    test_message: str = "Testing audio capture"

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize systems on startup"""
    log_info("=" * 60)
    log_info("STARTING VENOM AI ASSISTANT API")
    log_info("=" * 60)
    
    # Start reminder system
    start_reminder_system()
    log_success("Reminder system started")
    
    # Initialize vision system
    vision = get_vision_system()
    camera_init = vision.initialize_camera()
    
    if camera_init:
        log_success("Camera initialized successfully")
        log_info("💡 TIP: Run 'python video_viewer.py' to see camera feed")
    else:
        log_error("Camera initialization failed")
    
    log_success("Venom AI Assistant API Ready!")
    log_info("=" * 60)
    log_info("ENDPOINTS:")
    log_info("  - Health: http://localhost:8000/health")
    log_info("  - Docs: http://localhost:8000/docs")
    log_info("  - Debug: http://localhost:8000/debug/system-info")
    log_info("=" * 60)
    log_info("📹 For video output, run in separate terminal:")
    log_info("     python video_viewer.py")
    log_info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    log_info("Shutting down...")
    
    vision = get_vision_system()
    vision.release_camera()
    
    log_success("Shutdown complete")

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Venom AI Assistant API",
        "version": "1.0.0",
        "message": "Run video_viewer.py for camera feed",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    vision = get_vision_system()
    security = get_security_system()
    
    return {
        "status": "healthy",
        "camera_available": vision.is_camera_available(),
        "security_active": security.is_active(),
        "timestamp": datetime.now().isoformat()
    }

# ==================== DEBUG ENDPOINTS ====================

@app.get("/debug/camera-test")
async def camera_test():
    """Test camera capture"""
    try:
        vision = get_vision_system()
        
        if not vision.is_camera_available():
            return {
                "success": False,
                "error": "Camera not available",
                "timestamp": datetime.now().isoformat()
            }
        
        frame = vision.capture_frame()
        
        if frame is not None:
            img = vision.frame_to_pil(frame)
            img_b64 = vision.encode_image(img)
            
            return {
                "success": True,
                "message": "Camera working",
                "image_size": len(img_b64),
                "frame_shape": list(frame.shape),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Failed to capture frame",
                "timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        log_error(f"Camera test error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/debug/audio-test")
async def audio_test(request: AudioTestRequest):
    """Test text-to-speech"""
    try:
        log_info(f"Testing TTS with: {request.test_message}")
        speak(request.test_message, async_play=False)
        
        return {
            "success": True,
            "message": "Audio test completed",
            "text_spoken": request.test_message,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"Audio test error: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/debug/system-info")
async def system_info():
    """Get detailed system information"""
    import sys
    import platform
    
    vision = get_vision_system()
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "opencv_available": True,
        "camera_available": vision.is_camera_available(),
        "api_endpoints": len(app.routes),
        "video_note": "Run 'python video_viewer.py' for camera display",
        "timestamp": datetime.now().isoformat()
    }

# ==================== AI ENDPOINTS ====================

@app.post("/ai/query")
async def ai_query(request: AIQueryRequest):
    """Ask AI a question with optional image and memory context"""
    try:
        log_info(f"AI Query received: {request.query}")
        
        memory_context = ""
        if request.include_memory_context:
            from memory_module import build_memory_context
            memory_context = build_memory_context(request.query)
            log_info(f"Memory context built: {len(memory_context)} chars")
        
        if request.image_base64:
            log_info("Processing with image...")
            response = ask_ai(request.image_base64, request.query, memory_context)
        else:
            log_info("Processing text-only query...")
            response = ask_ai_text(request.query, memory_context)
        
        # Save conversation
        save_conversation(request.query, response)
        
        log_success(f"AI response generated: {len(response)} chars")
        
        return {
            "success": True,
            "query": request.query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"AI query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/process-command")
async def process_command(request: TextRequest):
    """Process a natural language command and route to appropriate handler"""
    try:
        text = request.text
        log_info(f"Command received: {text}")
        
        intent = classify_intent(text)
        log_info(f"Intent classified: {intent}")
        
        response_data = {
            "success": True,
            "command": text,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        }
        
        # Route to appropriate handler
        if intent == "memory_save":
            memory_cmd = is_memory_command(text)
            if memory_cmd == "save":
                memory_text = extract_memory_content(text)
                needs_cam = needs_visual_context(text)
                
                if memory_text:
                    save_memory(memory_text, f"User said: {text}")
                    response_data["response"] = "Got it! I'll remember that."
                    response_data["memory_saved"] = True
                else:
                    response_data["response"] = "Please provide more details or an image."
                    response_data["needs_image"] = needs_cam
        
        elif intent == "memory_recall":
            memories = search_memories(text)
            response_data["memories"] = memories[:5]
            if memories:
                memory_text = ", ".join([m['memory'] for m in memories[:3]])
                response_data["response"] = f"Based on what I remember: {memory_text}"
            else:
                response_data["response"] = "I don't have any memories matching that."
        
        elif intent == "reminder":
            task, duration = extract_reminder_parts(text)
            if task and duration:
                remind_time = datetime.now() + timedelta(seconds=duration)
                save_reminder(task, remind_time)
                response_data["response"] = f"Reminder set for {task}"
                response_data["reminder_set"] = True
            else:
                response_data["response"] = "Please specify task and time."
                response_data["needs_clarification"] = True
        
        elif intent == "security_activate":
            response_data["response"] = "Please provide your face image to activate security."
            response_data["needs_image"] = True
        
        else:
            # Use AI to respond
            response = ask_ai_text(text)
            response_data["response"] = response
        
        log_success(f"Command processed: {response_data['response']}")
        
        return response_data
    
    except Exception as e:
        log_error(f"Command processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MEMORY ENDPOINTS ====================

@app.post("/memory/save")
async def save_memory_endpoint(request: MemorySaveRequest):
    """Save a memory with optional image context"""
    try:
        memory_text = request.memory_text
        
        if request.image_base64:
            prompt = f"The user wants to remember: '{memory_text}'. Analyze the image and describe what they should remember."
            memory_text = ask_ai(request.image_base64, prompt)
        
        success = save_memory(memory_text, request.context)
        
        return {
            "success": success,
            "memory_saved": memory_text,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"Memory save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def search_memory_endpoint(request: MemorySearchRequest):
    """Search for memories"""
    try:
        memories = search_memories(request.query)
        
        return {
            "success": True,
            "query": request.query,
            "count": len(memories),
            "memories": memories[:request.max_results],
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"Memory search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/all")
async def get_all_memories():
    """Get all memories"""
    try:
        memory_system = get_memory_system()
        memories = memory_system.get_all_memories()
        
        return {
            "success": True,
            "count": len(memories),
            "memories": memories,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"Get all memories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== REMINDER ENDPOINTS ====================

@app.post("/reminder/create")
async def create_reminder(request: ReminderRequest):
    """Create a new reminder"""
    try:
        duration_seconds = parse_time_duration(request.time_description)
        
        if not duration_seconds:
            raise HTTPException(status_code=400, detail="Invalid time description")
        
        remind_time = datetime.now() + timedelta(seconds=duration_seconds)
        success = save_reminder(request.task, remind_time)
        
        return {
            "success": success,
            "task": request.task,
            "remind_time": remind_time.isoformat(),
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"Reminder creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== TTS ENDPOINTS ====================

@app.post("/tts/speak")
async def text_to_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """Convert text to speech"""
    try:
        log_info(f"TTS request: {request.text}")
        background_tasks.add_task(speak, request.text, request.save_audio)
        
        return {
            "success": True,
            "text": request.text,
            "message": "Speech queued",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CONVERSATION ENDPOINTS ====================

@app.get("/conversation/history")
async def get_conversation_history_endpoint(limit: Optional[int] = None):
    """Get conversation history"""
    try:
        history = get_conversation_history(limit)
        
        return {
            "success": True,
            "count": len(history),
            "conversations": history,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        log_error(f"Get conversation history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run the application
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🐍 VENOM AI ASSISTANT API")
    print("=" * 60)
    print("🌐 API Server: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔍 Debug Info: http://localhost:8000/debug/system-info")
    print("=" * 60)
    print("\n💡 For video output, run in another terminal:")
    print("   python video_viewer.py")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
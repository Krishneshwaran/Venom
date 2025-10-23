# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Gemini Live Chat** implementation of the Venom AI Assistant, focused on real-time multimodal interactions using Google Gemini 2.0 Flash. This is a simplified, optimized version separate from the full Venom AI system in the parent directory.

**Key Distinction**: This subdirectory (`Gemini_method/`) uses Google's native live streaming API for real-time video/audio chat, while the parent directory contains the full-featured Venom AI with modules for memory, reminders, and security.

## Architecture

### Core Components

1. **live_chat_module.py** - Main engine for real-time multimodal chat
   - `LiveChatEngine`: Manages camera, audio, and Gemini 2.0 Flash sessions
   - Supports three modes: video-only, audio-only, or multimodal (both)
   - **Optimized Q&A mode** (recommended): Continuous camera feed with keyboard-based queries

2. **ai_module.py** - AI processing for static image queries
   - Uses Gemini 2.5 Flash for image+text queries
   - Integrates conversation history for context
   - Supports Tamil language responses

3. **conversation_module.py** - Conversation history management
   - Saves Q&A exchanges with timestamps
   - Intent classification (memory, reminder, security triggers)
   - Command detection and validation

4. **config.py** - Centralized configuration
   - API keys (Google Gemini)
   - Model selection (gemini-2.0-flash-exp, gemini-2.5-flash)
   - Performance settings (video FPS, audio rate, image sizes)

5. **utils.py** - Common utilities
   - Logging functions (success, error, info, warning)
   - JSON file operations
   - Timestamp formatting

6. **main_live_chat.py** - Application entry point
   - Interactive menu for mode selection
   - Orchestrates different chat modes

### Data Storage

- **conversation_history.json** - Saved conversations with timestamps
- **data/** directory - Contains conversation and memory data from parent system

## Common Commands

### Running the Application

```bash
# Run the main live chat interface
python main_live_chat.py
```

**Available Modes:**
1. Live Video Chat - Real-time streaming with video analysis
2. **Optimized Video Q&A** (Recommended) - Continuous camera with keyboard queries
3. Live Audio Chat - Voice-only conversation
4. Multimodal Chat - Both video and audio together

### Testing Individual Modules

```bash
# Test AI module
python -c "from ai_module import get_ai_engine; engine = get_ai_engine(); print(engine.ask_text_only('Hello'))"

# Test conversation module
python -c "from conversation_module import save_conversation; save_conversation('test', 'response')"
```

### Gemini API Configuration

Set your Google API key in `config.py`:
```python
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'your-key-here')
```

Or set environment variable:
```bash
set GOOGLE_API_KEY=your-key-here  # Windows
export GOOGLE_API_KEY=your-key-here  # Linux/Mac
```

## Development Guidelines

### Working with Live Sessions

The `LiveChatEngine` manages WebSocket-like connections to Gemini:

- **Session lifecycle**: Created in `live_multimodal_session()`, uses async context manager
- **Frame streaming**: `_video_sender()` sends frames every 2 seconds (configurable)
- **Audio streaming**: `_audio_sender()` streams PCM audio continuously
- **Response handling**: `_response_receiver()` processes text and audio responses

**Important**: Always call `cleanup()` to release camera and audio resources.

### Optimized Q&A Mode Architecture

The recommended mode (`optimized_video_qa()`) is more efficient:
1. Camera runs continuously in background task
2. User types questions via keyboard
3. Current frame is captured on-demand when question asked
4. Uses `_quick_image_query()` for fast Gemini 2.0 Flash responses
5. No full session overhead - single API call per query

### Conversation History Integration

All modules that query Gemini automatically inject conversation history:
- Last 3-5 conversations included as context
- Format: "Recent conversation history:\nUser: {question}\nYou: {response}\n"
- Helps maintain continuity across queries

### Tamil Language Support

The system has built-in Tamil support:
- Prompts include Tamil instructions: `"உன் பதில் சுருக்கமாகவும் இயல்பாகவும் இருக்கட்டும்"`
- Responses are conversational (2-3 sentences max)
- Uses recent conversation history for context-aware Tamil replies

### Frame Processing Pipeline

1. **Capture**: `capture_frame_optimized()` - Reads from OpenCV VideoCapture
2. **Resize**: Downscale to 320x240 for efficiency
3. **Encode**: JPEG compression at 70% quality
4. **Send**: As bytes with mime_type="image/jpeg"

For static queries (ai_module), images are resized to match `Config.IMAGE_MAX_SIZE` (default 800px).

## Key Design Patterns

### Singleton Pattern for Global Instances

All modules use singleton pattern via global instances:
```python
_ai_engine = None
def get_ai_engine():
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine()
    return _ai_engine
```

This ensures:
- Single API client instance (avoiding re-initialization)
- Consistent state across imports
- Easy access from any module

### Async/Await for Real-time Operations

Live chat uses `asyncio` extensively:
- Concurrent tasks for video sender, audio sender, response receiver
- `asyncio.gather()` runs all tasks in parallel
- Non-blocking operations for smooth real-time experience

### Configuration-Driven Behavior

All magic numbers are in `Config` class:
- Video settings: `VIDEO_FPS`, `VIDEO_WIDTH`, `VIDEO_HEIGHT`
- Audio settings: `AUDIO_RATE`, `AUDIO_CHANNELS`, `AUDIO_CHUNK`
- AI settings: `MAX_OUTPUT_TOKENS`, `TEMPERATURE`, `MAX_HISTORY_LENGTH`

Modify config instead of hardcoding values in modules.

## Integration with Parent Venom AI System

This Gemini_method implementation is **standalone** but can integrate with parent system:

- **Shared conversation storage**: Uses same JSON format as parent `conversation_module.py`
- **Compatible memory format**: Can read memories saved by parent system
- **Independent AI backend**: Uses Gemini directly, not parent's `ai_module.py`

The parent directory contains additional features not in this implementation:
- Memory system with visual context (`memory_module.py`)
- Reminder system with time parsing (`reminder_module.py`)
- Security/face recognition (`security_module.py`)
- TTS with ElevenLabs (`tts_module.py`)
- Voice activation listener (`voice_module.py`)
- Flask API server for frontend integration (`api_server.py`)

## Troubleshooting

### Camera Issues
```bash
# Check camera availability
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Failed'); cap.release()"
```

### API Errors
- Verify `GOOGLE_API_KEY` is set correctly in config.py
- Check API quota: https://aistudio.google.com/app/apikey
- Ensure using supported models: gemini-2.0-flash-exp, gemini-2.5-flash

### Audio Issues
```bash
# List audio devices
python -c "import pyaudio; p = pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"
```

### Memory/Performance Issues
- Reduce `VIDEO_FPS` in config (default 30, try 15)
- Increase frame send interval in `_video_sender()` (default every 2 seconds)
- Lower JPEG quality in `capture_frame_optimized()` (default 70, try 50)

## File Structure Summary

```
Gemini_method/
├── main_live_chat.py          # Entry point with mode selection
├── live_chat_module.py         # Core live chat engine
├── ai_module.py                # Static image query handling
├── conversation_module.py      # History and intent management
├── config.py                   # Configuration settings
├── utils.py                    # Helper functions
├── gemini.py                   # Legacy Gemini implementation
├── gemini_v2.py               # Alternative Gemini implementation
├── conversation_history.json   # Saved conversations
├── data/                       # Data directory
├── tts_cache/                  # TTS audio cache (if used)
└── __pycache__/               # Python cache
```

## Related Documentation

For the full Venom AI system (parent directory), see:
- `api_guide.md` - Complete FastAPI backend documentation
- `FRONTEND_INTEGRATION.md` - Frontend integration with animated face
- `core.py` - Main orchestrator for full system

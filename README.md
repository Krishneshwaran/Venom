# Voice Command AI Assistant

This project combines multiple tools into a voice-command operated AI assistant:

- **DIY Helping**: Real-time help through cameras
- **Memory System**: Remembers everything we do
- **Activity Monitor**: Monitoring daily activities
- **Language Teaching**: Vaayadi language teaching tool

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up API key:
   - Create a `.env` file in the project root with: `OPENROUTER_API_KEY=your_key_here`
   - Or set environment variable `OPENROUTER_API_KEY`
   - Or enter it when prompted

## DIY Help Module

The DIY help module provides real-time assistance based on your camera feed for real-world objects and situations using Claude 3.5 Haiku. If camera is not available, it works in text-only mode.

### Usage

Run the camera helper:
```bash
python diy_help/real_time/camera_helper.py
```

- **With Camera**: A continuous camera feed window will open showing your real-time view
- **Text-Only Mode**: If camera fails, the system automatically switches to text-only assistance
- Simply speak any question or command - no activation phrase needed
- The system will analyze what's visible (or your description) and provide helpful responses
- Receive spoken AI-powered answers

### Features

- Continuous real-time camera feed display (when available)
- Automatic fallback to text-only mode if camera fails
- Voice-activated AI assistance - just speak naturally
- AI vision analysis using Claude 3.5 Haiku for excellent image understanding
- Voice query input and text-to-speech responses
- Local image storage for captured frames
- Audio response files saved for all AI interactions

## Project Structure

- `diy_help/`: DIY assistance module
  - `screens/`: Screen-related help
  - `real_time/`: Real-time assistance
    - `camera_helper.py`: Main camera helper script

- `memory/`: Memory and recall system
  - `storage/`: Data storage
  - `recall/`: Retrieval mechanisms

- `activity_monitor/`: Daily activity monitoring
  - `daily/`: Daily logs
  - `tracking/`: Activity tracking

- `language_teaching/`: Language teaching tools
  - `vaayadi/`: Vaayadi specific content
  - `lessons/`: Lesson materials

- `voice_commands/`: Voice command processing
  - `recognition/`: Speech recognition
  - `processing/`: Command processing

- `core/`: Core application logic
  - `main/`: Main entry points
  - `interfaces/`: Module interfaces

- `utils/`: Utility functions
  - `helpers/`: Helper scripts

- `tests/`: Test suites
  - `unit/`: Unit tests
  - `integration/`: Integration tests

- `docs/`: Documentation
  - `api/`: API documentation
  - `user_guide/`: User guides

## Getting Started

[Add setup instructions here]

## Usage

[Add usage instructions here]
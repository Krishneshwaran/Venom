# Venom AI Frontend Integration

## Overview
This integration connects your Python backend (Venom AI) with the Next.js animated face frontend. The eyes open when Venom is activated and close when it's idle.

## Architecture
- **Backend**: Flask API server running on port 5000
- **Frontend**: Next.js app polling the API every 500ms
- **Communication**: REST API with state updates

## Files Modified/Created

### Backend (Python)
1. **`api_server.py`** - NEW
   - Flask server that exposes Venom state
   - Endpoints:
     - `GET /api/state` - Returns current Venom state
     - `GET /api/health` - Health check

2. **`voice_module.py`** - MODIFIED
   - Added API state updates when Venom activates/deactivates
   - Updates sent to frontend automatically

3. **`core.py`** - MODIFIED
   - Starts API server on initialization

### Frontend (Next.js)
1. **`components/animated-face.tsx`** - MODIFIED
   - Polls API every 500ms
   - Opens eyes when `is_active` is true
   - Closes eyes when `is_active` is false
   - Shows activation status and last command

## How It Works

1. **Venom Activation**:
   ```
   User says "hey venom" 
   → voice_module detects activation
   → update_state(is_active=True, is_listening=True)
   → API updates state
   → Frontend polls API
   → Eyes open!
   ```

2. **Venom Deactivation**:
   ```
   Timeout or completion
   → update_state(is_active=False, is_listening=False)
   → Frontend detects change
   → Eyes close!
   ```

## Setup & Running

### 1. Install Dependencies

**Python:**
```bash
cd "d:\Vijay TV\Venom"
.\env\Scripts\Activate.ps1
pip install flask flask-cors pygame
```

**Next.js:**
```bash
cd animated-face
npm install
```

### 2. Start the Backend
```bash
cd "d:\Vijay TV\Venom\diy_help\new_method"
..\..\env\Scripts\python.exe core.py
```

The API server will start automatically on http://localhost:5000

### 3. Start the Frontend
```bash
cd "d:\Vijay TV\Venom\animated-face"
npm run dev
```

Open http://localhost:3000 in your browser

### 4. Test It!
1. Say "hey venom" or "dei venom"
2. Watch the eyes open on the frontend
3. After timeout, eyes close automatically

## Testing the API

Test the API independently:
```bash
cd "d:\Vijay TV\Venom\diy_help\new_method"
..\..\env\Scripts\python.exe test_api.py
```

Open http://localhost:5000/api/state in your browser to see the state.

## API Response Format

```json
{
  "is_active": true,
  "is_listening": true,
  "is_speaking": false,
  "last_command": "what is the weather",
  "timestamp": 1234567890.123
}
```

## State Variables
- **`is_active`**: Venom is activated and listening
- **`is_listening`**: Currently listening for commands
- **`is_speaking`**: Currently speaking a response
- **`last_command`**: Last recognized command text
- **`timestamp`**: Unix timestamp of last update

## Customization

### Change polling interval (frontend):
In `animated-face.tsx`, line ~22:
```typescript
}, 500) // Poll every 500ms - change this value
```

### Change API port (backend):
In `api_server.py`, line 33:
```python
def start_api_server(port=5000):  # Change port here
```

Also update frontend URL in `animated-face.tsx`, line ~24:
```typescript
const response = await fetch('http://localhost:5000/api/state')
```

## Troubleshooting

### Eyes don't open/close
1. Check if API is running: http://localhost:5000/api/health
2. Check browser console for CORS errors
3. Verify both backend and frontend are running

### CORS Errors
- Ensure `flask-cors` is installed
- Check that API server started successfully

### API not responding
- Check if port 5000 is available
- Look for error messages in Python console
- Try running `test_api.py` to verify API works

## Future Enhancements
- [ ] WebSocket for real-time updates (no polling)
- [ ] Add speaking animation when `is_speaking` is true
- [ ] Add visual feedback for `last_command`
- [ ] Add error states for API disconnection

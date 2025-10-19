# Venom AI Assistant - FastAPI Usage Guide

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
python api.py
```

Or using uvicorn directly:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📡 API Endpoints

### **Health & Status**

#### `GET /`
Health check endpoint
```bash
curl http://localhost:8000/
```

#### `GET /health`
Detailed system health
```bash
curl http://localhost:8000/health
```

---

### **🤖 AI Endpoints**

#### `POST /ai/query`
Ask AI with optional image and memory context

**Request:**
```json
{
  "query": "What's in this image?",
  "image_base64": "base64_encoded_image_here",
  "include_memory_context": true
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/ai/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What do you see?",
    "image_base64": null,
    "include_memory_context": true
  }'
```

#### `POST /ai/process-command`
Process natural language command (auto-routes to appropriate handler)

**Request:**
```json
{
  "text": "remember my name is Kavin",
  "language": "en"
}
```

**Tamil Example:**
```bash
curl -X POST "http://localhost:8000/ai/process-command" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "neyabagam vachuko",
    "language": "ta"
  }'
```

---

### **🧠 Memory Endpoints**

#### `POST /memory/save`
Save a memory

**Request:**
```json
{
  "memory_text": "My car keys are on the kitchen table",
  "context": "User told me this on 2025-01-15",
  "image_base64": null
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/memory/save" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_text": "My name is Kavin",
    "context": "User introduction"
  }'
```

#### `POST /memory/search`
Search memories

**Request:**
```json
{
  "query": "where are my keys",
  "max_results": 5
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/memory/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "name",
    "max_results": 5
  }'
```

#### `GET /memory/all`
Get all memories

```bash
curl http://localhost:8000/memory/all
```

#### `DELETE /memory/{memory_id}`
Delete a specific memory

```bash
curl -X DELETE "http://localhost:8000/memory/5"
```

---

### **⏰ Reminder Endpoints**

#### `POST /reminder/create`
Create a new reminder

**Request:**
```json
{
  "task": "Call John",
  "time_description": "5 minutes"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/reminder/create" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Take medicine",
    "time_description": "2 hours"
  }'
```

#### `GET /reminder/all`
Get all reminders

```bash
curl http://localhost:8000/reminder/all
```

---

### **🔒 Security Endpoints**

#### `POST /security/register-face`
Register owner's face for security

**Request:**
```json
{
  "image_base64": "base64_encoded_face_image"
}
```

**Python Example:**
```python
import base64
import requests

# Read image and encode
with open("my_face.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/security/register-face",
    json={"image_base64": img_b64}
)
print(response.json())
```

#### `GET /security/status`
Check security status

```bash
curl http://localhost:8000/security/status
```

#### `POST /security/deactivate`
Deactivate security monitoring

```bash
curl -X POST "http://localhost:8000/security/deactivate"
```

---

### **💬 Conversation Endpoints**

#### `POST /conversation/save`
Save a conversation

**Request:**
```json
{
  "question": "What's the weather?",
  "response": "It's sunny today"
}
```

#### `GET /conversation/history?limit=10`
Get conversation history

```bash
curl "http://localhost:8000/conversation/history?limit=10"
```

#### `DELETE /conversation/history`
Clear all conversation history

```bash
curl -X DELETE "http://localhost:8000/conversation/history"
```

---

### **🔊 TTS Endpoints**

#### `POST /tts/speak`
Convert text to speech

**Request:**
```json
{
  "text": "Hello, how are you?",
  "save_audio": false
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/tts/speak" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome back!",
    "save_audio": false
  }'
```

---

### **👁️ Vision Endpoints**

#### `POST /vision/analyze`
Analyze an uploaded image

**Form Data:**
- `file`: Image file
- `query`: Question about the image (optional)

**Example:**
```bash
curl -X POST "http://localhost:8000/vision/analyze" \
  -F "file=@image.jpg" \
  -F "query=What objects do you see?"
```

#### `GET /vision/capture`
Capture frame from camera

```bash
curl http://localhost:8000/vision/capture
```

Returns base64 encoded image.

---

## 🐍 Python Client Example

```python
import requests
import base64

BASE_URL = "http://localhost:8000"

class VenomClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
    
    def ask_ai(self, query, image_path=None):
        """Ask AI a question"""
        data = {"query": query, "include_memory_context": True}
        
        if image_path:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            data["image_base64"] = img_b64
        
        response = requests.post(f"{self.base_url}/ai/query", json=data)
        return response.json()
    
    def save_memory(self, memory_text, context=""):
        """Save a memory"""
        data = {"memory_text": memory_text, "context": context}
        response = requests.post(f"{self.base_url}/memory/save", json=data)
        return response.json()
    
    def search_memories(self, query):
        """Search memories"""
        data = {"query": query, "max_results": 5}
        response = requests.post(f"{self.base_url}/memory/search", json=data)
        return response.json()
    
    def create_reminder(self, task, time_description):
        """Create a reminder"""
        data = {"task": task, "time_description": time_description}
        response = requests.post(f"{self.base_url}/reminder/create", json=data)
        return response.json()
    
    def speak(self, text):
        """Text to speech"""
        data = {"text": text, "save_audio": False}
        response = requests.post(f"{self.base_url}/tts/speak", json=data)
        return response.json()

# Usage
client = VenomClient()

# Ask AI
result = client.ask_ai("What's the capital of France?")
print(result)

# Save memory
result = client.save_memory("My name is Kavin")
print(result)

# Search memories
result = client.search_memories("name")
print(result)

# Create reminder
result = client.create_reminder("Call mom", "1 hour")
print(result)

# Speak
result = client.speak("Hello, welcome!")
print(result)
```

---

## 🌐 JavaScript/Frontend Example

```javascript
const BASE_URL = 'http://localhost:8000';

class VenomClient {
    async askAI(query, imageBase64 = null) {
        const response = await fetch(`${BASE_URL}/ai/query`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                image_base64: imageBase64,
                include_memory_context: true
            })
        });
        return await response.json();
    }
    
    async saveMemory(memoryText, context = '') {
        const response = await fetch(`${BASE_URL}/memory/save`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                memory_text: memoryText,
                context: context
            })
        });
        return await response.json();
    }
    
    async searchMemories(query) {
        const response = await fetch(`${BASE_URL}/memory/search`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: query, max_results: 5})
        });
        return await response.json();
    }
    
    async createReminder(task, timeDescription) {
        const response = await fetch(`${BASE_URL}/reminder/create`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                task: task,
                time_description: timeDescription
            })
        });
        return await response.json();
    }
}

// Usage
const client = new VenomClient();

// Ask AI
client.askAI('What is AI?').then(result => console.log(result));

// Save memory
client.saveMemory('My favorite color is blue').then(result => console.log(result));

// Search memories
client.searchMemories('color').then(result => console.log(result));

// Create reminder
client.createReminder('Team meeting', '30 minutes').then(result => console.log(result));
```

---

## 🔧 Environment Variables

Create a `.env` file:

```env
GOOGLE_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
LISTEN_WINDOW=20
```

---

## 📊 Response Format

All endpoints return JSON responses with the following structure:

### Success Response
```json
{
  "success": true,
  "data": {...},
  "timestamp": "2025-10-19T10:30:00"
}
```

### Error Response
```json
{
  "detail": "Error message here"
}
```

---

## 🔐 Security Best Practices

1. **Use HTTPS in production** - Never expose API over HTTP
2. **Add authentication** - Implement JWT tokens or API keys
3. **Rate limiting** - Prevent abuse
4. **Input validation** - Already implemented with Pydantic models

### Adding API Key Authentication (Optional)

```python
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

API_KEY = "your-secret-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# Add to endpoints
@app.post("/ai/query")
async def ai_query(request: AIQueryRequest, api_key: str = Security(get_api_key)):
    # Your code here
```

---

## 🧪 Testing with Postman

### Import Collection

Create a Postman collection with these requests:

1. **Health Check** - GET `http://localhost:8000/health`
2. **AI Query** - POST `http://localhost:8000/ai/query`
3. **Save Memory** - POST `http://localhost:8000/memory/save`
4. **Search Memory** - POST `http://localhost:8000/memory/search`
5. **Create Reminder** - POST `http://localhost:8000/reminder/create`

---

## 🐳 Docker Deployment (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  venom-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./images:/app/images
      - ./tts_cache:/app/tts_cache
      - ./conversation_history.json:/app/conversation_history.json
      - ./memory.json:/app/memory.json
      - ./reminders.json:/app/reminders.json
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

---

## 📱 Mobile App Integration

### React Native Example

```javascript
import axios from 'axios';

const API_BASE_URL = 'http://your-server-ip:8000';

export const VenomAPI = {
  async askAI(query, imageBase64 = null) {
    const response = await axios.post(`${API_BASE_URL}/ai/query`, {
      query,
      image_base64: imageBase64,
      include_memory_context: true
    });
    return response.data;
  },

  async captureAndAnalyze(imageUri, query) {
    // Convert image to base64
    const base64 = await FileSystem.readAsStringAsync(imageUri, {
      encoding: FileSystem.EncodingType.Base64,
    });
    
    return await this.askAI(query, base64);
  },

  async saveMemory(text) {
    const response = await axios.post(`${API_BASE_URL}/memory/save`, {
      memory_text: text,
      context: 'Mobile app'
    });
    return response.data;
  },

  async createReminder(task, time) {
    const response = await axios.post(`${API_BASE_URL}/reminder/create`, {
      task,
      time_description: time
    });
    return response.data;
  }
};
```

---

## 🌍 Tamil Language Support

All endpoints support Tamil language automatically:

### Memory Commands (Tamil)
```bash
# Save memory in Tamil
curl -X POST "http://localhost:8000/ai/process-command" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "neyabagam vachuko en peyar Kavin",
    "language": "ta"
  }'

# Search memory in Tamil
curl -X POST "http://localhost:8000/memory/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "peyar",
    "max_results": 5
  }'
```

### Reminder Commands (Tamil)
```bash
curl -X POST "http://localhost:8000/reminder/create" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "அம்மாவுக்கு call செய்",
    "time_description": "5 minutes"
  }'
```

---

## 🔄 WebSocket Support (Future Enhancement)

For real-time features like live camera feed or voice streaming:

```python
from fastapi import WebSocket

@app.websocket("/ws/camera")
async def websocket_camera(websocket: WebSocket):
    await websocket.accept()
    vision = get_vision_system()
    
    try:
        while True:
            frame = vision.capture_frame()
            if frame:
                img = vision.frame_to_pil(frame)
                img_b64 = vision.encode_image(img)
                await websocket.send_json({
                    "type": "camera_frame",
                    "data": img_b64
                })
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

---

## 📈 Performance Tips

1. **Use async/await** - Already implemented for better concurrency
2. **Enable caching** - Redis for frequently accessed data
3. **Optimize images** - Compress before sending to API
4. **Use background tasks** - For TTS and long-running operations
5. **Database integration** - Replace JSON files with PostgreSQL/MongoDB

---

## 🐛 Troubleshooting

### Camera not working
```bash
# Check camera permissions
ls -l /dev/video*

# Test camera
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Port already in use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn api:app --port 8001
```

### Module import errors
```bash
# Ensure all modules are in same directory
ls -l *.py

# Check Python path
python -c "import sys; print(sys.path)"
```

---

## 📚 API Testing Examples

### Full Workflow Test

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Health check
print("Testing health check...")
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. Save memory
print("\nSaving memory...")
response = requests.post(f"{BASE_URL}/memory/save", json={
    "memory_text": "My favorite color is blue",
    "context": "User preference"
})
print(response.json())

# 3. Search memory
print("\nSearching memory...")
response = requests.post(f"{BASE_URL}/memory/search", json={
    "query": "favorite color",
    "max_results": 5
})
print(response.json())

# 4. Create reminder
print("\nCreating reminder...")
response = requests.post(f"{BASE_URL}/reminder/create", json={
    "task": "Test reminder",
    "time_description": "1 minute"
})
print(response.json())

# 5. Ask AI
print("\nAsking AI...")
response = requests.post(f"{BASE_URL}/ai/query", json={
    "query": "What's my favorite color?",
    "include_memory_context": True
})
print(response.json())

# 6. Get conversation history
print("\nGetting conversation history...")
response = requests.get(f"{BASE_URL}/conversation/history?limit=5")
print(response.json())

print("\n✅ All tests completed!")
```

---

## 🎯 Use Cases

### 1. Smart Home Assistant
```python
# Control smart home with voice commands via API
client.ask_ai("Turn on the lights in living room")
```

### 2. Personal Memory Assistant
```python
# Remember important information
client.save_memory("My passport number is AB123456")
client.search_memories("passport")
```

### 3. Medication Reminder
```python
# Set health reminders
client.create_reminder("Take blood pressure medication", "8 hours")
```

### 4. Home Security
```python
# Activate security when leaving
with open("my_face.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()
client.register_face(img_b64)
```

---

## 📞 Support

For issues or questions:
- Check `/docs` endpoint for interactive API documentation
- Review logs in terminal where API is running
- Test individual modules before API integration

---

## 🎉 Success!

Your Venom AI Assistant API is now ready! Access it at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

Happy coding! 🚀
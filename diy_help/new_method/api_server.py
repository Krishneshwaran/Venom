"""
Simple API Server for Frontend Communication
Sends Venom state updates to the animated face frontend
"""

from flask import Flask, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Global state
venom_state = {
    "is_active": False,
    "is_listening": False,
    "is_speaking": False,
    "last_command": "",
    "timestamp": 0
}

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current Venom state"""
    return jsonify(venom_state)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

def update_state(is_active=None, is_listening=None, is_speaking=None, last_command=None):
    """Update the global state"""
    import time
    if is_active is not None:
        venom_state["is_active"] = is_active
    if is_listening is not None:
        venom_state["is_listening"] = is_listening
    if is_speaking is not None:
        venom_state["is_speaking"] = is_speaking
    if last_command is not None:
        venom_state["last_command"] = last_command
    venom_state["timestamp"] = time.time()

def start_api_server(port=5000):
    """Start the API server in a background thread"""
    def run_server():
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"🌐 API Server started on http://localhost:{port}")
    return server_thread

# Singleton instance
_server_thread = None

def get_api_server():
    """Get or start API server"""
    global _server_thread
    if _server_thread is None:
        _server_thread = start_api_server()
    return _server_thread

"""
Simple API Server for Frontend Communication
Sends Venom state updates to the animated face frontend
"""

from flask import Flask, jsonify
from flask_cors import CORS
import threading
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://krish:krish@study.po9dv.mongodb.net/"
mongo_client = None
venom_db = None
state_collection = None

def init_mongodb():
    """Initialize MongoDB connection"""
    global mongo_client, venom_db, state_collection
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_client.admin.command('ping')
        venom_db = mongo_client['venom']
        state_collection = venom_db['state']
        print("✅ Connected to MongoDB Atlas")
        
        # Initialize state document if it doesn't exist
        if state_collection.count_documents({}) == 0:
            state_collection.insert_one({
                "is_active": False,
                "is_listening": False,
                "is_speaking": False,
                "last_command": "",
                "timestamp": 0
            })
    except ConnectionFailure as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
    except Exception as e:
        print(f"❌ MongoDB initialization error: {e}")

# Initialize MongoDB on module load
init_mongodb()

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
    """Get current Venom state from MongoDB"""
    try:
        state = state_collection.find_one({}, {'_id': 0})
        if state:
            return jsonify(state)
        else:
            return jsonify({
                "is_active": False,
                "is_listening": False,
                "is_speaking": False,
                "last_command": "",
                "timestamp": 0
            })
    except Exception as e:
        print(f"❌ Error fetching state from MongoDB: {e}")
        return jsonify({
            "is_active": False,
            "is_listening": False,
            "is_speaking": False,
            "last_command": "",
            "timestamp": 0
        })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

def update_state(is_active=None, is_listening=None, is_speaking=None, last_command=None):
    """Update the state in MongoDB"""
    import time
    
    update_doc = {"timestamp": time.time()}
    
    if is_active is not None:
        update_doc["is_active"] = is_active
    if is_listening is not None:
        update_doc["is_listening"] = is_listening
    if is_speaking is not None:
        update_doc["is_speaking"] = is_speaking
    if last_command is not None:
        update_doc["last_command"] = last_command
    
    try:
        if state_collection is not None:
            state_collection.update_one({}, {"$set": update_doc}, upsert=True)
            print(f"✅ Updated MongoDB state: {update_doc}")
        else:
            print("⚠️ MongoDB not connected, state not saved")
    except Exception as e:
        print(f"❌ Error updating MongoDB state: {e}")

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

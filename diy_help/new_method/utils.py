"""
Utilities Module
Common helper functions for file operations, logging, and error handling
"""

import os
import json
from datetime import datetime

def ensure_directory(directory_path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path, exist_ok=True)
            print(f"✅ Created directory: {directory_path}")
            return True
        except Exception as e:
            print(f"⚠️ Could not create directory '{directory_path}': {e}")
            return False
    return True

def load_json_file(filepath, default=None):
    """Load JSON file with error handling"""
    if default is None:
        default = []
    
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    return default
        else:
            return default
    except json.JSONDecodeError:
        print(f"⚠️ {filepath} corrupted, returning default...")
        return default
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return default

def save_json_file(filepath, data):
    """Save data to JSON file with error handling"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving to {filepath}: {e}")
        return False

def initialize_json_file(filepath, default_data=None):
    """Initialize JSON file if it doesn't exist"""
    if default_data is None:
        default_data = []
    
    if not os.path.exists(filepath):
        return save_json_file(filepath, default_data)
    return True

def get_timestamp():
    """Get formatted timestamp"""
    return datetime.now().isoformat()

def get_filename_timestamp():
    """Get timestamp suitable for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def log_info(message):
    """Log info message"""
    print(f"ℹ️  {message}")

def log_success(message):
    """Log success message"""
    print(f"✅ {message}")

def log_warning(message):
    """Log warning message"""
    print(f"⚠️  {message}")

def log_error(message):
    """Log error message"""
    print(f"❌ {message}")

def log_debug(message):
    """Log debug message"""
    print(f"🔍 {message}")
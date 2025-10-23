"""
Utility Module
Common helper functions for the application
"""

import json
from datetime import datetime
from pathlib import Path


def log_success(message):
    """Print success message"""
    print(f"✅ {message}")


def log_error(message):
    """Print error message"""
    print(f"❌ {message}")


def log_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")


def log_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")


def get_timestamp():
    """Get current timestamp string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json_file(filepath, default=None):
    """
    Load JSON file
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist
    
    Returns:
        Loaded data or default
    """
    try:
        filepath = Path(filepath)
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    except Exception as e:
        log_error(f"Error loading {filepath}: {e}")
        return default if default is not None else {}


def save_json_file(filepath, data):
    """
    Save data to JSON file
    
    Args:
        filepath: Path to save file
        data: Data to save
    
    Returns:
        Boolean indicating success
    """
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        log_error(f"Error saving {filepath}: {e}")
        return False


def format_size(bytes_size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def truncate_text(text, max_length=100):
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
"""
Reminder Module
Handles reminder creation, storage, and notifications
"""

import re
import time
import threading
from datetime import datetime, timedelta
from config import Config
from utils import load_json_file, save_json_file, initialize_json_file, get_timestamp, log_success, log_error
from tts_module import speak

class ReminderSystem:
    """Reminder management system"""
    
    def __init__(self):
        self.reminder_file = Config.REMINDER_FILE
        self.shutdown_flag = False
        self.pending_reminder = {"waiting_for": None, "task": None, "time": None}
        initialize_json_file(self.reminder_file, [])
    
    def save_reminder(self, task, remind_time):
        """
        Save a reminder
        
        Args:
            task: Task description
            remind_time: datetime object for when to remind
        
        Returns:
            Boolean indicating success
        """
        try:
            reminders = load_json_file(self.reminder_file, default=[])
            
            reminder_entry = {
                "id": len(reminders) + 1,
                "task": task,
                "remind_time": remind_time.isoformat(),
                "created_at": get_timestamp(),
                "completed": False
            }
            
            reminders.append(reminder_entry)
            
            if save_json_file(self.reminder_file, reminders):
                log_success(f"Reminder saved to {self.reminder_file}")
                return True
            return False
        
        except Exception as e:
            log_error(f"Error saving reminder: {e}")
            return False
    
    def check_reminders_loop(self):
        """Background thread to check for due reminders"""
        log_success("Reminder checker started...")
        
        while not self.shutdown_flag:
            try:
                reminders = load_json_file(self.reminder_file, default=[])
                current_time = datetime.now()
                updated = False
                
                for reminder in reminders:
                    if not reminder.get('completed', False):
                        remind_time = datetime.fromisoformat(reminder['remind_time'])
                        
                        if current_time >= remind_time:
                            task = reminder['task']
                            print(f"\n🔔 REMINDER: {task}")
                            speak(f"Reminder! {task}")
                            
                            reminder['completed'] = True
                            updated = True
                
                if updated:
                    save_json_file(self.reminder_file, reminders)
                
                time.sleep(10)
            
            except Exception as e:
                log_error(f"Error in reminder checker: {e}")
                time.sleep(10)
    
    def start_reminder_checker(self):
        """Start reminder checker in background"""
        checker_thread = threading.Thread(target=self.check_reminders_loop, daemon=True)
        checker_thread.start()
        log_success("Reminder system active")
    
    def get_pending_reminder(self):
        """Get pending reminder state"""
        return self.pending_reminder
    
    def set_pending_task(self, task):
        """Set pending reminder task"""
        self.pending_reminder["task"] = task
        self.pending_reminder["waiting_for"] = "time"
    
    def set_pending_time(self, time_value):
        """Set pending reminder time"""
        self.pending_reminder["time"] = time_value
        self.pending_reminder["waiting_for"] = None
    
    def clear_pending(self):
        """Clear pending reminder"""
        self.pending_reminder = {"waiting_for": None, "task": None, "time": None}
    
    def start_pending(self):
        """Start pending reminder flow"""
        self.pending_reminder["waiting_for"] = "task"
    
    def shutdown(self):
        """Shutdown reminder system"""
        self.shutdown_flag = True

def parse_time_duration(text):
    """
    Parse time duration from text
    
    Args:
        text: Text like '5 minutes', '10 mins', '2 hours'
    
    Returns:
        Duration in seconds, or None if not parseable
    """
    text_lower = text.lower()
    
    numbers = re.findall(r'\d+', text)
    if not numbers:
        return None
    
    duration = int(numbers[0])
    
    if 'hour' in text_lower:
        return duration * 3600
    elif 'min' in text_lower:
        return duration * 60
    elif 'sec' in text_lower:
        return duration
    else:
        return duration * 60  # Default to minutes

def is_reminder_command(text):
    """Check if text is a reminder command"""
    text_lower = text.lower()
    
    reminder_triggers = ['remind me', 'reminder', 'set a reminder', 'remind',
                        'alert me', 'notify me']
    
    for trigger in reminder_triggers:
        if trigger in text_lower:
            return True
    
    return False

def extract_reminder_parts(text):
    """
    Extract task and time from reminder command
    
    Args:
        text: Command like "remind me to call John in 5 minutes"
    
    Returns:
        Tuple of (task, duration_seconds) or (None, None)
    """
    text_lower = text.lower()
    
    if 'to' in text_lower and any(word in text_lower for word in ['minute', 'min', 'hour', 'sec']):
        duration_seconds = parse_time_duration(text)
        if duration_seconds:
            # Extract task
            time_pattern = r'\s+in\s+\d+\s*(minute|min|hour|sec)'
            task = text_lower.replace('remind me to', '').replace('remind me', '').strip()
            task = re.sub(r'\s+in\s+\d+\s*(minutes?|mins?|hours?|secs?)\s*', '', task, flags=re.IGNORECASE).strip()
            
            if task:
                return (task, duration_seconds)
    
    return (None, None)

# Global reminder system instance
_reminder_system = None

def get_reminder_system():
    """Get or create reminder system instance"""
    global _reminder_system
    if _reminder_system is None:
        _reminder_system = ReminderSystem()
    return _reminder_system

def start_reminder_system():
    """Start the reminder system"""
    system = get_reminder_system()
    system.start_reminder_checker()

def save_reminder(task, remind_time):
    """Save a reminder"""
    system = get_reminder_system()
    return system.save_reminder(task, remind_time)

def get_pending_reminder():
    """Get pending reminder state"""
    system = get_reminder_system()
    return system.get_pending_reminder()
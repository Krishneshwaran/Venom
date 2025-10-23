"""
Conversation Module
Handles conversation history, command classification, and dialogue management
"""

from config import Config
from utils import load_json_file, save_json_file, get_timestamp, log_success, log_error

class ConversationManager:
    """Manages conversation history and command processing"""
    
    def __init__(self):
        self.conversation_file = Config.CONVERSATION_FILE
    
    def save_conversation(self, question, response):
        """
        Save conversation exchange to history
        
        Args:
            question: User's question/command
            response: AI's response
        
        Returns:
            Boolean indicating success
        """
        try:
            conversations = load_json_file(self.conversation_file, default=[])
            
            conversation_entry = {
                "timestamp": get_timestamp(),
                "question": question,
                "response": response
            }
            
            conversations.append(conversation_entry)
            
            if save_json_file(self.conversation_file, conversations):
                log_success(f"Conversation saved to {self.conversation_file}")
                return True
            return False
        
        except Exception as e:
            log_error(f"Error saving conversation: {e}")
            return False
    
    def get_conversation_history(self, limit=None):
        """
        Get conversation history
        
        Args:
            limit: Maximum number of conversations to return (None for all)
        
        Returns:
            List of conversation entries
        """
        conversations = load_json_file(self.conversation_file, default=[])
        if limit:
            return conversations[-limit:]
        return conversations
    
    def clear_history(self):
        """Clear all conversation history"""
        try:
            if save_json_file(self.conversation_file, []):
                log_success("Conversation history cleared")
                return True
            return False
        except Exception as e:
            log_error(f"Error clearing history: {e}")
            return False

def is_command(text):
    """
    Check if text is a valid command or question
    
    Args:
        text: Input text
    
    Returns:
        Command type: "exit", "help", "question", or None
    """
    question_words = ['what', 'where', 'when', 'why', 'how', 'who', 'which', 
                     'can', 'could', 'would', 'should', 'is', 'are', 'do', 'does', 'did']
    action_words = ['tell', 'show', 'explain', 'describe', 'identify', 'find', 
                   'look', 'search', 'check', 'see', 'read', 'scan']
    
    text_lower = text.lower()
    
    # Check for exit command
    if any(word in text_lower for word in ["exit", "quit", "stop"]):
        return "exit"
    
    # Check for help command
    if "help me" in text_lower:
        return "help"
    
    # Check if ends with question mark
    if text_lower.endswith('?'):
        return "question"
    
    # Check if starts with question word
    words = text_lower.split()
    if words and words[0] in question_words:
        return "question"
    
    # Check if contains action words
    if any(word in text_lower for word in action_words):
        return "question"
    
    # Check for brand names or specific items
    brands = ['oneplus', 'iphone', 'samsung', 'xiaomi', 'oppo', 'vivo', 
             'nokia', 'motorola', 'lg', 'sony', 'huawei']
    if any(brand in text_lower for brand in brands):
        return "question"
    
    # Short phrases are likely requests
    if len(words) <= 3:
        return "question"
    
    # Default to question to be permissive
    return "question"

def classify_intent(text):
    """
    Classify user intent from text
    
    Args:
        text: User input text
    
    Returns:
        Intent type string
    """
    text_lower = text.lower()
    
    # Memory intents
    if any(trigger in text_lower for trigger in ['remember', 'save this', 'note this']):
        return "memory_save"
    
    if any(trigger in text_lower for trigger in ['what do you remember', 'do you remember', 'recall']):
        return "memory_recall"
    
    # Reminder intents
    if any(trigger in text_lower for trigger in ['remind me', 'reminder', 'set a reminder']):
        return "reminder"
    
    # Security intents
    if any(trigger in text_lower for trigger in ['leaving', 'going out']):
        return "security_activate"
    
    # General question
    return "question"

# Global conversation manager instance
_conversation_manager = None

def get_conversation_manager():
    """Get or create conversation manager instance"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager

def save_conversation(question, response):
    """Save a conversation"""
    manager = get_conversation_manager()
    return manager.save_conversation(question, response)

def get_conversation_history(limit=None):
    """Get conversation history"""
    manager = get_conversation_manager()
    return manager.get_conversation_history(limit)

def clear_conversation_history():
    """Clear conversation history"""
    manager = get_conversation_manager()
    return manager.clear_history()
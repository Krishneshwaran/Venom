"""
Memory Module
Handles long-term memory storage, search, and retrieval
"""

from config import Config
from utils import load_json_file, save_json_file, get_timestamp, log_success, log_error

class MemorySystem:
    """Memory storage and retrieval system"""
    
    def __init__(self):
        self.memory_file = Config.MEMORY_FILE
    
    def save_memory(self, memory_text, context=""):
        """
        Save a memory
        
        Args:
            memory_text: The memory content to save
            context: Additional context (optional)
        
        Returns:
            Boolean indicating success
        """
        try:
            memories = load_json_file(self.memory_file, default=[])
            
            memory_entry = {
                "id": len(memories) + 1,
                "timestamp": get_timestamp(),
                "memory": memory_text,
                "context": context
            }
            
            memories.append(memory_entry)
            
            if save_json_file(self.memory_file, memories):
                log_success(f"Memory saved to {self.memory_file}")
                return True
            return False
        
        except Exception as e:
            log_error(f"Error saving memory: {e}")
            return False
    
    def search_memories(self, query):
        """
        Search for relevant memories
        
        Args:
            query: Search query
        
        Returns:
            List of relevant memories sorted by relevance
        """
        try:
            memories = load_json_file(self.memory_file, default=[])
            
            if not memories:
                return []
            
            query_lower = query.lower()
            query_words = query_lower.split()
            relevant_memories = []
            
            for memory in memories:
                memory_text = memory.get('memory', '').lower()
                match_count = sum(1 for word in query_words if word in memory_text)
                
                if match_count > 0:
                    memory['match_score'] = match_count
                    relevant_memories.append(memory)
            
            # Sort by match score
            relevant_memories.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            return relevant_memories
        
        except Exception as e:
            log_error(f"Error searching memories: {e}")
            return []
    
    def get_all_memories(self):
        """Get all memories"""
        return load_json_file(self.memory_file, default=[])
    
    def delete_memory(self, memory_id):
        """Delete a memory by ID"""
        try:
            memories = load_json_file(self.memory_file, default=[])
            memories = [m for m in memories if m.get('id') != memory_id]
            
            if save_json_file(self.memory_file, memories):
                log_success(f"Memory {memory_id} deleted")
                return True
            return False
        
        except Exception as e:
            log_error(f"Error deleting memory: {e}")
            return False
    
    def build_memory_context(self, query, max_memories=5):
        """
        Build memory context string for AI
        
        Args:
            query: Query to search memories for
            max_memories: Maximum number of memories to include
        
        Returns:
            Formatted memory context string
        """
        relevant_memories = self.search_memories(query)
        
        if not relevant_memories:
            return ""
        
        context = "\n\nRELEVANT MEMORIES:\n"
        for mem in relevant_memories[:max_memories]:
            context += f"- {mem.get('memory', '')}\n"
        context += "\nUse these memories to answer if relevant."
        
        return context

def is_memory_command(text):
    """Check if text is a memory command (English + Tamil support)"""
    text_lower = text.lower()
    
    # English save triggers
    save_triggers_en = ['remember this', 'remember that', 'save this', 'note this',
                        'keep this in mind', 'don\'t forget', 'make a note', 'memorize this',
                        'remember my', 'remember i', 'remember']
    
    # Tamil save triggers (நினைவு = memory, நினைவில் வை = remember, ஞாபகம் = memory)
    save_triggers_ta = ['நினைவு', 'நினைவில்', 'ஞாபகம்', 'ஞாபகத்தில்', 
                        'neyabagam', 'niyabagam', 'nyabagam', 'nenjil', 
                        'marakadha', 'marakatha', 'vachuko', 'vachu']
    
    # English recall triggers
    recall_triggers_en = ['what do you remember', 'do you remember', 'recall',
                         'what did i tell you', 'remind me about', 'what do you know about',
                         'tell me what you remember', 'what\'s my', 'what is my']
    
    # Tamil recall triggers
    recall_triggers_ta = ['என்ன நினைவு', 'நினைவு இருக்கா', 'நினைவு உள்ளதா',
                         'enna neyabagam', 'enna nyabagam', 'neyabagam iruka',
                         'niyabagam irukka', 'solluda', 'sollu']
    
    # Check save triggers
    for trigger in save_triggers_en + save_triggers_ta:
        if trigger in text_lower:
            return "save"
    
    # Check recall triggers
    for trigger in recall_triggers_en + recall_triggers_ta:
        if trigger in text_lower:
            return "recall"
    
    return None

def extract_memory_content(text):
    """Extract what user wants to remember from command (English + Tamil support)"""
    text_lower = text.lower()
    memory_text = ""
    
    # English patterns
    if 'my name is' in text_lower:
        parts = text_lower.split('my name is')
        if len(parts) > 1:
            memory_text = f"User's name is {parts[1].strip()}"
    elif 'my name as' in text_lower:
        parts = text_lower.split('my name as')
        if len(parts) > 1:
            memory_text = f"User's name is {parts[1].strip()}"
    elif 'my card number' in text_lower or 'card number' in text_lower:
        parts = text_lower.split('card number')
        if len(parts) > 1:
            memory_text = f"User's card number: {parts[1].replace('is', '').strip()}"
    
    # Tamil patterns (என் பெயர் = my name, என் card = my card)
    elif 'என் பெயர்' in text or 'en peyar' in text_lower or 'yen peyar' in text_lower:
        # Extract name after "என் பெயர்" or "en peyar"
        if 'என் பெயர்' in text:
            parts = text.split('என் பெயர்')
        elif 'en peyar' in text_lower:
            parts = text_lower.split('en peyar')
        elif 'yen peyar' in text_lower:
            parts = text_lower.split('yen peyar')
        
        if len(parts) > 1:
            name = parts[1].strip()
            memory_text = f"User's name is {name}"
    
    elif 'card number' in text_lower or 'கார்டு எண்' in text:
        # Extract card number
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            memory_text = f"User's card number: {' '.join(numbers)}"
    
    return memory_text

def needs_visual_context(text):
    """Check if memory command needs camera for context (English + Tamil support)"""
    text_lower = text.lower()
    
    # English visual keywords
    visual_keywords_en = ['keeping', 'kept', 'placed', 'put', 'this', 'that', 'here', 'there',
                         'mobile', 'phone', 'laptop', 'keys', 'wallet', 'bottle', 'cup', 'book',
                         'where', 'location', 'position', 'bike', 'car', 'bag', 'watch']
    
    # Tamil visual keywords (வை = put, இங்கே = here, அங்கே = there, எங்கே = where)
    visual_keywords_ta = ['வை', 'வைத்து', 'வச்சு', 'இங்கே', 'அங்கே', 'எங்கே',
                         'மொபைல்', 'போன்', 'லேப்டாப்', 'சாவி', 'பணப்பை',
                         'vachu', 'vachitu', 'vachchu', 'inge', 'ange', 'enge',
                         'mobile', 'phone', 'laptop', 'chavi', 'saavi', 'key']
    
    has_visual_keyword = any(keyword in text_lower for keyword in visual_keywords_en + visual_keywords_ta)
    
    # Check if command is too vague (needs camera)
    text_without_trigger = text_lower
    for trigger in ['remember', 'நினைவு', 'ஞாபகம்', 'neyabagam', 'nyabagam', 
                   'i am', 'this', 'that', 'இது', 'அது', 'idhu', 'adhu']:
        text_without_trigger = text_without_trigger.replace(trigger, '')
    
    text_without_trigger = text_without_trigger.strip()
    is_vague = len(text_without_trigger) < 5
    
    return has_visual_keyword or is_vague

# Global memory system instance
_memory_system = None

def get_memory_system():
    """Get or create memory system instance"""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system

def save_memory(memory_text, context=""):
    """Save a memory"""
    system = get_memory_system()
    return system.save_memory(memory_text, context)

def search_memories(query):
    """Search memories"""
    system = get_memory_system()
    return system.search_memories(query)

def build_memory_context(query, max_memories=5):
    """Build memory context for AI"""
    system = get_memory_system()
    return system.build_memory_context(query, max_memories)
"""
Venom AI Assistant - Core Module
Main application that orchestrates all modules
"""

import cv2
import time
from datetime import datetime, timedelta

# Import all modules
from config import Config
from utils import log_success, log_error, log_info, log_warning
from tts_module import speak
from voice_module import start_voice_listener, get_voice_command, set_processing_state, get_voice_listener
from api_server import get_api_server
from vision_module import (
    initialize_camera, capture_frame, get_current_frame, 
    save_frame, is_camera_available, get_vision_system
)
from ai_module import ask_ai, ask_ai_text
from memory_module import (
    is_memory_command, extract_memory_content, needs_visual_context,
    save_memory, search_memories, build_memory_context
)
from reminder_module import (
    start_reminder_system, is_reminder_command, extract_reminder_parts,
    parse_time_duration, save_reminder, get_reminder_system
)
from security_module import (
    is_leaving_home_command, save_owner_face, activate_security,
    start_security_monitoring, is_security_active
)
from conversation_module import save_conversation, is_command

class VenomAssistant:
    """Main Venom AI Assistant"""
    
    def __init__(self):
        self.running = False
        self.processing_command = False
        
        # Print configuration
        Config.print_config()
    
    def initialize(self):
        """Initialize all systems"""
        log_info("=" * 50)
        log_info("INITIALIZING VENOM AI ASSISTANT")
        log_info("=" * 50)
        
        # Start API server for frontend communication
        get_api_server()
        
        # Start voice listener
        start_voice_listener()
        
        # Start reminder system
        start_reminder_system()
        
        # Initialize camera
        camera_init = initialize_camera()
        
        if camera_init:
            # Start security monitoring if camera available
            vision = get_vision_system()
            start_security_monitoring(vision.cap)
        else:
            log_warning("Starting in TEXT-ONLY mode (no camera)")
            speak("No camera found, but I can still help you out. Just describe what you need!")
        
        log_success("Venom AI Assistant initialized successfully!")
        speak("Say 'dei venom' unnaku venumdra appo")
        
        return camera_init
    
    def handle_memory_command(self, text, memory_cmd):
        """Handle memory save/recall commands"""
        if memory_cmd == "save":
            memory_text = extract_memory_content(text)
            user_context = text
            needs_camera = needs_visual_context(text)
            
            # Use camera if needed
            if (needs_camera or not memory_text) and is_camera_available():
                frame = get_current_frame()
                if frame is not None:
                    log_info("📸 Analyzing scene with camera for memory...")
                    
                    vision = get_vision_system()
                    img = vision.frame_to_pil(frame)
                    save_frame(frame, "memory")
                    
                    img = img.resize((256, 256))
                    img_b64 = vision.encode_image(img)
                    
                    prompt = f"The user said: '{text}'. Analyze the image and describe what they want you to remember. Include what object it is and where it's located. Be specific and concise (1-2 sentences)."
                    memory_text = ask_ai(img_b64, prompt)
                    memory_text = memory_text.strip()
            
            # Save memory
            if memory_text and save_memory(memory_text, f"User said: {user_context}"):
                answer = "Got it! I'll remember that."
            else:
                answer = "Sorry, I couldn't save that memory."
            
            return answer
        
        elif memory_cmd == "recall":
            relevant_memories = search_memories(text)
            
            if relevant_memories and is_camera_available():
                frame = get_current_frame()
                if frame is not None:
                    log_info("📸 Processing frame with memory context...")
                    
                    vision = get_vision_system()
                    img = vision.frame_to_pil(frame)
                    save_frame(frame, "captured")
                    
                    img = img.resize((256, 256))
                    img_b64 = vision.encode_image(img)
                    
                    memory_context = build_memory_context(text)
                    answer = ask_ai(img_b64, f"{text}{memory_context}\n\nAnswer the question naturally using these memories.")
                else:
                    memory_text = ", ".join([mem['memory'] for mem in relevant_memories[:3]])
                    answer = f"Based on what I remember: {memory_text}"
            elif relevant_memories:
                memory_text = ", ".join([mem['memory'] for mem in relevant_memories[:3]])
                answer = f"Based on what I remember: {memory_text}"
            else:
                answer = "I don't have any memories matching that. Try asking me to remember something first!"
            
            return answer
        
        return None
    
    def handle_reminder_command(self, text):
        """Handle reminder commands"""
        reminder_system = get_reminder_system()
        pending = reminder_system.get_pending_reminder()
        
        if pending["waiting_for"] == "task":
            reminder_system.set_pending_task(text)
            return "Got it! When should I remind you? Say something like '5 minutes' or '10 minutes'."
        
        elif pending["waiting_for"] == "time":
            duration_seconds = parse_time_duration(text)
            if duration_seconds:
                remind_time = datetime.now() + timedelta(seconds=duration_seconds)
                task = pending["task"]
                
                if save_reminder(task, remind_time):
                    minutes = duration_seconds / 60
                    if minutes < 1:
                        time_str = f"{duration_seconds} seconds"
                    elif minutes < 60:
                        time_str = f"{int(minutes)} minutes"
                    else:
                        time_str = f"{minutes/60:.1f} hours"
                    answer = f"Reminder set! I'll remind you about '{task}' in {time_str}."
                else:
                    answer = "Sorry, I couldn't set the reminder."
            else:
                answer = "I didn't understand the time. Try saying '5 minutes' or '10 minutes'."
            
            reminder_system.clear_pending()
            return answer
        
        else:
            # New reminder request
            task, duration_seconds = extract_reminder_parts(text)
            
            if task and duration_seconds:
                remind_time = datetime.now() + timedelta(seconds=duration_seconds)
                
                if save_reminder(task, remind_time):
                    minutes = duration_seconds / 60
                    if minutes < 1:
                        time_str = f"{duration_seconds} seconds"
                    elif minutes < 60:
                        time_str = f"{int(minutes)} minutes"
                    else:
                        time_str = f"{minutes/60:.1f} hours"
                    answer = f"Reminder set! I'll remind you to {task} in {time_str}."
                else:
                    answer = "Sorry, I couldn't set the reminder."
            else:
                reminder_system.start_pending()
                answer = "Sure! What should I remind you about?"
            
            return answer
    
    def handle_security_command(self, text):
        """Handle security/leaving home commands"""
        frame = get_current_frame()
        
        if is_camera_available() and frame is not None:
            if save_owner_face(frame):
                activate_security()
                return "Got it! Your face is registered. I'll watch for strangers while you're away. Stay safe!"
            else:
                return "I couldn't register your face. Please try again with better lighting."
        else:
            return "Camera not available. I can't enable security mode without seeing you."
    
    def handle_vision_question(self, text):
        """Handle questions requiring vision"""
        frame = get_current_frame()
        
        if not is_camera_available() or frame is None:
            return "I heard: '{}'. Since camera is not available, I can help with general advice. Please describe what you need help with in more detail.".format(text)
        
        log_info("📸 Processing frame...")
        
        vision = get_vision_system()
        img = vision.frame_to_pil(frame)
        save_frame(frame, "captured")
        
        # Resize for faster processing
        img = img.resize((256, 256))
        img_b64 = vision.encode_image(img)
        
        # Add memory context
        memory_context = build_memory_context(text)
        
        # Get AI response
        answer = ask_ai(img_b64, text, memory_context)
        answer = answer.strip()
        answer = answer.replace('\n', ' ').replace('  ', ' ')
        
        return answer
    
    def process_command(self, text):
        """Process a voice command"""
        log_info(f"📥 Processing command: '{text}'")
        self.processing_command = True
        set_processing_state(True)
        
        try:
            # Check for security command
            if is_leaving_home_command(text):
                answer = self.handle_security_command(text)
                log_info(f"🤖 AI RESPONSE: {answer}")
                save_conversation(text, answer)
                speak(answer)
                return
            
            # Check for reminder command
            reminder_system = get_reminder_system()
            pending = reminder_system.get_pending_reminder()
            
            if is_reminder_command(text) or pending["waiting_for"] is not None:
                answer = self.handle_reminder_command(text)
                log_info(f"🤖 AI RESPONSE: {answer}")
                save_conversation(text, answer)
                speak(answer)
                return
            
            # Check for memory command
            memory_cmd = is_memory_command(text)
            if memory_cmd:
                answer = self.handle_memory_command(text, memory_cmd)
                log_info(f"🤖 AI RESPONSE: {answer}")
                save_conversation(text, answer)
                speak(answer)
                return
            
            # Handle regular vision question
            answer = self.handle_vision_question(text)
            log_info(f"🤖 AI RESPONSE: {answer}")
            save_conversation(text, answer)
            speak(answer)
        
        finally:
            # Reset flags
            self.processing_command = False
            set_processing_state(False)
            
            # Keep listening active
            listener = get_voice_listener()
            listener.activate_listening()
            
            log_success("✅ Ready for next command.")
    
    def run(self):
        """Main application loop"""
        camera_available = self.initialize()
        self.running = True
        
        log_info("=" * 50)
        log_info("VENOM AI ASSISTANT RUNNING")
        log_info("=" * 50)
        
        try:
            while self.running:
                # Capture and display camera feed if available
                if camera_available:
                    frame = capture_frame()
                    
                    if frame is not None:
                        # Add processing overlay
                        if self.processing_command:
                            cv2.putText(frame, "PROCESSING YOUR REQUEST...", (10, 30),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            cv2.putText(frame, "Voice listening paused", (10, 60),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        
                        cv2.imshow('Camera Feed - Say "hey venom" to activate', frame)
                    
                    # Check for quit key
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    # Text-only mode - just wait
                    time.sleep(0.1)
                
                # Check for voice commands
                command = get_voice_command(block=False)
                if command:
                    self.process_command(command)
        
        except KeyboardInterrupt:
            log_warning("Keyboard interrupt received")
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all systems"""
        log_info("Shutting down Venom AI Assistant...")
        
        vision = get_vision_system()
        vision.release_camera()
        
        log_success("✅ Application closed")

def main():
    """Entry point"""
    assistant = VenomAssistant()
    assistant.run()

if __name__ == "__main__":
    main()
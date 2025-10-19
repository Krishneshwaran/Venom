"""
Security Module
Handles face recognition, owner identification, and intruder detection
"""

import os
import cv2
import time
import pickle
import threading
import face_recognition
from config import Config
from utils import log_success, log_error, log_warning
from tts_module import speak

class SecuritySystem:
    """Home security system with face recognition"""
    
    def __init__(self):
        self.owner_face_encoding = None
        self.home_security_active = False
        self.last_face_check_time = 0
        self.last_alert_time = 0
        self.shutdown_flag = False
        self.load_owner_face()
    
    def save_owner_face(self, frame):
        """
        Save owner's face encoding from frame
        
        Args:
            frame: OpenCV frame containing owner's face
        
        Returns:
            Boolean indicating success
        """
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                log_error("No face detected in frame")
                return False
            
            if len(face_locations) > 1:
                log_warning("Multiple faces detected, using the largest one")
            
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            if face_encodings:
                self.owner_face_encoding = face_encodings[0]
                
                with open(Config.FACE_DATA_FILE, 'wb') as f:
                    pickle.dump(self.owner_face_encoding, f)
                
                log_success("Owner face registered successfully")
                return True
            else:
                log_error("Could not encode face")
                return False
        
        except Exception as e:
            log_error(f"Error saving owner face: {e}")
            return False
    
    def load_owner_face(self):
        """Load owner's face encoding from file"""
        try:
            if os.path.exists(Config.FACE_DATA_FILE):
                with open(Config.FACE_DATA_FILE, 'rb') as f:
                    self.owner_face_encoding = pickle.load(f)
                log_success("Owner face loaded from file")
                return True
            else:
                log_warning("No owner face registered yet")
                return False
        
        except Exception as e:
            log_error(f"Error loading owner face: {e}")
            return False
    
    def check_for_faces(self, frame):
        """
        Check frame for faces and identify owner vs stranger
        
        Args:
            frame: OpenCV frame
        
        Returns:
            "owner", "stranger", or None
        """
        if self.owner_face_encoding is None:
            return None
        
        try:
            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces with HOG (faster)
            face_locations = face_recognition.face_locations(rgb_frame, model="hog", number_of_times_to_upsample=0)
            
            if not face_locations:
                return None
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)
            
            if not face_encodings:
                return None
            
            # Check first face only
            face_encoding = face_encodings[0]
            face_distance = face_recognition.face_distance([self.owner_face_encoding], face_encoding)[0]
            
            if face_distance < Config.FACE_RECOGNITION_THRESHOLD:
                print(f"✓ Owner detected (distance: {face_distance:.2f})")
                return "owner"
            else:
                print(f"✗ Stranger detected (distance: {face_distance:.2f})")
                return "stranger"
        
        except Exception as e:
            log_error(f"Error checking faces: {e}")
            return None
    
    def monitor_faces_background(self, cap):
        """Background thread to monitor for strangers"""
        log_success("Face monitoring started...")
        
        owner_left = False
        owner_welcomed = False
        no_face_time = None
        detection_count = {"owner": 0, "stranger": 0}
        
        while not self.shutdown_flag:
            try:
                if self.home_security_active and cap is not None:
                    current_time = time.time()
                    
                    if current_time - self.last_face_check_time >= Config.FACE_CHECK_INTERVAL:
                        try:
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                result = self.check_for_faces(frame)
                                
                                if result == "stranger":
                                    detection_count["stranger"] += 1
                                    detection_count["owner"] = 0
                                    print(f"🚨 Stranger count: {detection_count['stranger']}/1")
                                    
                                    if detection_count["stranger"] >= 1:
                                        if current_time - self.last_alert_time >= Config.ALERT_COOLDOWN:
                                            print("\n🚨 STRANGER DETECTED!")
                                            speak("Alert! Stranger intruded!")
                                            self.last_alert_time = current_time
                                            owner_welcomed = False
                                            owner_left = True
                                            no_face_time = None
                                            detection_count["stranger"] = 0
                                
                                elif result == "owner":
                                    detection_count["owner"] += 1
                                    detection_count["stranger"] = 0
                                    print(f"👋 Owner count: {detection_count['owner']}/3")
                                    no_face_time = None
                                    
                                    if detection_count["owner"] >= 3:
                                        if owner_left and not owner_welcomed:
                                            print("\n👋 OWNER DETECTED!")
                                            speak("Welcome back, bro!")
                                            owner_welcomed = True
                                            owner_left = False
                                            self.home_security_active = False
                                            print("🏠 Security monitoring paused. Say 'I am leaving home' to activate again.")
                                            detection_count = {"owner": 0, "stranger": 0}
                                            break
                                
                                else:  # No face
                                    detection_count["owner"] = 0
                                    detection_count["stranger"] = 0
                                    
                                    if no_face_time is None:
                                        no_face_time = current_time
                                    elif current_time - no_face_time >= 5:
                                        if not owner_left:
                                            print("👤 No face detected for 5 seconds - Owner considered left")
                                            owner_left = True
                                            owner_welcomed = False
                            else:
                                log_warning("Failed to read frame from camera")
                        
                        except Exception as frame_error:
                            log_error(f"Error processing frame: {frame_error}")
                        
                        self.last_face_check_time = current_time
                
                time.sleep(1)
            
            except Exception as e:
                log_error(f"Error in face monitoring: {e}")
                time.sleep(2)
    
    def start_monitoring(self, cap):
        """Start face monitoring in background"""
        monitor_thread = threading.Thread(target=self.monitor_faces_background, args=(cap,), daemon=True)
        monitor_thread.start()
        log_success("Face monitoring system active")
    
    def activate_security(self):
        """Activate security mode"""
        self.home_security_active = True
        log_success("Security monitoring ACTIVATED - Watching for intruders...")
    
    def deactivate_security(self):
        """Deactivate security mode"""
        self.home_security_active = False
        log_success("Security monitoring DEACTIVATED")
    
    def is_active(self):
        """Check if security is active"""
        return self.home_security_active
    
    def shutdown(self):
        """Shutdown security system"""
        self.shutdown_flag = True

def is_leaving_home_command(text):
    """Check if user is leaving home"""
    text_lower = text.lower()
    triggers = ['i am leaving', 'i\'m leaving', 'leaving home', 'going out',
                'i am going out', 'i\'m going out']
    
    for trigger in triggers:
        if trigger in text_lower:
            return True
    return False

# Global security system instance
_security_system = None

def get_security_system():
    """Get or create security system instance"""
    global _security_system
    if _security_system is None:
        _security_system = SecuritySystem()
    return _security_system

def start_security_monitoring(cap):
    """Start security monitoring"""
    system = get_security_system()
    system.start_monitoring(cap)

def save_owner_face(frame):
    """Save owner's face"""
    system = get_security_system()
    return system.save_owner_face(frame)

def activate_security():
    """Activate security mode"""
    system = get_security_system()
    system.activate_security()

def is_security_active():
    """Check if security is active"""
    system = get_security_system()
    return system.is_active()
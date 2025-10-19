"""
Vision Module
Handles camera operations, frame capture, and image processing
"""

import cv2
import base64
import io
from PIL import Image
from config import Config
from utils import ensure_directory, get_filename_timestamp, log_success, log_error, log_warning

class VisionSystem:
    """Camera and image processing system"""
    
    def __init__(self):
        self.cap = None
        self.camera_available = False
        self.camera_error_count = 0
        self.current_frame = None
        ensure_directory(Config.IMAGES_DIR)
    
    def initialize_camera(self):
        """Initialize camera"""
        try:
            self.cap = cv2.VideoCapture(0)
            
            if self.cap.isOpened():
                # Test camera
                ret, test_frame = self.cap.read()
                if ret:
                    self.camera_available = True
                    log_success("Camera initialized successfully")
                    return True
                else:
                    log_warning("Camera opened but cannot capture frames")
                    self.cap.release()
                    self.cap = None
            else:
                log_error("Could not open camera. Check permissions and connections.")
            
            return False
        
        except Exception as e:
            log_error(f"Camera initialization error: {e}")
            return False
    
    def capture_frame(self):
        """Capture a single frame from camera"""
        if not self.camera_available or self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret:
                self.camera_error_count = 0
                self.current_frame = frame
                return frame
            else:
                self.camera_error_count += 1
                log_warning(f"Camera frame grab failed ({self.camera_error_count}/5)")
                
                if self.camera_error_count >= 5:
                    log_error("Camera failed 5 times. Switching to text-only mode...")
                    self.camera_available = False
                    if self.cap:
                        self.cap.release()
                        self.cap = None
                
                return None
        
        except Exception as e:
            log_error(f"Frame capture error: {e}")
            return None
    
    def get_current_frame(self):
        """Get the last captured frame"""
        return self.current_frame
    
    def save_frame(self, frame, prefix="captured"):
        """Save frame to disk"""
        try:
            timestamp = get_filename_timestamp()
            filename = f"{prefix}_{timestamp}.png"
            filepath = f"{Config.IMAGES_DIR}/{filename}"
            
            cv2.imwrite(filepath, frame)
            log_success(f"Image saved: {filepath}")
            return filepath
        
        except Exception as e:
            log_error(f"Failed to save frame: {e}")
            return None
    
    def frame_to_pil(self, frame):
        """Convert OpenCV frame to PIL Image"""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame_rgb)
        except Exception as e:
            log_error(f"Frame conversion error: {e}")
            return None
    
    def encode_image(self, image, max_size_mb=4, quality=85):
        """
        Encode PIL Image to base64 string
        
        Args:
            image: PIL Image
            max_size_mb: Maximum size in MB
            quality: JPEG quality (1-100)
        
        Returns:
            Base64 encoded string
        """
        try:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality)
            size_mb = len(buffer.getvalue()) / (1024 * 1024)
            
            if size_mb > max_size_mb:
                # Resize and try again
                image = image.resize((640, 480))
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality)
            
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        except Exception as e:
            log_error(f"Image encoding error: {e}")
            return None
    
    def show_frame(self, frame, window_name="Camera Feed"):
        """Display frame in OpenCV window"""
        try:
            cv2.imshow(window_name, frame)
        except Exception as e:
            log_error(f"Failed to show frame: {e}")
    
    def is_camera_available(self):
        """Check if camera is available"""
        return self.camera_available
    
    def release_camera(self):
        """Release camera resources"""
        if self.cap:
            self.cap.release()
            log_success("Camera released")
        cv2.destroyAllWindows()

# Global vision system instance
_vision_system = None

def get_vision_system():
    """Get or create vision system instance"""
    global _vision_system
    if _vision_system is None:
        _vision_system = VisionSystem()
    return _vision_system

def initialize_camera():
    """Initialize the camera"""
    vision = get_vision_system()
    return vision.initialize_camera()

def capture_frame():
    """Capture a frame"""
    vision = get_vision_system()
    return vision.capture_frame()

def get_current_frame():
    """Get current frame"""
    vision = get_vision_system()
    return vision.get_current_frame()

def save_frame(frame, prefix="captured"):
    """Save a frame"""
    vision = get_vision_system()
    return vision.save_frame(frame, prefix)

def is_camera_available():
    """Check camera availability"""
    vision = get_vision_system()
    return vision.is_camera_available()
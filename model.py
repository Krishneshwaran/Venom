import requests
import cv2
import time
import sys
import numpy as np
import mediapipe as mp

# ==== CONFIGURATION ====
# Replace with your ESP32's IP address
ESP32_IP = "192.168.97.10"  # CHANGE THIS TO YOUR ESP32 IP
BASE_URL = f"http://{ESP32_IP}"

# Camera configuration
CAMERA_INDEX = 0  # 0 for default webcam, 1 for external camera

# Detection thresholds
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for face detection
CENTER_TOLERANCE = 100  # Pixels from center before turning
DISTANCE_THRESHOLD = 250  # Pixel height threshold - stop if face is too close
MIN_DETECTION_SIZE = 50  # Minimum face size to consider

# Speed settings
SPEED_NORMAL = 70
SPEED_APPROACH = 55
SPEED_SEARCH = 40

# ==== CONTROL FUNCTIONS ====
def send_command(cmd):
    """Send a command to the ESP32"""
    try:
        response = requests.get(f"{BASE_URL}/{cmd}", timeout=0.5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def set_speed(speed):
    """Set motor speed (0-100)"""
    try:
        response = requests.get(f"{BASE_URL}/speed?value={speed}", timeout=0.5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def forward():
    send_command('R')  # Adjusted for your wiring

def backward():
    send_command('L')  # Adjusted for your wiring

def left():
    send_command('F')  # Adjusted for your wiring

def right():
    send_command('B')  # Adjusted for your wiring

def stop():
    send_command('S')

# ==== MEDIAPIPE FACE DETECTION SETUP ====
def initialize_mediapipe():
    """Initialize MediaPipe face detection"""
    print("\n🚀 Initializing MediaPipe Face Detection...")
    
    try:
        mp_face_detection = mp.solutions.face_detection
        mp_drawing = mp.solutions.drawing_utils
        
        # Create face detection object
        # model_selection: 0 for short-range (2m), 1 for full-range (5m+)
        face_detection = mp_face_detection.FaceDetection(
            model_selection=1,  # Full-range model
            min_detection_confidence=CONFIDENCE_THRESHOLD
        )
        
        print("✅ MediaPipe Face Detection loaded successfully!")
        print("   - Model: Full-range (detects up to 5+ meters)")
        print("   - Confidence threshold:", CONFIDENCE_THRESHOLD)
        print("   - Fast and reliable")
        print("   - Works in various lighting conditions\n")
        
        return {
            'detector': face_detection,
            'mp_face_detection': mp_face_detection,
            'mp_drawing': mp_drawing
        }
        
    except Exception as e:
        print(f"❌ Error initializing MediaPipe: {e}")
        print("\nPlease install MediaPipe:")
        print("  pip install mediapipe")
        return None

def detect_faces_mediapipe(frame, mp_model):
    """Detect faces using MediaPipe"""
    
    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Process the frame
    results = mp_model['detector'].process(rgb_frame)
    
    detections = []
    
    if results.detections:
        h, w = frame.shape[:2]
        
        for detection in results.detections:
            # Get bounding box
            bbox = detection.location_data.relative_bounding_box
            
            # Convert to pixel coordinates
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            box_w = int(bbox.width * w)
            box_h = int(bbox.height * h)
            
            # Get confidence score
            confidence = detection.score[0]
            
            # Filter out small detections
            if box_w > MIN_DETECTION_SIZE and box_h > MIN_DETECTION_SIZE:
                detections.append({
                    'bbox': (x, y, box_w, box_h),
                    'confidence': confidence,
                    'type': 'face',
                    'center': (x + box_w // 2, y + box_h // 2),
                    'keypoints': detection.location_data.relative_keypoints if hasattr(detection.location_data, 'relative_keypoints') else None
                })
    
    return detections

# ==== NAVIGATION LOGIC ====
def calculate_movement(detections, frame_width, frame_height):
    """Calculate which direction to move based on detected faces"""
    if not detections:
        return 'SEARCH', None
    
    # Find the largest/closest face
    largest_face = max(detections, key=lambda d: d['bbox'][2] * d['bbox'][3])
    x, y, w, h = largest_face['bbox']
    
    # Get center
    person_center_x, person_center_y = largest_face['center']
    
    # Calculate frame center
    frame_center_x = frame_width // 2
    
    # Check if face is too close
    if h > DISTANCE_THRESHOLD:
        return 'STOP', largest_face
    
    # Determine horizontal alignment
    offset = person_center_x - frame_center_x
    
    if abs(offset) < CENTER_TOLERANCE:
        return 'FORWARD', largest_face
    elif offset < 0:
        return 'LEFT', largest_face
    else:
        return 'RIGHT', largest_face

def execute_movement(action, current_speed):
    """Execute the movement command"""
    if action == 'FORWARD':
        set_speed(SPEED_APPROACH)
        forward()
        print("🚗 Moving forward towards person")
    elif action == 'LEFT':
        set_speed(SPEED_NORMAL)
        left()
        print("↶ Turning left")
    elif action == 'RIGHT':
        set_speed(SPEED_NORMAL)
        right()
        print("↷ Turning right")
    elif action == 'STOP':
        stop()
        print("⏹ Person is close - stopping")
    elif action == 'SEARCH':
        stop()
        print("👁 Searching for people...")

# ==== MAIN TRACKING LOOP ====
def human_tracking_mode():
    """Main mode - track and follow humans using face detection"""
    print("\n" + "="*60)
    print("🤖 ESP32 CAR - MEDIAPIPE FACE TRACKING")
    print("="*60)
    print("\nInitializing camera and detection system...")
    
    # Initialize camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("✅ Camera initialized")
    
    # Initialize MediaPipe face detector
    mp_model = initialize_mediapipe()
    if mp_model is None:
        print("❌ Failed to initialize MediaPipe. Exiting...")
        cap.release()
        return
    
    print("\n" + "="*60)
    print("Controls:")
    print("  Q - Quit")
    print("  S - Manual Stop")
    print("  + - Increase Speed")
    print("  - - Decrease Speed")
    print("  P - Pause/Resume tracking")
    print("  D - Toggle debug info")
    print("="*60 + "\n")
    
    # Set initial speed
    current_speed = SPEED_APPROACH
    set_speed(current_speed)
    
    last_action = None
    fps_time = time.time()
    fps_counter = 0
    fps = 0
    paused = False
    show_debug = True
    
    print("🎬 Starting face tracking... Point camera at people!\n")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to grab frame")
                break
            
            # Flip frame horizontally for mirror view
            frame = cv2.flip(frame, 1)
            frame_height, frame_width = frame.shape[:2]
            
            if not paused:
                # Detect faces
                detections = detect_faces_mediapipe(frame, mp_model)
                
                # Calculate movement
                action, target = calculate_movement(detections, frame_width, frame_height)
                
                # Execute movement
                if action != last_action:
                    execute_movement(action, current_speed)
                    last_action = action
            else:
                detections = []
                target = None
            
            # Draw detections
            for detection in detections:
                x, y, w, h = detection['bbox']
                conf = detection['confidence']
                
                # Draw bounding box
                is_target = (detection == target)
                color = (0, 255, 0) if is_target else (255, 100, 100)
                thickness = 3 if is_target else 2
                
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
                
                # Draw label
                label = f"Face {conf*100:.1f}%"
                if is_target:
                    label = f"TARGET: {label}"
                
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (x, y - label_size[1] - 10), 
                            (x + label_size[0], y), color, -1)
                cv2.putText(frame, label, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                
                # Draw center point
                center_x, center_y = detection['center']
                cv2.circle(frame, (center_x, center_y), 5, (0, 255, 255), -1)
                
                # Draw line to center for target
                if is_target:
                    cv2.line(frame, (center_x, center_y), 
                            (frame_width // 2, frame_height // 2), (0, 255, 0), 2)
            
            # Draw center line
            cv2.line(frame, (frame_width // 2, 0), 
                    (frame_width // 2, frame_height), (0, 255, 255), 2)
            
            # Draw center tolerance zone
            left_bound = frame_width // 2 - CENTER_TOLERANCE
            right_bound = frame_width // 2 + CENTER_TOLERANCE
            cv2.rectangle(frame, (left_bound, 0), (right_bound, frame_height), 
                         (255, 255, 0), 2)
            
            # Calculate FPS
            fps_counter += 1
            if time.time() - fps_time > 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_time = time.time()
            
            # Display info overlay
            if show_debug:
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (300, 150), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
                
                info_text = [
                    f"FPS: {fps}",
                    f"Model: MediaPipe",
                    f"Action: {last_action if not paused else 'PAUSED'}",
                    f"Speed: {current_speed}%",
                    f"Faces: {len(detections)}",
                    f"Conf: {CONFIDENCE_THRESHOLD}"
                ]
                
                y_offset = 25
                for text in info_text:
                    cv2.putText(frame, text, (10, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    y_offset += 23
            
            # Status indicator
            status_color = (0, 255, 0) if detections else (0, 0, 255)
            cv2.circle(frame, (frame_width - 30, 30), 15, status_color, -1)
            cv2.putText(frame, "ACTIVE" if detections else "SEARCH", 
                       (frame_width - 90, 35), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.4, (255, 255, 255), 1)
            
            # Pause indicator
            if paused:
                cv2.putText(frame, "PAUSED", (frame_width // 2 - 50, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            
            # Show frame
            cv2.imshow('ESP32 Face Tracking - MediaPipe', frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n🛑 Quitting...")
                break
            elif key == ord('s'):
                stop()
                print("⏹ Manual stop")
                last_action = 'STOP'
            elif key == ord('p'):
                paused = not paused
                if paused:
                    stop()
                    print("⏸ Tracking paused")
                else:
                    print("▶️ Tracking resumed")
            elif key == ord('d'):
                show_debug = not show_debug
                print(f"🐛 Debug info: {'ON' if show_debug else 'OFF'}")
            elif key == ord('+') or key == ord('='):
                current_speed = min(100, current_speed + 10)
                set_speed(current_speed)
                print(f"⚡ Speed increased to {current_speed}%")
            elif key == ord('-'):
                current_speed = max(0, current_speed - 10)
                set_speed(current_speed)
                print(f"🐌 Speed decreased to {current_speed}%")
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    finally:
        stop()
        mp_model['detector'].close()
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Cleanup complete")

# ==== TEST CONNECTION ====
def test_connection():
    """Test if ESP32 is reachable"""
    print(f"Testing connection to ESP32 at {BASE_URL}...")
    try:
        response = requests.get(BASE_URL, timeout=2)
        if response.status_code == 200:
            print("✅ Connection successful!")
            return True
        else:
            print(f"❌ Connection failed. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to ESP32: {e}")
        print(f"\nMake sure:")
        print(f"  1. ESP32 is powered on")
        print(f"  2. ESP32 is connected to WiFi")
        print(f"  3. Your computer is on the same network")
        print(f"  4. ESP32_IP is set correctly (currently: {ESP32_IP})")
        return False

# ==== MAIN ====
def main():
    print("\n" + "="*60)
    print("ESP32 ROBOT CAR - MEDIAPIPE FACE TRACKING")
    print("Powered by Google MediaPipe")
    print("="*60)
    
    # Test connection
    if not test_connection():
        sys.exit(1)
    
    print("\n🎥 Starting MediaPipe face tracking mode...")
    print("✨ Features:")
    print("   - Reliable face detection (up to 5+ meters)")
    print("   - Fast performance (30+ FPS)")
    print("   - No model downloads needed")
    print("   - Works in various lighting conditions")
    print("   - Multi-face detection\n")
    
    time.sleep(1)
    human_tracking_mode()

if __name__ == "__main__":
    main()
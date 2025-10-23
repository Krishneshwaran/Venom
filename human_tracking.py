import requests
import cv2
import time
import sys
import numpy as np

# ==== CONFIGURATION ====
# Replace with your ESP32's IP address
ESP32_IP = "192.168.97.10"  # CHANGE THIS TO YOUR ESP32 IP
BASE_URL = f"http://{ESP32_IP}"

# Camera configuration
CAMERA_INDEX = 0  # 0 for default webcam, 1 for external camera

# Detection thresholds
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for person detection
CENTER_TOLERANCE = 80  # Pixels from center before turning
DISTANCE_THRESHOLD = 200  # Pixel height threshold - stop if person is too close
SPEED_NORMAL = 70
SPEED_APPROACH = 50

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

# ==== HUMAN DETECTION SETUP ====
def initialize_detector():
    """Initialize the human detection model"""
    print("Loading human detection model...")
    
    # Using Haar Cascade for fast detection (alternative: YOLO, MobileNet-SSD)
    # Download from: https://github.com/opencv/opencv/tree/master/data/haarcascades
    
    # Try multiple detection methods
    detectors = {
        'body': 'haarcascade_fullbody.xml',
        'upper': 'haarcascade_upperbody.xml',
        'face': 'haarcascade_frontalface_default.xml'
    }
    
    loaded_detectors = {}
    
    for name, cascade_file in detectors.items():
        try:
            detector = cv2.CascadeClassifier(cv2.data.haarcascades + cascade_file)
            if not detector.empty():
                loaded_detectors[name] = detector
                print(f"✅ Loaded {name} detector")
        except Exception as e:
            print(f"⚠️ Could not load {name} detector: {e}")
    
    if not loaded_detectors:
        print("❌ No detectors loaded! Using HOG detector as fallback...")
        return None
    
    return loaded_detectors

def detect_humans_cascade(frame, detectors):
    """Detect humans using Haar Cascade detectors"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    all_detections = []
    
    # Try each detector
    for name, detector in detectors.items():
        detections = detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        for (x, y, w, h) in detections:
            all_detections.append({
                'bbox': (x, y, w, h),
                'confidence': 1.0,
                'type': name
            })
    
    return all_detections

def detect_humans_hog(frame):
    """Detect humans using HOG detector (backup method)"""
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    
    # Detect people
    boxes, weights = hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
    
    detections = []
    for i, (x, y, w, h) in enumerate(boxes):
        detections.append({
            'bbox': (x, y, w, h),
            'confidence': weights[i][0] if len(weights) > i else 0.5,
            'type': 'hog'
        })
    
    return detections

# ==== NAVIGATION LOGIC ====
def calculate_movement(detections, frame_width, frame_height):
    """
    Calculate which direction to move based on detected humans
    Returns: (action, target_info)
    """
    if not detections:
        return 'SEARCH', None
    
    # Find the largest/closest person (by bounding box area)
    largest_person = max(detections, key=lambda d: d['bbox'][2] * d['bbox'][3])
    x, y, w, h = largest_person['bbox']
    
    # Calculate center of detected person
    person_center_x = x + w // 2
    person_center_y = y + h // 2
    
    # Calculate frame center
    frame_center_x = frame_width // 2
    
    # Check if person is too close (bounding box height too large)
    if h > DISTANCE_THRESHOLD:
        return 'STOP', largest_person
    
    # Determine horizontal alignment
    offset = person_center_x - frame_center_x
    
    if abs(offset) < CENTER_TOLERANCE:
        # Person is centered - move forward
        return 'FORWARD', largest_person
    elif offset < 0:
        # Person is on the left - turn left
        return 'LEFT', largest_person
    else:
        # Person is on the right - turn right
        return 'RIGHT', largest_person

def execute_movement(action):
    """Execute the movement command"""
    if action == 'FORWARD':
        forward()
        print("🚗 Moving forward towards person")
    elif action == 'LEFT':
        left()
        print("↶ Turning left")
    elif action == 'RIGHT':
        right()
        print("↷ Turning right")
    elif action == 'STOP':
        stop()
        print("⏹ Person is close - stopping")
    elif action == 'SEARCH':
        stop()
        print("👁 Searching for humans...")

# ==== MAIN TRACKING LOOP ====
def human_tracking_mode():
    """Main mode - track and follow humans"""
    print("\n" + "="*60)
    print("🤖 ESP32 CAR - HUMAN TRACKING MODE")
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
    
    print("✅ Camera initialized")
    
    # Initialize detectors
    detectors = initialize_detector()
    use_hog = detectors is None
    
    print("\n" + "="*60)
    print("Controls:")
    print("  Q - Quit")
    print("  S - Manual Stop")
    print("  + - Increase Speed")
    print("  - - Decrease Speed")
    print("="*60 + "\n")
    
    # Set initial speed
    current_speed = SPEED_APPROACH
    set_speed(current_speed)
    
    last_action = None
    fps_time = time.time()
    fps_counter = 0
    fps = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to grab frame")
                break
            
            # Flip frame horizontally for mirror view
            frame = cv2.flip(frame, 1)
            frame_height, frame_width = frame.shape[:2]
            
            # Detect humans
            if use_hog:
                detections = detect_humans_hog(frame)
            else:
                detections = detect_humans_cascade(frame, detectors)
            
            # Calculate movement
            action, target = calculate_movement(detections, frame_width, frame_height)
            
            # Execute movement (only if action changed to reduce command spam)
            if action != last_action:
                execute_movement(action)
                last_action = action
            
            # Draw detections and info on frame
            for detection in detections:
                x, y, w, h = detection['bbox']
                conf = detection['confidence']
                
                # Draw bounding box
                color = (0, 255, 0) if detection == target else (255, 0, 0)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                label = f"{detection['type']} ({conf:.2f})"
                cv2.putText(frame, label, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw center line
            cv2.line(frame, (frame_width // 2, 0), 
                    (frame_width // 2, frame_height), (0, 255, 255), 1)
            
            # Draw center tolerance zone
            left_bound = frame_width // 2 - CENTER_TOLERANCE
            right_bound = frame_width // 2 + CENTER_TOLERANCE
            cv2.line(frame, (left_bound, 0), (left_bound, frame_height), (255, 255, 0), 1)
            cv2.line(frame, (right_bound, 0), (right_bound, frame_height), (255, 255, 0), 1)
            
            # Display info
            fps_counter += 1
            if time.time() - fps_time > 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_time = time.time()
            
            info_text = [
                f"FPS: {fps}",
                f"Action: {action}",
                f"Speed: {current_speed}%",
                f"Humans detected: {len(detections)}"
            ]
            
            y_offset = 30
            for text in info_text:
                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                y_offset += 30
            
            # Show frame
            cv2.imshow('Human Tracking - ESP32 Car', frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n🛑 Quitting...")
                break
            elif key == ord('s'):
                stop()
                print("⏹ Manual stop")
                last_action = 'STOP'
            elif key == ord('+') or key == ord('='):
                current_speed = min(100, current_speed + 10)
                set_speed(current_speed)
                print(f"Speed increased to {current_speed}%")
            elif key == ord('-'):
                current_speed = max(0, current_speed - 10)
                set_speed(current_speed)
                print(f"Speed decreased to {current_speed}%")
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    finally:
        stop()
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
    print("ESP32 ROBOT CAR - HUMAN TRACKING SYSTEM")
    print("="*60)
    
    # Test connection
    if not test_connection():
        sys.exit(1)
    
    print("\n🎥 Starting human tracking mode...")
    print("The car will automatically follow detected humans!\n")
    
    time.sleep(1)
    human_tracking_mode()

if __name__ == "__main__":
    main()
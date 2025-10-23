import requests
import cv2
import time
import sys
import numpy as np
from ultralytics import YOLO
import os

# ==== CONFIGURATION ====
# Replace with your ESP32's IP address
ESP32_IP = "192.168.97.10"  # CHANGE THIS TO YOUR ESP32 IP
BASE_URL = f"http://{ESP32_IP}"

# Camera configuration
CAMERA_INDEX = 0  # 0 for default webcam, 1 for external camera

# Model path - UPDATE THIS to where you saved the model
MODEL_PATH = "yolov8m.pt"  # Path to your YOLOv8m model

# Detection thresholds
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for person detection
IOU_THRESHOLD = 0.45  # NMS IoU threshold
CENTER_TOLERANCE = 100  # Pixels from center before turning
DISTANCE_THRESHOLD = 300  # Pixel height threshold - stop if person is too close
MIN_DETECTION_SIZE = 50  # Minimum detection size to consider

# Speed settings
SPEED_NORMAL = 70
SPEED_APPROACH = 55
SPEED_SEARCH = 40

# Detection settings
IMG_SIZE = 640  # Input image size for model
DETECT_PERSON_ONLY = True  # Only detect person class (class 0 in COCO)

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

# ==== YOLOV8 DETECTION SETUP ====
def initialize_yolov8():
    """Initialize YOLOv8m detection model"""
    print("\n🚀 Initializing YOLOv8m Detection Model...")
    
    # Check if model file exists
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ Model file not found: {MODEL_PATH}")
        print("\n📥 Downloading YOLOv8m model...")
        print("   This will download ~50MB on first run...\n")
        
        try:
            # Download YOLOv8m from Ultralytics
            model = YOLO('yolov8m.pt')
            print("✅ YOLOv8m downloaded successfully!")
        except Exception as e:
            print(f"❌ Failed to download model: {e}")
            print("\nPlease download manually:")
            print("  1. Visit: https://github.com/ultralytics/ultralytics")
            print("  2. Or run: pip install ultralytics")
            print("  3. Model will auto-download on first use")
            return None
    else:
        print(f"📦 Loading model from: {MODEL_PATH}")
        print(f"📊 Model file size: {os.path.getsize(MODEL_PATH) / (1024*1024):.2f} MB")
        
        try:
            # Load YOLOv8 model
            model = YOLO(MODEL_PATH)
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            print("\nTroubleshooting:")
            print("  1. Ensure model file is not corrupted")
            print("  2. Try re-downloading: yolov8m.pt")
            print("  3. Check Ultralytics installation: pip install -U ultralytics")
            return None
    
    # Get device info
    device = 'cuda:0' if model.device.type == 'cuda' else 'cpu'
    
    if device != 'cpu':
        print("✅ Using GPU acceleration (CUDA)")
    else:
        print("✅ Using CPU")
    
    print("\n📋 Model Information:")
    print(f"   - Model: YOLOv8m (Medium)")
    print(f"   - Input size: {IMG_SIZE}x{IMG_SIZE}")
    print(f"   - Device: {device}")
    print(f"   - Classes: 80 (COCO dataset)")
    print(f"   - Person detection optimized")
    print(f"   - Long-range detection (10-20+ meters)")
    print(f"   - High accuracy and speed\n")
    
    return model

def detect_persons_yolov8(frame, model):
    """Detect persons using YOLOv8"""
    
    # Run inference
    results = model(frame, imgsz=IMG_SIZE, conf=CONFIDENCE_THRESHOLD, iou=IOU_THRESHOLD, verbose=False)
    
    detections = []
    
    # Parse results
    for result in results:
        boxes = result.boxes
        
        for box in boxes:
            # Get class
            cls = int(box.cls[0])
            
            # Filter for person class only (class 0 in COCO)
            if DETECT_PERSON_ONLY and cls != 0:
                continue
            
            # Get confidence
            conf = float(box.conf[0])
            
            # Get bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Calculate width and height
            w = x2 - x1
            h = y2 - y1
            
            # Filter out very small detections
            if w > MIN_DETECTION_SIZE and h > MIN_DETECTION_SIZE:
                detections.append({
                    'bbox': (x1, y1, w, h),
                    'confidence': conf,
                    'type': 'person',
                    'class_id': cls,
                    'center': ((x1 + x2) // 2, (y1 + y2) // 2)
                })
    
    return detections

# ==== NAVIGATION LOGIC ====
def calculate_movement(detections, frame_width, frame_height):
    """
    Calculate which direction to move based on detected persons
    Returns: (action, target_info)
    """
    if not detections:
        return 'SEARCH', None
    
    # Find the largest/closest person (by bounding box area)
    largest_person = max(detections, key=lambda d: d['bbox'][2] * d['bbox'][3])
    x, y, w, h = largest_person['bbox']
    
    # Get center from detection
    person_center_x, person_center_y = largest_person['center']
    
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

def execute_movement(action, current_speed):
    """Execute the movement command with appropriate speed"""
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

def estimate_distance(person_height_pixels):
    """
    Estimate approximate distance to person in meters
    Assumes average person height = 1.7m
    """
    if person_height_pixels == 0:
        return None
    
    # Camera focal length (approximate, calibrate for your camera)
    FOCAL_LENGTH = 600
    PERSON_HEIGHT_M = 1.7
    
    distance_m = (PERSON_HEIGHT_M * FOCAL_LENGTH) / person_height_pixels
    return distance_m

# ==== MAIN TRACKING LOOP ====
def human_tracking_mode():
    """Main mode - track and follow humans using YOLOv8"""
    global DETECT_PERSON_ONLY
    
    print("\n" + "="*60)
    print("🤖 ESP32 CAR - YOLOV8M HUMAN TRACKING")
    print("="*60)
    print("\nInitializing camera and detection system...")
    
    # Initialize camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Error: Could not open camera")
        return
    
    # Set camera properties for better quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("✅ Camera initialized")
    
    # Initialize YOLOv8 detector
    model = initialize_yolov8()
    if model is None:
        print("❌ Failed to initialize YOLOv8m model. Exiting...")
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
    print("  A - Toggle all objects detection")
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
    detect_person_only = DETECT_PERSON_ONLY
    
    print("🎬 Starting human tracking... Point camera at people!\n")
    
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
                # Detect persons
                detections = detect_persons_yolov8(frame, model)
                
                # Calculate movement
                action, target = calculate_movement(detections, frame_width, frame_height)
                
                # Execute movement (only if action changed to reduce command spam)
                if action != last_action:
                    execute_movement(action, current_speed)
                    last_action = action
            else:
                detections = []
                target = None
            
            # Draw detections and info on frame
            for detection in detections:
                x, y, w, h = detection['bbox']
                conf = detection['confidence']
                
                # Draw bounding box
                is_target = (detection == target)
                color = (0, 255, 0) if is_target else (255, 100, 100)
                thickness = 3 if is_target else 2
                
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
                
                # Calculate distance
                distance = estimate_distance(h)
                distance_text = f" ~{distance:.1f}m" if distance and distance < 20 else ""
                
                # Draw label with confidence
                label = f"Person {conf*100:.1f}%{distance_text}"
                if is_target:
                    label = f"TARGET: {label}"
                
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                
                # Background for text
                cv2.rectangle(frame, (x, y - label_size[1] - 10), 
                            (x + label_size[0] + 10, y), color, -1)
                cv2.putText(frame, label, (x + 5, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                
                # Draw center point
                center_x, center_y = detection['center']
                cv2.circle(frame, (center_x, center_y), 5, (0, 255, 255), -1)
                
                # Draw line from person to frame center (for target only)
                if is_target:
                    cv2.line(frame, (center_x, center_y), 
                            (frame_width // 2, frame_height // 2), (0, 255, 0), 2)
                    
                    # Draw distance arc
                    if distance and distance < 20:
                        arc_radius = int(h / 2)
                        cv2.ellipse(frame, (center_x, y + h), (arc_radius, 20), 
                                   0, 0, 180, (0, 255, 255), 2)
            
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
                cv2.rectangle(overlay, (0, 0), (320, 200), (0, 0, 0), -1)
                frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
                
                # Get device info
                device_name = str(model.device)
                
                info_text = [
                    f"FPS: {fps}",
                    f"Model: YOLOv8m",
                    f"Device: {device_name.upper()}",
                    f"Action: {last_action if not paused else 'PAUSED'}",
                    f"Speed: {current_speed}%",
                    f"Persons: {len(detections)}",
                    f"Conf: {CONFIDENCE_THRESHOLD}",
                    f"Mode: {'Person Only' if detect_person_only else 'All Objects'}"
                ]
                
                y_offset = 25
                for text in info_text:
                    cv2.putText(frame, text, (10, y_offset),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    y_offset += 23
            
            # Show status indicator (top right)
            status_color = (0, 255, 0) if detections else (0, 0, 255)
            cv2.circle(frame, (frame_width - 30, 30), 15, status_color, -1)
            cv2.putText(frame, "ACTIVE" if detections else "SEARCH", 
                       (frame_width - 90, 35), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.4, (255, 255, 255), 1)
            
            # Show pause indicator
            if paused:
                cv2.putText(frame, "PAUSED", (frame_width // 2 - 60, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            
            # Show frame
            cv2.imshow('ESP32 Human Tracking - YOLOv8m', frame)
            
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
            elif key == ord('a'):
                detect_person_only = not detect_person_only
                DETECT_PERSON_ONLY = detect_person_only
                print(f"🎯 Detection mode: {'Person Only' if detect_person_only else 'All Objects'}")
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
    print("ESP32 ROBOT CAR - YOLOV8M TRACKING SYSTEM")
    print("Powered by Ultralytics YOLOv8")
    print("="*60)
    
    # Check Python version
    print(f"\nPython Version: {sys.version}")
    
    # Check Ultralytics
    try:
        from ultralytics import __version__
        print(f"Ultralytics Version: {__version__}")
    except:
        print("❌ Ultralytics not found. Please install: pip install ultralytics")
        return
    
    # Test connection
    if not test_connection():
        sys.exit(1)
    
    print("\n🎥 Starting YOLOv8m human tracking mode...")
    print("✨ Features:")
    print("   - Long-range person detection (10-20+ meters)")
    print("   - State-of-the-art accuracy")
    print("   - Real-time tracking (20-30 FPS)")
    print("   - Distance estimation")
    print("   - Multi-person detection")
    print("   - 80 COCO classes support\n")
    
    time.sleep(1)
    human_tracking_mode()

if __name__ == "__main__":
    main()
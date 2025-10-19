"""
Venom AI Assistant - Standalone Video Viewer
Run this separately to view camera feed while API runs
"""

import cv2
import time
from datetime import datetime
from vision_module import get_vision_system
from utils import log_success, log_error, log_info

def main():
    """Main video viewer loop"""
    
    print("\n" + "=" * 60)
    print("📹 VENOM AI - VIDEO VIEWER")
    print("=" * 60)
    
    # Initialize vision system
    vision = get_vision_system()
    
    log_info("Initializing camera...")
    if not vision.initialize_camera():
        log_error("Failed to initialize camera!")
        print("\n❌ Camera not available. Please check:")
        print("  1. Camera is connected")
        print("  2. No other app is using the camera")
        print("  3. Camera permissions are granted")
        return
    
    log_success("Camera initialized!")
    
    print("\n" + "=" * 60)
    print("✅ VIDEO VIEWER READY")
    print("=" * 60)
    print("📹 Displaying camera feed...")
    print("Press 'q' to quit")
    print("=" * 60 + "\n")
    
    # Create window
    cv2.namedWindow('Venom AI - Camera Feed', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Venom AI - Camera Feed', 800, 600)
    
    frame_count = 0
    fps_start = time.time()
    fps = 0
    
    try:
        while True:
            frame = vision.capture_frame()
            
            if frame is not None:
                frame_count += 1
                
                # Calculate FPS every 30 frames
                if frame_count % 30 == 0:
                    elapsed = time.time() - fps_start
                    if elapsed > 0:
                        fps = 30 / elapsed
                    fps_start = time.time()
                
                # Add status overlay with background for better visibility
                overlay = frame.copy()
                
                # Dark background for text
                cv2.rectangle(overlay, (5, 5), (400, 150), (0, 0, 0), -1)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
                
                # Status text
                cv2.putText(frame, f"Venom AI - Camera Active", (15, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.putText(frame, f"Frame: {frame_count} | FPS: {fps:.1f}", (15, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, f"Time: {timestamp}", (15, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                resolution = f"{frame.shape[1]}x{frame.shape[0]}"
                cv2.putText(frame, f"Resolution: {resolution}", (15, 120),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Show frame
                cv2.imshow('Venom AI - Camera Feed', frame)
                
                # Check for quit
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    log_info("Quit key pressed")
                    break
                elif key == ord('s'):
                    # Save screenshot
                    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    cv2.imwrite(filename, frame)
                    log_success(f"Screenshot saved: {filename}")
            else:
                log_error("Failed to capture frame")
                time.sleep(0.1)
    
    except KeyboardInterrupt:
        log_info("Keyboard interrupt received")
    except Exception as e:
        log_error(f"Video error: {e}")
    finally:
        cv2.destroyAllWindows()
        vision.release_camera()
        log_success("Video viewer stopped")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
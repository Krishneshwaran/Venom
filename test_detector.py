#!/usr/bin/env python3
"""
Test the detector to see if it's generating per-person data
"""

import cv2
import numpy as np
from detector import YOLODetector, SimpleActivityClassifier, ActivityDetector
from config import Config

def test_detector():
    print("🔍 TESTING DETECTOR FOR PER-PERSON DATA")
    print("=" * 50)
    
    # Initialize components
    config = Config()
    detector = ActivityDetector(config)
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera")
        return
    
    print("📹 Camera opened. Testing detection for 10 seconds...")
    
    frame_count = 0
    person_detections = 0
    
    try:
        while frame_count < 50:  # Test ~10 seconds at 5fps
            ret, frame = cap.read()
            if not ret:
                break
                
            # Run detection
            result = detector.detect_activity(frame)
            
            frame_count += 1
            
            # Check what we detected
            persons_found = len([obj for obj in result.objects if obj['label'].lower() == 'person'])
            per_person_count = len(result.per_person_activities) if result.per_person_activities else 0
            
            print(f"Frame {frame_count}: {result.activity} | {persons_found} persons | {per_person_count} per-person activities")
            
            if result.per_person_activities:
                person_detections += 1
                for i, person in enumerate(result.per_person_activities):
                    print(f"  Person {i+1}: {person['activity']} ({person['confidence']:.2f}) | bbox: {person['bbox']}")
            
            # Display frame with detections
            annotated = detector.draw_detection(frame, result)
            cv2.imshow('Detection Test', annotated)
            
            if cv2.waitKey(200) & 0xFF == ord('q'):  # 5fps
                break
                
    except KeyboardInterrupt:
        print("\\n🛑 Test interrupted")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
    print(f"\\n📊 Test Results:")
    print(f"   • Frames processed: {frame_count}")
    print(f"   • Frames with per-person data: {person_detections}")
    print(f"   • Success rate: {person_detections/frame_count*100:.1f}%")
    
    if person_detections == 0:
        print("❌ NO PER-PERSON DATA GENERATED!")
        print("🔧 This explains why snapshots aren't working.")
    else:
        print("✅ Per-person data is being generated correctly.")

if __name__ == "__main__":
    test_detector()
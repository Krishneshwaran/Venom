"""
Fresh, Clean Activity Detection Module - Real-time YOLO detection
Detects objects and activities in real-time with no caching issues
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, asdict
import time
from collections import deque, Counter
from config import Config, ActivityType, DetectionModel, DetectionConfig


@dataclass
class Detection:
    """Represents a detected object in a frame"""
    label: str
    score: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)


@dataclass
class DetectionResult:
    """Complete detection result for a frame"""
    activity: str
    confidence: float
    objects: List[Dict]
    person_detected: bool = True
    per_person_activities: Optional[List[Dict]] = None
    head_pose: Optional[Dict] = None
    timestamp: float = 0.0


class YOLODetector:
    """Simple YOLO detector - runs fresh every frame, NO CACHING"""
    
    def __init__(self, config: DetectionConfig, model_name: str = "yolov8n"):
        self.config = config
        self.model = None
        self.model_name = model_name
        self.initialized = False
        
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
            self.initialized = True
            print(f"✓ YOLO detector initialized (model={self.model_name})")
        except Exception as e:
            print(f"✗ Failed to load YOLO: {e}")
            self.initialized = False
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLO detection - FRESH every time"""
        if not self.initialized:
            return []
        
        try:
            # Run prediction with VERY LOW confidence to detect more objects
            results = self.model.predict(
                frame,
                imgsz=640,
                conf=0.15,  # Even lower threshold - detect MORE objects
                iou=0.4,    # Lower IoU for better overlapping object detection
                verbose=False
            )
            
            if not results:
                return []
            
            detections = []
            res = results[0]
            boxes = res.boxes
            
            if boxes is None or len(boxes) == 0:
                return []
            
            # Parse detections
            for box in boxes:
                try:
                    # Get box coordinates
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    w, h = x2 - x1, y2 - y1
                    
                    # Get confidence and class
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    label = self.model.names[cls_id]
                    
                    detections.append(Detection(label, conf, (x1, y1, w, h)))
                except Exception as e:
                    continue
            
            # Print ALL detected labels for debugging (show everything YOLO sees)
            if detections:
                labels_with_conf = [(d.label, f"{d.score:.2f}") for d in detections]
                print(f"Detected {len(detections)} objects: {labels_with_conf}")
            else:
                print("Detected: []")
            
            return detections
            
        except Exception as e:
            print(f"YOLO detection error: {e}")
            return []


class SimpleActivityClassifier:
    """Simple rule-based activity classifier"""
    
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.history = deque(maxlen=5)  # Keep last 5 classifications
    
    def classify(self, objects: List[Detection], person_present: bool) -> Tuple[str, float]:
        """Classify activity based on detected objects"""
        if not person_present:
            return 'absent', 1.0
        
        if not objects:
            return 'idle', 0.5
        
        # Get object labels and count them
        labels = [obj.label.lower() for obj in objects]
        label_counts = {}
        for label in labels:
            label_counts[label] = label_counts.get(label, 0) + 1
        
        # Priority-based classification with MORE activities
        # WORKING activities
        if 'laptop' in labels and 'keyboard' in labels:
            return 'working_computer', 0.95
        elif 'laptop' in labels or 'keyboard' in labels or 'mouse' in labels:
            return 'working', 0.92
        
        # PHONE activities
        elif 'cell phone' in labels or 'phone' in labels:
            if 'person' in labels:
                return 'using_phone', 0.93
            else:
                return 'watching_reels', 0.90
        
        # WATCHING activities
        elif 'tv' in labels or 'monitor' in labels or 'tvmonitor' in labels:
            return 'watching_tv', 0.90
        
        # READING/WRITING activities
        elif 'book' in labels:
            return 'reading', 0.87
        
        # EATING/DRINKING activities
        elif 'cup' in labels or 'bottle' in labels or 'wine glass' in labels:
            return 'drinking', 0.85
        elif 'bowl' in labels or 'fork' in labels or 'spoon' in labels or 'knife' in labels:
            return 'eating', 0.85
        elif 'pizza' in labels or 'hot dog' in labels or 'sandwich' in labels or 'cake' in labels:
            return 'eating', 0.88
        
        # RELAXING/LEISURE activities
        elif 'couch' in labels or 'bed' in labels:
            return 'relaxing', 0.75
        elif 'chair' in labels:
            return 'sitting', 0.70
        
        # SPORTS/EXERCISE activities
        elif 'sports ball' in labels or 'baseball bat' in labels or 'tennis racket' in labels:
            return 'playing_sports', 0.85
        elif 'frisbee' in labels or 'skis' in labels or 'snowboard' in labels or 'surfboard' in labels:
            return 'playing_sports', 0.85
        
        # TRAVEL/TRANSPORTATION
        elif 'backpack' in labels or 'handbag' in labels or 'suitcase' in labels:
            return 'traveling', 0.75
        elif 'car' in labels or 'bus' in labels or 'train' in labels or 'bicycle' in labels:
            return 'commuting', 0.80
        
        # GROOMING/PERSONAL CARE
        elif 'toothbrush' in labels or 'hair drier' in labels:
            return 'grooming', 0.82
        
        # PETS/ANIMALS
        elif 'dog' in labels or 'cat' in labels or 'bird' in labels or 'horse' in labels:
            return 'with_pet', 0.80
        
        # PERSON only (idle)
        elif 'person' in labels:
            return 'idle', 0.70
        
        # Objects present but unclear activity
        else:
            # Return generic activity based on most common object
            if labels:
                most_common = max(set(labels), key=labels.count)
                return f'near_{most_common}', 0.65
            return 'idle', 0.60
    
    def smooth(self, activity: str, confidence: float) -> Tuple[str, float]:
        """Apply minimal smoothing"""
        self.history.append((activity, confidence))
        
        if len(self.history) < 3:
            return activity, confidence
        
        # Most common in last 3 frames
        recent = list(self.history)[-3:]
        activities = [a for a, c in recent]
        most_common = max(set(activities), key=activities.count)
        
        # Average confidence
        confs = [c for a, c in recent if a == most_common]
        avg_conf = sum(confs) / len(confs) if confs else confidence
        
        return most_common, avg_conf


class ActivityDetector:
    """Main detector - coordinates YOLO and classification"""
    
    def __init__(self, config: Config):
        self.config = config
        self.detection_config = config.detection
        
        # Initialize YOLO
        model_name = getattr(config, 'yolo_model', 'yolov8n')
        self.detector = YOLODetector(self.detection_config, model_name=model_name)
        
        if not self.detector.initialized:
            print("⚠️ YOLO not available - using mock mode")
        
        self.classifier = SimpleActivityClassifier(self.detection_config)
        
        print(f"✓ Activity detector ready")
    
    def _get_nearby_objects(self, person_bbox: Tuple[int, int, int, int], 
                           all_objects: List[Detection]) -> List[Detection]:
        """Get objects near a specific person"""
        px, py, pw, ph = person_bbox
        # Expand person bbox by 50% to catch nearby objects
        margin = int(max(pw, ph) * 0.5)
        expanded = (px - margin, py - margin, pw + margin * 2, ph + margin * 2)
        
        nearby = []
        for obj in all_objects:
            if obj.label.lower() == 'person':
                continue  # Skip other persons
            
            ox, oy, ow, oh = obj.bbox
            obj_center = (ox + ow // 2, oy + oh // 2)
            
            # Check if object center is near person
            ex, ey, ew, eh = expanded
            if ex <= obj_center[0] <= ex + ew and ey <= obj_center[1] <= ey + eh:
                nearby.append(obj)
        
        return nearby
    
    def detect_activity(self, frame: np.ndarray) -> DetectionResult:
        """Detect activity in frame with per-person activities"""
        
        # Run YOLO detection
        objects = self.detector.detect(frame)
        
        # Find all persons
        persons = [obj for obj in objects if obj.label.lower() == 'person']
        person_present = len(persons) > 0
        
        # Classify overall activity
        activity, confidence = self.classifier.classify(objects, person_present)
        activity, confidence = self.classifier.smooth(activity, confidence)
        
        # Per-person activities
        per_person_activities = []
        for i, person in enumerate(persons):
            # Get objects near this person
            nearby_objects = self._get_nearby_objects(person.bbox, objects)
            
            # Classify this person's activity
            person_activity, person_conf = self.classifier.classify(
                nearby_objects, 
                person_present=True
            )
            
            per_person_activities.append({
                'person_id': i + 1,
                'bbox': person.bbox,
                'activity': person_activity,
                'confidence': person_conf,
                'nearby_objects': [obj.label for obj in nearby_objects]
            })
        
        # Build result
        result = DetectionResult(
            activity=activity,
            confidence=confidence,
            objects=[asdict(obj) for obj in objects],
            person_detected=person_present,
            per_person_activities=per_person_activities,
            head_pose=None,
            timestamp=time.time()
        )
        
        return result
    
    def draw_detection(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        """Draw detection results on frame with per-person activity labels"""
        output = frame.copy()
        h, w = output.shape[:2]
        
        # Draw all object bounding boxes first
        for obj_dict in result.objects:
            x, y, bw, bh = obj_dict['bbox']
            label = obj_dict['label']
            score = obj_dict['score']
            
            # Color based on object type
            if label.lower() == 'person':
                color = (0, 255, 0)  # Green for person
                thickness = 3
            else:
                color = (255, 100, 0)  # Blue for objects
                thickness = 2
            
            # Draw bbox
            cv2.rectangle(output, (x, y), (x + bw, y + bh), color, thickness)
            
            # Draw small object label at bottom of bbox
            if label.lower() != 'person':  # Don't draw person label here
                obj_label_text = f"{label}"
                (tw, th), _ = cv2.getTextSize(obj_label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(output, (x, y + bh), (x + tw + 6, y + bh + th + 6), (0, 0, 0), -1)
                cv2.putText(output, obj_label_text, (x + 3, y + bh + th + 3), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw per-person activity labels
        if result.per_person_activities:
            for person_info in result.per_person_activities:
                px, py, pw, ph = person_info['bbox']
                activity = person_info['activity']
                confidence = person_info['confidence']
                person_id = person_info['person_id']
                
                # Format activity text (readable)
                activity_text = activity.replace('_', ' ').title()
                
                # Create label with person ID
                label_text = f"Person {person_id}: {activity_text}"
                conf_text = f"{confidence:.0%}"
                
                # Position label above person's head
                label_y = max(35, py - 10)
                
                # Calculate text sizes
                (text_w, text_h), _ = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                (conf_w, conf_h), _ = cv2.getTextSize(
                    conf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                
                # Background box dimensions
                box_w = max(text_w, conf_w) + 20
                box_h = text_h + conf_h + 15
                box_x = px + (pw - box_w) // 2  # Center above person
                box_y = label_y - box_h
                
                # Ensure box stays in frame
                box_x = max(5, min(box_x, w - box_w - 5))
                box_y = max(5, box_y)
                
                # Draw semi-transparent background
                overlay = output.copy()
                cv2.rectangle(overlay, (box_x, box_y), 
                            (box_x + box_w, box_y + box_h),
                            (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.75, output, 0.25, 0, output)
                
                # Draw bright green border
                cv2.rectangle(output, (box_x, box_y), 
                            (box_x + box_w, box_y + box_h),
                            (0, 255, 0), 2)
                
                # Draw activity text (bright green)
                text_x = box_x + 10
                text_y = box_y + text_h + 5
                cv2.putText(output, label_text, (text_x, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Draw confidence below (lighter green)
                conf_y = text_y + conf_h + 3
                cv2.putText(output, conf_text, (text_x, conf_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        
        # Draw compact overall status in top-left corner
        status_text = f"Overall: {result.activity.replace('_', ' ').title()}"
        cv2.rectangle(output, (0, 0), (w, 30), (0, 0, 0), -1)
        cv2.putText(output, status_text, (10, 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return output

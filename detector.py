"""
Activity Detection Module
Handles object detection, pose estimation, and activity classification
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, asdict
import time
from collections import deque, Counter
from config import (
    Config, ActivityType, DetectionModel, ACTIVITY_RULES, 
    OBJECT_LABELS, DetectionConfig
)


@dataclass
class Detection:
    """Represents a detected object in a frame"""
    label: str
    score: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)


@dataclass
class HeadPose:
    """Represents head orientation"""
    yaw: float
    pitch: float
    roll: float


@dataclass
class DetectionResult:
    """Complete detection result for a frame"""
    activity: str
    confidence: float
    objects: List[Dict]
    head_pose: Optional[Dict] = None
    person_detected: bool = True
    timestamp: float = 0.0


class BaseDetector:
    """Base class for all detectors"""
    
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.initialized = False
    
    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """Detect objects in frame"""
        raise NotImplementedError
    
    def detect_pose(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect pose/head orientation"""
        raise NotImplementedError
    
    def detect_person(self, frame: np.ndarray) -> bool:
        """Detect if person is present"""
        raise NotImplementedError


class MockDetector(BaseDetector):
    """Mock detector for testing without ML models"""
    
    def __init__(self, config: DetectionConfig):
        super().__init__(config)
        self.frame_count = 0
        self.cycle_activities = [
            ActivityType.WATCHING_REELS,
            ActivityType.WORKING,
            ActivityType.WATCHING_TV,
            ActivityType.IDLE,
            ActivityType.READING
        ]
        self.current_activity_index = 0
        self.frames_in_activity = 0
        self.frames_per_activity = 300  # ~10 seconds at 30fps
        self.initialized = True
    
    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """Simulate object detection"""
        self.frame_count += 1
        
        # Cycle through activities
        if self.frames_in_activity >= self.frames_per_activity:
            self.current_activity_index = (self.current_activity_index + 1) % len(self.cycle_activities)
            self.frames_in_activity = 0
        self.frames_in_activity += 1
        
        current_activity = self.cycle_activities[self.current_activity_index]
        
        # Generate appropriate objects for activity
        detections = []
        if current_activity == ActivityType.WATCHING_REELS:
            detections.append(Detection("phone", 0.92, (100, 150, 80, 160)))
        elif current_activity == ActivityType.WORKING:
            detections.append(Detection("laptop", 0.88, (150, 100, 300, 200)))
            detections.append(Detection("keyboard", 0.85, (150, 280, 300, 50)))
        elif current_activity == ActivityType.WATCHING_TV:
            detections.append(Detection("tv", 0.90, (200, 50, 400, 300)))
        elif current_activity == ActivityType.READING:
            detections.append(Detection("book", 0.87, (120, 180, 150, 200)))
        
        return detections
    
    def detect_pose(self, frame: np.ndarray) -> Optional[Dict]:
        """Simulate head pose detection"""
        current_activity = self.cycle_activities[self.current_activity_index]
        
        # Generate realistic head poses for each activity
        pose_map = {
            ActivityType.WATCHING_REELS: {"yaw": 2.1, "pitch": -20.5, "roll": 0.3},
            ActivityType.WORKING: {"yaw": 0.5, "pitch": -10.2, "roll": -1.0},
            ActivityType.WATCHING_TV: {"yaw": 0.0, "pitch": 5.0, "roll": 0.0},
            ActivityType.READING: {"yaw": 3.0, "pitch": -25.0, "roll": 2.0},
            ActivityType.IDLE: {"yaw": 10.0, "pitch": 0.0, "roll": 0.0}
        }
        
        return pose_map.get(current_activity, {"yaw": 0, "pitch": 0, "roll": 0})
    
    def detect_person(self, frame: np.ndarray) -> bool:
        """Simulate person detection"""
        # Person present 90% of the time in mock mode
        return self.current_activity_index < len(self.cycle_activities) - 1 or np.random.random() > 0.1


class MediaPipeDetector(BaseDetector):
    """Real detector using MediaPipe for pose and face detection"""
    
    def __init__(self, config: DetectionConfig):
        super().__init__(config)
        try:
            import mediapipe as mp
            self.mp = mp
            
            # Initialize MediaPipe solutions
            self.mp_pose = mp.solutions.pose.Pose(
                min_detection_confidence=config.min_confidence,
                min_tracking_confidence=config.min_confidence
            )
            self.mp_face = mp.solutions.face_detection.FaceDetection(
                min_detection_confidence=config.min_confidence
            )
            self.mp_hands = mp.solutions.hands.Hands(
                min_detection_confidence=config.min_confidence,
                min_tracking_confidence=config.min_confidence
            )
            
            self.initialized = True
            print("MediaPipe detector initialized")
        except ImportError as e:
            print(f"MediaPipe not available: {e}")
            self.initialized = False
    
    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """
        MediaPipe doesn't do object detection, so this would need 
        to be combined with YOLO or another object detector
        """
        # Placeholder - would integrate YOLO here
        return []
    
    def detect_pose(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect head pose using MediaPipe Face Mesh"""
        if not self.initialized:
            return None
        
        # Convert to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None
        
        # Extract head landmarks to calculate orientation
        # This is a simplified version - real implementation would use face mesh
        landmarks = results.pose_landmarks.landmark
        
        # Estimate head pose from shoulder and nose positions
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        
        # Simple yaw calculation from shoulder positions
        yaw = np.arctan2(left_shoulder.x - right_shoulder.x, 
                        left_shoulder.z - right_shoulder.z) * 180 / np.pi
        
        # Simple pitch from nose to shoulder midpoint
        shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2
        pitch = (nose.y - shoulder_mid_y) * 90  # Rough approximation
        
        return {
            "yaw": float(yaw),
            "pitch": float(pitch),
            "roll": 0.0  # Would need more complex calculation
        }
    
    def detect_person(self, frame: np.ndarray) -> bool:
        """Detect if person is present using face detection"""
        if not self.initialized:
            return False
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.mp_face.process(frame_rgb)
        
        return results.detections is not None and len(results.detections) > 0


class ActivityClassifier:
    """Classifies activity based on detected objects and pose"""
    
    def __init__(self, config: DetectionConfig):
        self.config = config
        self.activity_history = deque(maxlen=config.temporal_smoothing_frames)
    
    def classify(self, objects: List[Detection], head_pose: Optional[Dict], 
                 person_present: bool) -> Tuple[str, float]:
        """
        Classify activity based on objects and pose
        Returns: (activity_type, confidence)
        """
        if not person_present:
            return ActivityType.ABSENT.value, 1.0
        
        # Score each activity based on rules
        activity_scores = {}
        
        for activity_type, rules in ACTIVITY_RULES.items():
            score = self._score_activity(activity_type, rules, objects, head_pose, person_present)
            activity_scores[activity_type] = score
        
        # Get highest scoring activity
        best_activity = max(activity_scores.items(), key=lambda x: (x[1], rules.get("priority", 0)))
        activity_type, confidence = best_activity
        
        return activity_type.value, min(confidence, 1.0)
    
    def _score_activity(self, activity_type: ActivityType, rules: Dict, 
                       objects: List[Detection], head_pose: Optional[Dict],
                       person_present: bool) -> float:
        """Calculate score for a specific activity"""
        score = 0.0
        
        # Check person presence requirement
        if rules.get("person_present", True) != person_present:
            return 0.0
        
        # Check required objects
        required_objects = rules.get("required_objects", [])
        if required_objects:
            detected_labels = [obj.label.lower() for obj in objects]
            matched_objects = sum(1 for req in required_objects 
                                 if any(label in detected_labels 
                                       for label in OBJECT_LABELS.get(req, [req])))
            
            if matched_objects == 0:
                return 0.0
            
            score += (matched_objects / len(required_objects)) * 0.6
            
            # Add object confidence
            relevant_objects = [obj for obj in objects 
                              if any(label in obj.label.lower() 
                                    for req in required_objects 
                                    for label in OBJECT_LABELS.get(req, [req]))]
            if relevant_objects:
                avg_confidence = sum(obj.score for obj in relevant_objects) / len(relevant_objects)
                score += avg_confidence * 0.4
        else:
            # No objects required (like idle)
            score = 0.3
        
        # Check head pose criteria
        if head_pose and "head_pose_criteria" in rules:
            pose_score = self._score_head_pose(head_pose, rules["head_pose_criteria"])
            score = score * pose_score if score > 0 else pose_score * 0.3
        
        return score
    
    def _score_head_pose(self, head_pose: Dict, criteria: Dict) -> float:
        """Score how well head pose matches criteria"""
        score = 1.0
        
        for axis, range_val in criteria.items():
            if axis not in head_pose:
                continue
            
            value = head_pose[axis]
            min_val, max_val = range_val
            
            if min_val <= value <= max_val:
                # Perfect match
                continue
            else:
                # Calculate how far outside range
                if value < min_val:
                    deviation = min_val - value
                else:
                    deviation = value - max_val
                
                # Penalize based on deviation (max 30 degrees tolerance)
                penalty = max(0, 1 - (deviation / 30))
                score *= penalty
        
        return max(score, 0.0)
    
    def smooth_activity(self, activity: str, confidence: float) -> Tuple[str, float]:
        """Apply temporal smoothing to reduce jitter"""
        self.activity_history.append((activity, confidence))
        
        if len(self.activity_history) < 3:
            return activity, confidence
        
        # Get most common activity in recent history
        recent_activities = [a[0] for a in list(self.activity_history)[-5:]]
        activity_counts = Counter(recent_activities)
        most_common_activity = activity_counts.most_common(1)[0][0]
        
        # Calculate average confidence for that activity
        confidences = [conf for act, conf in self.activity_history if act == most_common_activity]
        avg_confidence = sum(confidences) / len(confidences) if confidences else confidence
        
        return most_common_activity, avg_confidence


class ActivityDetector:
    """Main detector that orchestrates detection and classification"""
    
    def __init__(self, config: Config):
        self.config = config
        self.detection_config = config.detection
        
        # Initialize appropriate detector
        if self.detection_config.model == DetectionModel.MEDIAPIPE:
            self.detector = MediaPipeDetector(self.detection_config)
            if not self.detector.initialized:
                print("Falling back to mock detector")
                self.detector = MockDetector(self.detection_config)
        else:
            self.detector = MockDetector(self.detection_config)
        
        self.classifier = ActivityClassifier(self.detection_config)
        
        print(f"Activity detector initialized with {self.detection_config.model.value} model")
    
    def detect_activity(self, frame: np.ndarray) -> DetectionResult:
        """
        Run complete detection pipeline on a frame
        Returns: DetectionResult with activity, confidence, objects, and pose
        """
        # Detect person
        person_present = self.detector.detect_person(frame)
        
        # Detect objects
        objects = self.detector.detect_objects(frame)
        
        # Detect head pose
        head_pose = self.detector.detect_pose(frame)
        
        # Classify activity
        activity, confidence = self.classifier.classify(objects, head_pose, person_present)
        
        # Apply temporal smoothing
        activity, confidence = self.classifier.smooth_activity(activity, confidence)
        
        # Build result
        result = DetectionResult(
            activity=activity,
            confidence=confidence,
            objects=[asdict(obj) for obj in objects],
            head_pose=head_pose,
            person_detected=person_present,
            timestamp=time.time()
        )
        
        return result
    
    def draw_detection(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        """Draw detection results on frame for visualization"""
        frame = frame.copy()
        
        # Draw activity label
        activity_text = f"Activity: {result.activity}"
        confidence_text = f"Confidence: {result.confidence:.2f}"
        
        cv2.putText(frame, activity_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, confidence_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Draw bounding boxes for objects
        for obj in result.objects:
            bbox = obj['bbox']
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, f"{obj['label']} {obj['score']:.2f}", 
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Draw head pose if available
        if result.head_pose:
            pose_text = f"Yaw: {result.head_pose['yaw']:.1f} Pitch: {result.head_pose['pitch']:.1f}"
            cv2.putText(frame, pose_text, (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Person detection indicator
        status_text = "Person: Present" if result.person_detected else "Person: Absent"
        color = (0, 255, 0) if result.person_detected else (0, 0, 255)
        cv2.putText(frame, status_text, (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return frame

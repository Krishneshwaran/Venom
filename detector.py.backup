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
    per_person_activities: Optional[List[Dict]] = None
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
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Return list of face bounding boxes (x,y,w,h) in pixel coordinates.
        Default: no faces detected. Detectors can override for face-capable models.
        """
        return []


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

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Mock face detection: return a simulated face bbox when person present."""
        if self.detect_person(frame):
            # return a simple face bbox near the top-left for testing
            return [(120, 120, 80, 80)]
        return []


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

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Return a list of face bounding boxes (x,y,w,h) using MediaPipe face detection."""
        faces = []
        if not self.initialized:
            return faces

        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mp_face.process(frame_rgb)
            h, w = frame.shape[:2]
            if results.detections:
                for det in results.detections:
                    bbox_rel = det.location_data.relative_bounding_box
                    x = int(bbox_rel.xmin * w)
                    y = int(bbox_rel.ymin * h)
                    bw = int(bbox_rel.width * w)
                    bh = int(bbox_rel.height * h)
                    # sanitize
                    x = max(0, x)
                    y = max(0, y)
                    bw = max(0, bw)
                    bh = max(0, bh)
                    faces.append((x, y, bw, bh))
        except Exception:
            pass

        return faces


class YOLODetector(BaseDetector):
    """Object detector using Ultralytics YOLO (yolov8n by default).
    Falls back gracefully if the ultralytics package or weights are unavailable.
    """

    def __init__(self, config: DetectionConfig, model_name: str = "yolov8n"):
        super().__init__(config)
        self.model = None
        self.model_name = model_name
        # Track frame number instead of hash
        self._last_frame_number = -1
        self._frame_counter = 0
        self._current_detections = []

        try:
            # Lazy import to avoid hard dependency if user doesn't enable YOLO
            from ultralytics import YOLO

            try:
                # This will download weights on first run if not present
                self.model = YOLO(self.model_name)
                self.initialized = True
                print(f"YOLO detector initialized (model={self.model_name})")
            except Exception as e:
                print(f"Failed to load YOLO model '{self.model_name}': {e}")
                self.initialized = False

        except ImportError:
            print("ultralytics not installed — YOLO detector not available")
            self.initialized = False

    def _run_yolo(self, frame: np.ndarray, frame_number: int) -> List[Detection]:
        """Run YOLO prediction once per unique frame and cache results."""
        
        if frame_number != self._last_frame_number:
            # New frame - run fresh prediction
            self._last_frame_number = frame_number
            self._current_detections = []
            
            try:
                results = self.model.predict(frame, imgsz=640, conf=float(self.config.min_confidence), verbose=False)
                if not results:
                    return []

                res = results[0]
                boxes = getattr(res, 'boxes', None)
                names = getattr(res, 'names', {}) if hasattr(res, 'names') else getattr(self.model, 'names', {})

                if boxes is None:
                    return []

                try:
                    xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, 'cpu') else boxes.xyxy
                    conf_arr = boxes.conf.cpu().numpy() if hasattr(boxes.conf, 'cpu') else boxes.conf
                    cls_arr = boxes.cls.cpu().numpy() if hasattr(boxes.cls, 'cpu') else boxes.cls

                    for i in range(len(xyxy)):
                        x1, y1, x2, y2 = map(int, xyxy[i])
                        w = x2 - x1
                        h = y2 - y1
                        score = float(conf_arr[i])
                        cls_id = int(cls_arr[i])
                        label = names.get(cls_id, str(cls_id))
                        self._current_detections.append(Detection(label, score, (x1, y1, w, h)))
                except Exception:
                    try:
                        for box in boxes:
                            xy = box.xyxy.cpu().numpy().tolist()[0] if hasattr(box.xyxy, 'cpu') else box.xyxy.tolist()[0]
                            x1, y1, x2, y2 = map(int, xy)
                            w = x2 - x1
                            h = y2 - y1
                            score = float(box.conf.cpu().numpy().tolist()[0]) if hasattr(box.conf, 'cpu') else float(box.conf)
                            cls_id = int(box.cls.cpu().numpy().tolist()[0]) if hasattr(box.cls, 'cpu') else int(box.cls)
                            label = names.get(cls_id, str(cls_id))
                            self._current_detections.append(Detection(label, score, (x1, y1, w, h)))
                    except Exception as e:
                        print(f"YOLO detection parsing failed: {e}")
            except Exception as e:
                print(f"YOLO detection failed: {e}")
        
        return self._current_detections

    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLO on the frame and return a list of Detection dataclasses."""
        if not self.initialized or self.model is None:
            return []
        # Increment counter for each new frame
        self._frame_counter += 1
        return self._run_yolo(frame, self._frame_counter)

    def detect_pose(self, frame: np.ndarray) -> Optional[Dict]:
        # YOLO doesn't provide head pose; leave as None
        return None

    def detect_person(self, frame: np.ndarray) -> bool:
        """Return True if a person was detected in the frame."""
        if not self.initialized:
            return False

        # Reuse cached detections from _run_yolo (use same frame counter)
        detections = self._run_yolo(frame, self._frame_counter)
        for det in detections:
            if str(det.label).lower() == 'person':
                return True
        return False

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """YOLO-based detectors typically don't return face bounding boxes; return empty list.
        If you have a model that detects faces, override this method to return face bboxes.
        """
        return []


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
        best_activity = max(activity_scores.items(), key=lambda x: (x[1], ACTIVITY_RULES[x[0]].get("priority", 0)))
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


class ActivityRecognizer:
    """Recognize per-person activities by associating nearby objects to each person

    This is a lightweight heuristic recognizer: for each detected person bbox we
    collect objects whose centers fall within an expanded person bbox (or have
    IoU overlap) and run the ActivityClassifier on that subset. We keep a small
    spatially-keyed history for smoothing per-person.
    """

    def __init__(self, config: DetectionConfig, classifier: ActivityClassifier):
        self.config = config
        self.classifier = classifier
        self.histories = {}  # key -> deque of (activity, confidence)
        self.margin_ratio = getattr(config, 'person_object_margin', 0.5)
        self.smooth_frames = getattr(config, 'temporal_smoothing_frames', 5)
        # Simple tracking state for persistent person IDs
        self.next_person_id = 1
        # tracks: person_id -> { 'bbox': (x,y,w,h), 'last_seen': timestamp, 'history': deque, 'lost': int }
        self.tracks = {}
        # matching thresholds
        self.max_lost_frames = getattr(config, 'person_lost_frames', 60)
        self.max_center_distance = getattr(config, 'person_match_dist', 100)
        # Optional Norfair tracker (preferred for stable IDs)
        self.norfair_available = False
        self.norfair_tracker = None
        try:
            from norfair import Detection as NorfairDetection, Tracker as NorfairTracker

            # simple euclidean distance on points
            def _euclidean(detection, tracked_object):
                import numpy as _np
                # detection.points or detection.points[0]
                p = _np.asarray(detection.points).reshape(-1)
                est = _np.asarray(tracked_object.estimate).reshape(-1)
                return float(_np.linalg.norm(p - est))

            # create a tracker instance
            self._NorfairDetection = NorfairDetection
            self._NorfairTrackerClass = NorfairTracker
            try:
                # instantiate tracker with reasonable threshold
                self.norfair_tracker = NorfairTracker(distance_function=_euclidean, distance_threshold=self.max_center_distance)
                self.norfair_available = True
            except Exception:
                # if Tracker signature differs, just mark unavailable
                self.norfair_tracker = None
                self.norfair_available = False
        except Exception:
            self.norfair_available = False

    def _bbox_center(self, bbox):
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)

    def _iou(self, a, b) -> float:
        # a and b are (x,y,w,h)
        ax1, ay1, aw, ah = a
        ax2, ay2 = ax1 + aw, ay1 + ah
        bx1, by1, bw, bh = b
        bx2, by2 = bx1 + bw, by1 + bh

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = aw * ah
        area_b = bw * bh
        union = area_a + area_b - inter_area
        return inter_area / union if union > 0 else 0.0

    def _spatial_key(self, center):
        # quantize center to build a stable-ish key (50px grid)
        gx = int(center[0] // 50)
        gy = int(center[1] // 50)
        return f"{gx}:{gy}"

    def recognize(self, detections: List[Detection], head_pose: Optional[Dict]) -> List[Dict]:
        # Find person detections
        persons = [d for d in detections if str(d.label).lower() == 'person']
        others = [d for d in detections if str(d.label).lower() != 'person']
        # Attempt to detect faces in the frame if detector provides it
        face_bboxes = []
        try:
            # the underlying detector instance may offer detect_faces(frame) but
            # ActivityRecognizer doesn't have the frame here; callers may set
            # per-frame face info on the classifier or detector. We'll attempt
            # to access a cached attribute on classifier.config if present.
            det_instance = getattr(self, 'detector_instance', None)
            if det_instance and hasattr(det_instance, 'detect_faces'):
                # caller must set recognizer.detector_instance = actual detector
                # externally in ActivityDetector before calling recognize
                face_bboxes = det_instance.detect_faces(getattr(self, '_last_frame', None)) or []
        except Exception:
            face_bboxes = []

        per_person = []
        if self.norfair_available and self.norfair_tracker is not None:
            # Convert person bboxes to Norfair detections (use bbox center as point)
            norfair_detections = []
            for p in persons:
                cx, cy = self._bbox_center(p.bbox)
                # norfair expects points as ndarray-like
                pts = [cx, cy]
                nor_d = self._NorfairDetection(points=pts, scores=None)
                norfair_detections.append(nor_d)

            try:
                tracked = self.norfair_tracker.update(norfair_detections)
                # Map tracked objects back to detections by nearest center
                for t in tracked:
                    # t.estimate is the estimated point
                    est = t.estimate
                    # find closest detection
                    best = None
                    best_dist = float('inf')
                    for p in persons:
                        cx, cy = self._bbox_center(p.bbox)
                        dist = ((est[0] - cx) ** 2 + (est[1] - cy) ** 2) ** 0.5
                        if dist < best_dist:
                            best_dist = dist
                            best = p

                    if best is None:
                        continue

                    # Use tracked.id if available, otherwise assign new
                    pid = getattr(t, 'id', None)
                    if pid is None:
                        pid = self.next_person_id
                        self.next_person_id += 1

                    # update local tracks mapping for compatibility
                    self.tracks[pid] = {'bbox': best.bbox, 'last_seen': time.time(), 'history': deque(maxlen=self.smooth_frames), 'lost': 0}

                    # gather nearby objects and classify
                    px, py, pw, ph = best.bbox
                    margin = int(max(pw, ph) * self.margin_ratio)
                    ex = max(0, px - margin)
                    ey = max(0, py - margin)
                    ew = pw + margin * 2
                    eh = ph + margin * 2
                    nearby = []
                    for o in others:
                        cx, cy = self._bbox_center(o.bbox)
                        if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
                            nearby.append(o)
                            continue
                        if self._iou((ex, ey, ew, eh), o.bbox) > 0.05:
                            nearby.append(o)

                    activity, confidence = self.classifier.classify(nearby, head_pose, True)
                    hist = self.tracks[pid]['history']
                    hist.append((activity, confidence))
                    acts = [a for a, _ in hist]
                    most_common = max(set(acts), key=acts.count) if acts else activity
                    confidences = [c for a, c in hist if a == most_common]
                    avg_conf = sum(confidences) / len(confidences) if confidences else confidence

                    # determine if face overlaps this person's bbox
                    face_detected = False
                    for fx, fy, fw, fh in face_bboxes:
                        # simple IoU-ish overlap
                        if self._iou((fx, fy, fw, fh), best.bbox) > 0.02:
                            face_detected = True
                            break

                    per_person.append({'person_id': pid, 'bbox': best.bbox, 'activity': most_common, 'confidence': float(avg_conf), 'objects': [asdict(o) for o in nearby], 'face_detected': face_detected})
            except Exception:
                # fallback to simple matching below
                pass

        if not per_person:
            # Fallback matching (internal) when norfair isn't available or failed
            matched_track_ids = set()
            detected_assignments = {}

            now_ts = time.time()

            for p in persons:
                px, py, pw, ph = p.bbox
                center = self._bbox_center(p.bbox)

                # Find best matching track
                best_id = None
                best_score = 0.0
                for tid, t in list(self.tracks.items()):
                    tbbox = t.get('bbox')
                    if not tbbox:
                        continue
                    iou = self._iou(tbbox, p.bbox)
                    # center distance
                    tcx, tcy = self._bbox_center(tbbox)
                    dist = ((tcx - center[0]) ** 2 + (tcy - center[1]) ** 2) ** 0.5

                    score = iou
                    if score < 0.2:
                        score = max(0.0, 1.0 - (dist / max(self.max_center_distance, 1))) * 0.2

                    if score > best_score:
                        best_score = score
                        best_id = tid

                assigned_id = None
                if best_id is not None:
                    tbbox = self.tracks[best_id]['bbox']
                    iou_val = self._iou(tbbox, p.bbox)
                    tcx, tcy = self._bbox_center(tbbox)
                    dist = ((tcx - center[0]) ** 2 + (tcy - center[1]) ** 2) ** 0.5
                    if iou_val >= 0.25 or dist <= self.max_center_distance:
                        assigned_id = best_id

                if assigned_id is None:
                    assigned_id = self.next_person_id
                    self.next_person_id += 1
                    self.tracks[assigned_id] = {'bbox': p.bbox, 'last_seen': now_ts, 'history': deque(maxlen=self.smooth_frames), 'lost': 0}
                else:
                    self.tracks[assigned_id]['bbox'] = p.bbox
                    self.tracks[assigned_id]['last_seen'] = now_ts
                    self.tracks[assigned_id]['lost'] = 0

                matched_track_ids.add(assigned_id)
                detected_assignments[assigned_id] = p

            for tid, t in list(self.tracks.items()):
                if tid not in matched_track_ids:
                    t['lost'] = t.get('lost', 0) + 1
                    if t['lost'] > self.max_lost_frames:
                        del self.tracks[tid]

            for pid, p in detected_assignments.items():
                px, py, pw, ph = p.bbox
                margin = int(max(pw, ph) * self.margin_ratio)
                ex = max(0, px - margin)
                ey = max(0, py - margin)
                ew = pw + margin * 2
                eh = ph + margin * 2
                expanded = (ex, ey, ew, eh)

                nearby = []
                for o in others:
                    cx, cy = self._bbox_center(o.bbox)
                    if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
                        nearby.append(o)
                        continue

                    if self._iou(expanded, o.bbox) > 0.05:
                        nearby.append(o)

                activity, confidence = self.classifier.classify(nearby, head_pose, True)
                hist = self.tracks[pid].get('history')
                hist.append((activity, confidence))
                acts = [a for a, _ in hist]
                most_common = max(set(acts), key=acts.count) if acts else activity
                confidences = [c for a, c in hist if a == most_common]
                avg_conf = sum(confidences) / len(confidences) if confidences else confidence

                # check face overlap
                face_detected = False
                for fx, fy, fw, fh in face_bboxes:
                    if self._iou((fx, fy, fw, fh), p.bbox) > 0.02:
                        face_detected = True
                        break

                per_person.append({'person_id': pid, 'bbox': p.bbox, 'activity': most_common, 'confidence': float(avg_conf), 'objects': [asdict(o) for o in nearby], 'face_detected': face_detected})
        # Update tracking: match detected persons to existing tracks by IoU or center distance
        matched_track_ids = set()
        detected_assignments = {}

        now_ts = time.time()

        for p in persons:
            px, py, pw, ph = p.bbox
            center = self._bbox_center(p.bbox)

            # Find best matching track
            best_id = None
            best_score = 0.0
            for tid, t in list(self.tracks.items()):
                tbbox = t.get('bbox')
                if not tbbox:
                    continue
                iou = self._iou(tbbox, p.bbox)
                # center distance
                tcx, tcy = self._bbox_center(tbbox)
                dist = ((tcx - center[0]) ** 2 + (tcy - center[1]) ** 2) ** 0.5

                score = iou
                # if IoU very low, consider negative score but allow center match
                if score < 0.2:
                    # convert distance to a pseudo-score
                    score = max(0.0, 1.0 - (dist / max(self.max_center_distance, 1))) * 0.2

                if score > best_score:
                    best_score = score
                    best_id = tid

            # If the best match is acceptable (IoU or center close), assign it
            assigned_id = None
            if best_id is not None:
                # re-evaluate IoU/center for thresholding
                tbbox = self.tracks[best_id]['bbox']
                iou_val = self._iou(tbbox, p.bbox)
                tcx, tcy = self._bbox_center(tbbox)
                dist = ((tcx - center[0]) ** 2 + (tcy - center[1]) ** 2) ** 0.5
                if iou_val >= 0.25 or dist <= self.max_center_distance:
                    assigned_id = best_id

            if assigned_id is None:
                # create new track
                assigned_id = self.next_person_id
                self.next_person_id += 1
                self.tracks[assigned_id] = {
                    'bbox': p.bbox,
                    'last_seen': now_ts,
                    'history': deque(maxlen=self.smooth_frames),
                    'lost': 0
                }
            else:
                # update existing track
                self.tracks[assigned_id]['bbox'] = p.bbox
                self.tracks[assigned_id]['last_seen'] = now_ts
                self.tracks[assigned_id]['lost'] = 0

            matched_track_ids.add(assigned_id)
            detected_assignments[assigned_id] = p

        # Increment lost counters for unmatched tracks and remove old ones
        for tid, t in list(self.tracks.items()):
            if tid not in matched_track_ids:
                t['lost'] = t.get('lost', 0) + 1
                if t['lost'] > self.max_lost_frames:
                    del self.tracks[tid]

        # For each detected/assigned person, gather nearby objects and classify
        for pid, p in detected_assignments.items():
            px, py, pw, ph = p.bbox
            # expand bbox by margin
            margin = int(max(pw, ph) * self.margin_ratio)
            ex = max(0, px - margin)
            ey = max(0, py - margin)
            ew = pw + margin * 2
            eh = ph + margin * 2
            expanded = (ex, ey, ew, eh)

            # Collect nearby objects: center inside expanded OR IoU > small threshold
            nearby = []
            for o in others:
                cx, cy = self._bbox_center(o.bbox)
                if ex <= cx <= ex + ew and ey <= cy <= ey + eh:
                    nearby.append(o)
                    continue

                if self._iou(expanded, o.bbox) > 0.05:
                    nearby.append(o)

            # Classify activity for this person
            activity, confidence = self.classifier.classify(nearby, head_pose, True)

            # Use track-specific history for smoothing
            hist = self.tracks[pid].get('history')
            hist.append((activity, confidence))
            acts = [a for a, _ in hist]
            most_common = max(set(acts), key=acts.count) if acts else activity
            confidences = [c for a, c in hist if a == most_common]
            avg_conf = sum(confidences) / len(confidences) if confidences else confidence

            per_person.append({
                'person_id': pid,
                'bbox': p.bbox,
                'activity': most_common,
                'confidence': float(avg_conf),
                'objects': [asdict(o) for o in nearby]
            })

        return per_person


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
        elif self.detection_config.model == DetectionModel.YOLO:
            # Try YOLO detector (ultralytics); fall back to mock on failure
            model_name = getattr(self.config, 'yolo_model', 'yolov8n')
            yolo = YOLODetector(self.detection_config, model_name=model_name)
            if yolo.initialized:
                self.detector = yolo
            else:
                print("Falling back to mock detector")
                self.detector = MockDetector(self.detection_config)
        else:
            self.detector = MockDetector(self.detection_config)
            # If mock selected but ultralytics YOLO is available in the environment,
            # prefer to use YOLO for richer detections. This makes the app 'just work'
            # in environments where the user installed ultralytics but didn't set env var.
            try:
                # lazy import to avoid dependency when not installed
                from ultralytics import YOLO  # noqa: F401
                model_name = getattr(self.config, 'yolo_model', 'yolov8n')
                yolo = YOLODetector(self.detection_config, model_name=model_name)
                if yolo.initialized:
                    self.detector = yolo
                    print(f"Auto-switched to YOLO detector (model={model_name})")
            except Exception:
                # ultralytics not available or failed to init; keep mock
                pass
        
        self.classifier = ActivityClassifier(self.detection_config)
        # Per-person recognizer uses same classifier
        self.recognizer = ActivityRecognizer(self.detection_config, self.classifier)
        
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

        # Classify scene-level activity
        activity, confidence = self.classifier.classify(objects, head_pose, person_present)
        # Apply temporal smoothing for scene-level
        activity, confidence = self.classifier.smooth_activity(activity, confidence)

        # Per-person recognition (heuristic)
        per_person = self.recognizer.recognize(objects, head_pose) if objects else []

        # Build result
        result = DetectionResult(
            activity=activity,
            confidence=confidence,
            objects=[asdict(obj) for obj in objects],
            head_pose=head_pose,
            person_detected=person_present,
            per_person_activities=per_person,
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
        
        # Draw bounding boxes for objects (color-code people)
        for obj in result.objects:
            bbox = obj['bbox']
            x, y, w, h = bbox
            label = obj.get('label', '')
            score = obj.get('score', 0.0)

            # Color for person vs others
            if str(label).lower() == 'person':
                box_color = (0, 255, 0)  # green
                text_color = (0, 200, 0)
            else:
                box_color = (255, 0, 0)  # blue
                text_color = (255, 0, 0)

            # Draw thicker box for emphasis
            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 3)

            # Background for text for readability
            label_text = f"{label} {score:.2f}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, max(0, y - th - 8)), (x + tw + 6, y), (0, 0, 0), -1)
            cv2.putText(frame, label_text, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        
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

        # Draw per-person activity labels with their bbox
        if result.per_person_activities:
            for p in result.per_person_activities:
                bx, by, bw, bh = p.get('bbox', (0, 0, 0, 0))
                act = p.get('activity', '')
                conf = p.get('confidence', 0.0)

                label_text = f"{act} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                # draw a semi-transparent background box
                cv2.rectangle(frame, (bx, max(0, by - th - 10)), (bx + tw + 8, by), (0, 0, 0), -1)
                cv2.putText(frame, label_text, (bx + 4, by - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return frame

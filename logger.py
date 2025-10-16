"""
Event Logging Module
Handles time-stamped event logging with weekly rotation and session tracking
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import cv2
import numpy as np
from dataclasses import dataclass, asdict
from config import Config, LoggingConfig
from pathlib import PurePath
from PIL import Image
import io


@dataclass
class ActivityEvent:
    """Represents a single activity event"""
    session_id: str
    timestamp: str
    activity: str
    confidence: float
    duration_seconds: int
    detection_details: Dict
    snapshot: Optional[str] = None
    # per_person: list of dicts with keys: bbox, activity, confidence, snapshot (optional)
    per_person: Optional[List[Dict]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class ActivityLogger:
    """
    Manages activity event logging with:
    - Weekly file rotation
    - Session tracking
    - NDJSON format for streaming
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logging_config = config.logging
        
        # Setup logs directory
        self.logs_dir = Path(self.logging_config.logs_dir)
        self.logs_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize session
        self.session_id = self._generate_session_id()
        self.current_week_file = self._get_week_file()
        
        # Event buffer for batch writing
        self.event_buffer: List[ActivityEvent] = []
        self.buffer_size = self.logging_config.max_event_buffer
        
        print(f"Logger initialized: session={self.session_id}, file={self.current_week_file.name}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{self.logging_config.session_prefix}_{timestamp}"
    
    def _get_week_file(self) -> Path:
        """Get file path for current week"""
        today = datetime.now()
        year, week_num, _ = today.isocalendar()
        
        if self.logging_config.weekly_rotation:
            filename = f"{year}-W{week_num:02d}.{self.logging_config.log_format}"
        else:
            filename = f"activity_log.{self.logging_config.log_format}"
        
        return self.logs_dir / filename
    
    def log_activity(self, activity: str, confidence: float, 
                     duration: int, objects: List[Dict],
                     head_pose: Optional[Dict] = None,
                     per_person: Optional[List[Dict]] = None,
                     frame: Optional[bytes] = None) -> None:
        """
        Log a single activity event
        
        Args:
            activity: Activity type (e.g., "watching_reels")
            confidence: Detection confidence (0-1)
            duration: Duration in seconds
            objects: List of detected objects
            head_pose: Optional head pose information
        """
        event = ActivityEvent(
            session_id=self.session_id,
            timestamp=datetime.now().isoformat(),
            activity=activity,
            confidence=confidence,
            duration_seconds=duration,
            detection_details={
                "objects": objects,
                "head_pose": head_pose,
                "per_person_activities": per_person
            }
        )

        # Attach per_person list to top-level event (will be persisted)
        event.per_person = None
        # Only persist per-person entries that have a detected face (face_detected==True)
        if per_person:
            filtered = []
            for p in per_person:
                try:
                    if p.get('face_detected'):
                        filtered.append(dict(p))
                except Exception:
                    continue
            if filtered:
                event.per_person = filtered

        # Optionally save a small snapshot for the event and per-person crops
        if frame is not None:
            try:
                # Normalize frame to numpy array (BGR)
                frame_array = None
                if isinstance(frame, (bytes, bytearray)):
                    arr = np.frombuffer(frame, dtype=np.uint8)
                    im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    frame_array = im
                elif isinstance(frame, np.ndarray):
                    frame_array = frame
                else:
                    # Try PIL bytes
                    try:
                        from PIL import Image as PILImage
                        bio = io.BytesIO(frame)
                        pil = PILImage.open(bio).convert('RGB')
                        frame_array = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
                    except Exception:
                        frame_array = None

                # Save full-frame snapshot
                snapshot_path = None
                if frame_array is not None:
                    snapshot_path = self._save_numpy_snapshot_for_event(event, frame_array)
                else:
                    # fallback to writing raw bytes
                    snapshot_path = self._save_snapshot_for_event(event, frame)

                if snapshot_path:
                    event.snapshot = str(snapshot_path)

                # Save per-person cropped snapshots if possible
                if frame_array is not None and event.per_person:
                    for idx, person in enumerate(event.per_person):
                        try:
                            # Only save person snapshot if face_detected flag is present and True
                            if not person.get('face_detected'):
                                continue

                            bbox = person.get('bbox') or person.get('bbox', (0,0,0,0))
                            px, py, pw, ph = bbox
                            # sanitize
                            h, w = frame_array.shape[:2]
                            x1 = max(0, int(px))
                            y1 = max(0, int(py))
                            x2 = min(w, int(px + pw))
                            y2 = min(h, int(py + ph))
                            if x2 > x1 and y2 > y1:
                                crop = frame_array[y1:y2, x1:x2]
                                if crop.size > 0:
                                    person_snapshot = self._save_numpy_person_snapshot(event, idx, crop)
                                    if person_snapshot:
                                        person['snapshot'] = str(person_snapshot)
                        except Exception as e:
                            # non-fatal
                            continue
            except Exception as e:
                print(f"Warning: failed to save snapshot: {e}")

        self._write_event(event)
    
    def _write_event(self, event: ActivityEvent) -> None:
        """Write event to log file"""
        # Check if we need to rotate to new week file
        current_week_file = self._get_week_file()
        if current_week_file != self.current_week_file:
            self._flush_buffer()
            self.current_week_file = current_week_file
            print(f"Rotated to new log file: {current_week_file.name}")
        
        # Write based on format
        if self.logging_config.log_format == "ndjson":
            self._write_ndjson(event)
        else:
            self._write_json(event)
    
    def _write_ndjson(self, event: ActivityEvent) -> None:
        """Write event in NDJSON format (one JSON per line)"""
        d = event.to_dict()
        # Ensure snapshot field is included if set
        if hasattr(event, 'snapshot') and event.snapshot:
            d['snapshot'] = event.snapshot
        with open(self.current_week_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(d) + '\n')

    def _save_snapshot_for_event(self, event: ActivityEvent, frame_data) -> Optional[Path]:
        """Save a small JPEG snapshot for the event under logs/snapshots/YYYY-WNN/.

        frame_data can be bytes (encoded image) or a numpy array (BGR). Caller should
        ideally pass an encoded JPEG bytes for simplicity.
        """
        try:
            snapshots_dir = self.logs_dir / 'snapshots'
            snapshots_dir.mkdir(parents=True, exist_ok=True)

            # create subdir per week
            today = datetime.now()
            year, week_num, _ = today.isocalendar()
            week_dir = snapshots_dir / f"{year}-W{week_num:02d}"
            week_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{self.session_id}_{int(time.time())}.jpg"
            file_path = week_dir / filename

            # If frame_data is bytes, assume JPEG and write directly
            if isinstance(frame_data, (bytes, bytearray)):
                with open(file_path, 'wb') as f:
                    f.write(frame_data)
                return file_path

            # Otherwise, try to interpret as numpy array via PIL
            try:
                import numpy as np
                arr = np.asarray(frame_data)
                # Convert BGR (OpenCV) to RGB
                if arr.ndim == 3 and arr.shape[2] == 3:
                    arr = arr[:, :, ::-1]
                img = Image.fromarray(arr)
                img.thumbnail((640, 480))
                img.save(file_path, format='JPEG', quality=80)
                return file_path
            except Exception as e:
                # As last resort, try to write raw bytes
                with open(file_path, 'wb') as f:
                    f.write(bytes(frame_data))
                return file_path
        except Exception as e:
            print(f"Failed to save snapshot: {e}")
            return None

    def _save_numpy_snapshot_for_event(self, event: ActivityEvent, frame_array: 'np.ndarray') -> Optional[Path]:
        """Save a numpy BGR image as JPEG for the event"""
        try:
            snapshots_dir = self.logs_dir / 'snapshots'
            snapshots_dir.mkdir(parents=True, exist_ok=True)

            today = datetime.now()
            year, week_num, _ = today.isocalendar()
            week_dir = snapshots_dir / f"{year}-W{week_num:02d}"
            week_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{self.session_id}_{int(time.time())}.jpg"
            file_path = week_dir / filename

            # Convert BGR to RGB for PIL
            img_rgb = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
            from PIL import Image as PILImage
            pil = PILImage.fromarray(img_rgb)
            pil.thumbnail((1280, 720))
            pil.save(file_path, format='JPEG', quality=85)
            return file_path
        except Exception as e:
            print(f"Failed to save numpy snapshot: {e}")
            return None

    def _save_numpy_person_snapshot(self, event: ActivityEvent, person_idx: int, crop_array: 'np.ndarray') -> Optional[Path]:
        """Save a cropped person image for per-person snapshot"""
        try:
            snapshots_dir = self.logs_dir / 'snapshots'
            snapshots_dir.mkdir(parents=True, exist_ok=True)

            today = datetime.now()
            year, week_num, _ = today.isocalendar()
            week_dir = snapshots_dir / f"{year}-W{week_num:02d}"
            week_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{self.session_id}_person{person_idx}_{int(time.time())}.jpg"
            file_path = week_dir / filename

            img_rgb = cv2.cvtColor(crop_array, cv2.COLOR_BGR2RGB)
            from PIL import Image as PILImage
            pil = PILImage.fromarray(img_rgb)
            pil.thumbnail((640, 480))
            pil.save(file_path, format='JPEG', quality=80)
            return file_path
        except Exception as e:
            print(f"Failed to save person snapshot: {e}")
            return None
    
    def _write_json(self, event: ActivityEvent) -> None:
        """Write event in standard JSON array format"""
        # This is less efficient for streaming but more standard
        events = []
        
        # Read existing events
        if self.current_week_file.exists():
            with open(self.current_week_file, 'r', encoding='utf-8') as f:
                try:
                    events = json.load(f)
                except json.JSONDecodeError:
                    events = []
        
        # Append new event
        events.append(event.to_dict())
        
        # Write back
        with open(self.current_week_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2)
    
    def _flush_buffer(self) -> None:
        """Flush event buffer to disk"""
        if self.event_buffer:
            for event in self.event_buffer:
                self._write_event(event)
            self.event_buffer.clear()
    
    def read_events(self, file_path: Optional[Path] = None, 
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[Dict]:
        """
        Read events from log file with optional time filtering
        
        Args:
            file_path: Optional specific file to read (default: current week)
            start_time: Optional start time filter
            end_time: Optional end time filter
        
        Returns:
            List of event dictionaries
        """
        file_path = file_path or self.current_week_file
        
        if not file_path.exists():
            return []
        
        events = []
        
        if self.logging_config.log_format == "ndjson":
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if self._event_in_timerange(event, start_time, end_time):
                            events.append(event)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing event: {e}")
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    all_events = json.load(f)
                    events = [e for e in all_events 
                             if self._event_in_timerange(e, start_time, end_time)]
                except json.JSONDecodeError:
                    events = []
        
        return events
    
    def _event_in_timerange(self, event: Dict, 
                           start_time: Optional[datetime],
                           end_time: Optional[datetime]) -> bool:
        """Check if event falls within time range"""
        if not start_time and not end_time:
            return True
        
        try:
            event_time = datetime.fromisoformat(event['timestamp'])
        except (KeyError, ValueError):
            return False
        
        if start_time and event_time < start_time:
            return False
        if end_time and event_time > end_time:
            return False
        
        return True
    
    def get_all_log_files(self) -> List[Path]:
        """Get all log files in logs directory"""
        pattern = f"*.{self.logging_config.log_format}"
        return sorted(self.logs_dir.glob(pattern))
    
    def get_log_file_for_week(self, year: int, week: int) -> Optional[Path]:
        """Get log file for specific week"""
        filename = f"{year}-W{week:02d}.{self.logging_config.log_format}"
        file_path = self.logs_dir / filename
        return file_path if file_path.exists() else None
    
    def get_session_events(self, session_id: Optional[str] = None) -> List[Dict]:
        """Get all events for a specific session"""
        session_id = session_id or self.session_id
        all_events = self.read_events()
        return [e for e in all_events if e.get('session_id') == session_id]
    
    def get_stats(self) -> Dict:
        """Get logging statistics"""
        log_files = self.get_all_log_files()
        total_events = 0
        total_size_mb = 0.0
        
        for file_path in log_files:
            events = self.read_events(file_path)
            total_events += len(events)
            total_size_mb += file_path.stat().st_size / (1024 * 1024)
        
        return {
            "total_log_files": len(log_files),
            "total_events": total_events,
            "total_size_mb": round(total_size_mb, 2),
            "current_session": self.session_id,
            "current_week_file": self.current_week_file.name,
            "logs_directory": str(self.logs_dir)
        }
    
    def cleanup_old_logs(self, keep_weeks: int = 12) -> int:
        """
        Remove log files older than specified weeks
        
        Args:
            keep_weeks: Number of recent weeks to keep
        
        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.now() - timedelta(weeks=keep_weeks)
        cutoff_year, cutoff_week, _ = cutoff_date.isocalendar()
        
        deleted_count = 0
        for file_path in self.get_all_log_files():
            # Parse week from filename (format: YYYY-WNN.ext)
            try:
                name = file_path.stem
                if '-W' in name:
                    year_str, week_str = name.split('-W')
                    year, week = int(year_str), int(week_str)
                    
                    # Check if older than cutoff
                    if year < cutoff_year or (year == cutoff_year and week < cutoff_week):
                        file_path.unlink()
                        deleted_count += 1
                        print(f"Deleted old log: {file_path.name}")
            except (ValueError, IndexError) as e:
                print(f"Could not parse log file name: {file_path.name} - {e}")
        
        return deleted_count
    
    def close(self) -> None:
        """Cleanup and close logger"""
        self._flush_buffer()
        print(f"Logger closed: {self.session_id}")


class SessionTracker:
    """Track and manage activity sessions"""
    
    def __init__(self, logger: ActivityLogger):
        self.logger = logger
        self.session_start_time = datetime.now()
        self.current_activity = None
        self.activity_start_time = None
        self.activity_durations: Dict[str, int] = {}
    
    def start_activity(self, activity: str) -> None:
        """Start tracking a new activity"""
        # End previous activity if exists
        if self.current_activity:
            self.end_activity()
        
        self.current_activity = activity
        self.activity_start_time = time.time()
    
    def end_activity(self) -> Optional[int]:
        """End current activity and return duration"""
        if not self.current_activity or not self.activity_start_time:
            return None
        
        duration = int(time.time() - self.activity_start_time)
        
        # Update total duration for this activity
        if self.current_activity not in self.activity_durations:
            self.activity_durations[self.current_activity] = 0
        self.activity_durations[self.current_activity] += duration
        
        return duration
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        
        return {
            "session_id": self.logger.session_id,
            "session_start": self.session_start_time.isoformat(),
            "session_duration_minutes": round(session_duration / 60, 1),
            "activity_durations": {
                activity: round(duration / 60, 1)
                for activity, duration in self.activity_durations.items()
            },
            "current_activity": self.current_activity
        }

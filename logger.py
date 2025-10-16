"""
Event Logging Module
Handles time-stamped event logging with weekly rotation and session tracking
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from config import Config, LoggingConfig


@dataclass
class ActivityEvent:
    """Represents a single activity event"""
    session_id: str
    timestamp: str
    activity: str
    confidence: float
    duration_seconds: int
    detection_details: Dict
    
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
                     head_pose: Optional[Dict] = None) -> None:
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
                "head_pose": head_pose
            }
        )
        
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
        with open(self.current_week_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event.to_dict()) + '\n')
    
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

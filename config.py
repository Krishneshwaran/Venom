"""
Configuration module for Activity Monitor
Contains all settings, constants, and configuration management
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum
from pathlib import Path


class ActivityType(Enum):
    """All possible activity types that can be detected"""
    WATCHING_REELS = "watching_reels"
    WATCHING_TV = "watching_tv"
    WORKING = "working"
    READING = "reading"
    IDLE = "idle"
    ABSENT = "absent"
    BROWSING = "browsing"


class DetectionModel(Enum):
    """Available detection models"""
    MOCK = "mock"
    MEDIAPIPE = "mediapipe"
    YOLO = "yolo"


@dataclass
class DetectionConfig:
    """Detection and recognition thresholds"""
    model: DetectionModel = DetectionModel.MOCK
    min_confidence: float = 0.5
    temporal_smoothing_frames: int = 5
    # Process every Nth frame. Lower = more responsive but higher CPU usage.
    frame_skip: int = 3  # balanced responsiveness
    
    # Activity-specific thresholds
    phone_detection_threshold: float = 0.7
    phone_hold_duration_sec: int = 10
    tv_view_duration_sec: int = 30
    laptop_work_duration_sec: int = 30
    absent_duration_sec: int = 60

    # Minimum seconds before logging an activity (can be lowered for faster switching)
    min_log_duration: int = 5
    
    # Head pose thresholds for activity classification
    phone_pitch_min: float = -45.0  # Looking down
    phone_pitch_max: float = -10.0
    tv_yaw_range: float = 15.0  # Looking straight
    tv_pitch_range: float = 10.0


@dataclass
class LoggingConfig:
    """Logging and storage configuration"""
    logs_dir: str = "logs"
    log_format: str = "ndjson"  # ndjson or json
    weekly_rotation: bool = True
    session_prefix: str = "session"
    max_event_buffer: int = 100


@dataclass
class SchedulerConfig:
    """Scheduler settings for periodic tasks"""
    enable_weekly_report: bool = True
    report_day: str = "mon"  # Monday
    report_hour: int = 9
    report_minute: int = 0
    
    # Aggregation intervals
    aggregation_interval_minutes: int = 60


@dataclass
class NotificationConfig:
    """Notification delivery settings"""
    enable_email: bool = False
    enable_desktop: bool = True
    enable_console: bool = True
    
    email_from: str = "noreply@activitytracker.local"
    email_to: Optional[str] = None


@dataclass
class APIConfig:
    """External API credentials and endpoints"""
    groq_api_key: Optional[str] = None
    groq_endpoint: str = "https://api.groq.com/openai/v1/chat/completions"
    groq_model: str = "mixtral-8x7b-32768"
    groq_timeout: int = 20
    
    resend_api_key: Optional[str] = None
    resend_endpoint: str = "https://api.resend.com/emails"
    resend_timeout: int = 10


@dataclass
class Config:
    """Main configuration class combining all settings"""
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    api: APIConfig = field(default_factory=APIConfig)
    
    # Display settings
    show_camera_feed: bool = True
    display_width: int = 640
    display_height: int = 480
    # Camera index (default 0)
    camera_index: int = 0
    # Allow overriding YOLO model name
    yolo_model: str = "yolov8n"
    # Debug toggle to print detections each frame
    debug_detections: bool = False
    # Raw overlay mode: show raw detected objects on screen and bypass activity classifier
    raw_overlay: bool = False
    # Report customization
    report_logo_path: Optional[str] = None
    report_theme_color: Optional[str] = None  # hex color e.g. '#2B8CFF'
    report_font: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables"""
        config = cls()
        
        # API keys from environment
        config.api.groq_api_key = os.getenv("GROQ_API_KEY")
        config.api.resend_api_key = os.getenv("RESEND_API_KEY")
        
        # Email configuration
        config.notification.email_to = os.getenv("NOTIFICATION_EMAIL")
        if config.notification.email_to:
            config.notification.enable_email = True
        
        # Detection model
        model_name = os.getenv("DETECTION_MODEL", "mock").upper()
        try:
            config.detection.model = DetectionModel[model_name]
        except KeyError:
            config.detection.model = DetectionModel.MOCK

        # Camera index
        try:
            config.camera_index = int(os.getenv('CAMERA_INDEX', '0'))
        except Exception:
            config.camera_index = 0

        # Allow overriding min confidence via env
        try:
            conf_env = os.getenv('DETECTION_MIN_CONF')
            if conf_env is not None:
                config.detection.min_confidence = float(conf_env)
        except Exception:
            pass

        # YOLO model override
        config.yolo_model = os.getenv('YOLO_MODEL', config.yolo_model)

        # Debug toggle
        config.debug_detections = os.getenv('DEBUG_DETECTIONS', '0') in ('1', 'true', 'True')

        # Raw overlay toggle
        config.raw_overlay = os.getenv('RAW_OVERLAY', '0') in ('1', 'true', 'True')

        # Logging directory
        logs_dir = os.getenv("LOGS_DIR", "logs")
        config.logging.logs_dir = logs_dir
        Path(logs_dir).mkdir(exist_ok=True)

        # Report customization from env
        config.report_logo_path = os.getenv('REPORT_LOGO') or None
        config.report_theme_color = os.getenv('REPORT_THEME_COLOR') or None
        config.report_font = os.getenv('REPORT_FONT') or None

        return config
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration and return (is_valid, errors)"""
        errors = []
        
        # Check if logs directory is writable
        logs_path = Path(self.logging.logs_dir)
        if not logs_path.exists():
            try:
                logs_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create logs directory: {e}")
        
        # Check API keys if features enabled
        if self.notification.enable_email and not self.api.resend_api_key:
            errors.append("Email notifications enabled but RESEND_API_KEY not set")
        
        if self.notification.enable_email and not self.notification.email_to:
            errors.append("Email notifications enabled but NOTIFICATION_EMAIL not set")
        
        # Validate thresholds
        if not 0 <= self.detection.min_confidence <= 1:
            errors.append("min_confidence must be between 0 and 1")
        
        if self.detection.temporal_smoothing_frames < 1:
            errors.append("temporal_smoothing_frames must be >= 1")
        
        return len(errors) == 0, errors


# Activity detection rules and weights
ACTIVITY_RULES = {
    ActivityType.WATCHING_REELS: {
        "required_objects": ["phone"],
        "head_pose_criteria": {
            "pitch": (-45, -10),  # Looking down
            "yaw": (-20, 20)
        },
        "min_duration": 10,
        "priority": 3
    },
    ActivityType.WATCHING_TV: {
        "required_objects": ["tv", "monitor"],
        "head_pose_criteria": {
            "pitch": (-10, 10),  # Looking straight
            "yaw": (-15, 15)
        },
        "min_duration": 30,
        "priority": 2
    },
    ActivityType.WORKING: {
        "required_objects": ["laptop", "keyboard"],
        "hand_activity": True,
        "head_pose_criteria": {
            "pitch": (-20, 5),
            "yaw": (-30, 30)
        },
        "min_duration": 30,
        "priority": 4
    },
    ActivityType.READING: {
        "required_objects": ["book"],
        "head_pose_criteria": {
            "pitch": (-30, -5)
        },
        "min_duration": 20,
        "priority": 2
    },
    ActivityType.IDLE: {
        "required_objects": [],
        "person_present": True,
        "min_duration": 10,
        "priority": 1
    },
    ActivityType.ABSENT: {
        "person_present": False,
        "min_duration": 60,
        "priority": 0
    }
}


# Object labels for different detection models
OBJECT_LABELS = {
    "phone": ["cell phone", "mobile", "smartphone"],
    "tv": ["tv", "television", "monitor", "screen"],
    "laptop": ["laptop", "notebook computer"],
    "keyboard": ["keyboard"],
    "mouse": ["mouse"],
    "book": ["book"]
}


# Productivity classification
PRODUCTIVE_ACTIVITIES = [
    ActivityType.WORKING.value,
    ActivityType.READING.value
]

UNPRODUCTIVE_ACTIVITIES = [
    ActivityType.WATCHING_REELS.value,
    ActivityType.WATCHING_TV.value
]

NEUTRAL_ACTIVITIES = [
    ActivityType.IDLE.value,
    ActivityType.BROWSING.value,
    ActivityType.ABSENT.value
]

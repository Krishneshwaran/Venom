# Activity Monitor - System Architecture

## 📐 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                     ACTIVITY MONITOR SYSTEM                         │
└────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│   Webcam    │ (Input: 640x480 @ 30fps)
└──────┬──────┘
       │ Frame Stream
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DETECTION LAYER                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  Object     │  │ Pose/Head    │  │  Activity           │   │
│  │  Detection  │  │  Detection   │  │  Classifier         │   │
│  │             │  │              │  │                     │   │
│  │ • Phone     │  │ • Yaw        │  │ • watching_reels    │   │
│  │ • Laptop    │  │ • Pitch      │  │ • working           │   │
│  │ • TV        │  │ • Roll       │  │ • watching_tv       │   │
│  │ • Book      │  │              │  │ • reading           │   │
│  └─────────────┘  └──────────────┘  │ • idle              │   │
│                                      │ • absent            │   │
│                                      └─────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ DetectionResult
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LOGGING LAYER                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ActivityLogger                                          │   │
│  │  • Session tracking                                      │   │
│  │  • NDJSON format                                         │   │
│  │  • Weekly rotation (2025-W42.ndjson)                    │   │
│  │  • Event schema validation                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Event Stream
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AGGREGATION LAYER                            │
│  ┌────────────┐  ┌────────────┐  ┌───────────────────────┐    │
│  │  Weekly    │  │   Daily    │  │  Multi-Week           │    │
│  │  Summary   │  │  Summary   │  │  Trends               │    │
│  │            │  │            │  │                       │    │
│  │ • Total    │  │ • Hours    │  │ • Week-over-week      │    │
│  │   hours    │  │ • Activity │  │ • Pattern detection   │    │
│  │ • Activity │  │   breakdown│  │ • Insights            │    │
│  │   breakdown│  │            │  │                       │    │
│  │ • Prod %   │  │            │  │                       │    │
│  └────────────┘  └────────────┘  └───────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Aggregated Data
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PREDICTION LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  GroqPredictor (AI Engine)                               │  │
│  │                                                           │  │
│  │  Input Features:                                         │  │
│  │  • Activity percentages                                  │  │
│  │  • Productivity metrics                                  │  │
│  │  • Trends                                                │  │
│  │                                                           │  │
│  │  Output:                                                 │  │
│  │  • Risk level (Low/Medium/High)                         │  │
│  │  • Personalized suggestions                             │  │
│  │  • Actionable recommendations                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Suggestions & Insights
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NOTIFICATION LAYER                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Email     │  │   Desktop    │  │      Console         │  │
│  │  (Resend)   │  │ Notification │  │    Rich Output       │  │
│  │             │  │              │  │                      │  │
│  │ • HTML      │  │ • Toast      │  │ • Bar charts         │  │
│  │   formatted │  │   popup      │  │ • Colored text       │  │
│  │ • Charts    │  │ • System     │  │ • Summaries          │  │
│  │ • Trends    │  │   native     │  │                      │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

### 1. Real-time Capture & Detection
```
Webcam (30fps) 
  → Frame capture (every 30th frame)
  → Object detection
  → Pose estimation
  → Activity classification
  → Temporal smoothing (10 frames)
  → Activity label + confidence
```

### 2. Event Logging
```
Activity change detected
  → Calculate duration
  → Build event object
  → Append to NDJSON file
  → Update session tracker
```

### 3. Aggregation (On-demand or Scheduled)
```
Read log file(s)
  → Parse NDJSON events
  → Group by activity
  → Calculate totals & percentages
  → Compute productivity metrics
  → Compare with previous periods
```

### 4. AI Prediction (Weekly or On-demand)
```
Weekly summary
  → Format prompt for Groq
  → Call API with features
  → Parse response
  → Extract suggestions
  → Fallback if API fails
```

### 5. Notification Delivery
```
Report data
  → Format for each channel
  → Send email (Resend API)
  → Show desktop notification
  → Print to console
```

## 🗂️ File Structure

```
Activity Monitor/
│
├── 📄 Core Application Files
│   ├── main.py              # Entry point, CLI, orchestration
│   ├── config.py            # Configuration, constants, rules
│   ├── detector.py          # Detection engine
│   ├── logger.py            # Event logging & storage
│   ├── aggregator.py        # Data analysis & summarization
│   ├── predictor.py         # AI predictions (Groq)
│   └── notifier.py          # Multi-channel notifications
│
├── 📋 Documentation
│   ├── README.md            # Full documentation
│   ├── QUICKSTART.md        # Setup guide
│   ├── PROJECT_SUMMARY.md   # Project overview
│   └── ARCHITECTURE.md      # This file
│
├── ⚙️ Configuration
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   ├── .env                 # Your API keys (not in git)
│   └── .gitignore           # Git ignore rules
│
├── 🧪 Testing
│   └── test_setup.py        # System verification
│
├── 📊 Data
│   └── logs/                # Activity logs (NDJSON)
│       ├── 2025-W42.ndjson
│       ├── 2025-W43.ndjson
│       └── ...
│
└── 🔧 Environment
    └── env/                 # Virtual environment (not in git)
```

## 🎯 Module Dependencies

```
main.py
  ├─→ config.py (Config)
  ├─→ detector.py (ActivityDetector)
  │   └─→ config.py (DetectionConfig, ACTIVITY_RULES)
  ├─→ logger.py (ActivityLogger, SessionTracker)
  │   └─→ config.py (LoggingConfig)
  ├─→ aggregator.py (ActivityAggregator)
  │   ├─→ logger.py (ActivityLogger)
  │   └─→ config.py (PRODUCTIVE_ACTIVITIES)
  ├─→ predictor.py (GroqPredictor)
  │   └─→ config.py (APIConfig)
  └─→ notifier.py (NotificationManager)
      └─→ config.py (NotificationConfig, APIConfig)
```

## 📦 External Dependencies

### Required
- **opencv-python** - Camera capture & computer vision
- **numpy** - Numerical operations for image processing
- **requests** - HTTP requests for APIs
- **APScheduler** - Background task scheduling

### Optional
- **mediapipe** - Real pose & face detection
- **plyer** - Cross-platform desktop notifications

## 🔐 Security & Privacy

### Data Storage
```
All personal data → Local filesystem only
  └─→ logs/ directory (NDJSON files)
      • No cloud storage
      • User controls retention
      • Easy to delete
```

### External API Calls
```
Groq API (optional)
  ├─→ Sends: Aggregated statistics (no images/video)
  ├─→ Receives: Text suggestions
  └─→ Frequency: Once per week

Resend API (optional)
  ├─→ Sends: HTML email report
  ├─→ Frequency: Once per week
  └─→ Recipient: User-configured email
```

### Camera Access
```
Webcam
  ├─→ Real-time processing only
  ├─→ Frames never saved to disk
  ├─→ Only detection metadata logged
  └─→ User can disable camera feed display
```

## ⚡ Performance

### Resource Usage
- **CPU**: ~5-10% (with frame skipping)
- **Memory**: ~100-200 MB
- **Disk**: ~1-5 MB per week of logs
- **Network**: Minimal (only for weekly API calls)

### Optimization Strategies
1. **Frame Skipping**: Process every 30th frame (1fps effective)
2. **Temporal Smoothing**: Reduce classification jitter
3. **Append-only Logging**: Fast O(1) writes
4. **NDJSON Format**: Streaming-friendly, no parse overhead
5. **Background Scheduler**: Non-blocking report generation

## 🔄 Lifecycle

### Application Startup
```
1. Load configuration (.env + defaults)
2. Validate configuration
3. Initialize all components
   ├─→ Logger (create session)
   ├─→ Detector (load models or use mock)
   ├─→ Aggregator (connect to logger)
   ├─→ Predictor (check API key)
   ├─→ Notifier (configure channels)
   └─→ Scheduler (setup jobs)
4. Start scheduler
5. Open camera
6. Enter main loop
```

### Main Loop (While Running)
```
1. Capture frame from webcam
2. Every 30th frame:
   ├─→ Run detection
   ├─→ Classify activity
   ├─→ Check for activity change
   └─→ Log event if changed (duration > 5s)
3. Update display overlay
4. Handle keyboard input (q, p, s, r)
5. Repeat
```

### Shutdown
```
1. Stop camera
2. Log final activity
3. Close logger
4. Stop scheduler
5. Display session summary
6. Display logging statistics
7. Exit cleanly
```

### Scheduled Weekly Report
```
Every Monday at 9:00 AM:
1. Read last week's log file
2. Aggregate events into summary
3. Calculate trends (vs previous week)
4. Generate insights
5. Call Groq API for suggestions
6. Calculate risk assessment
7. Format report for each channel
8. Send notifications
9. Log completion
```

## 🧩 Extension Points

### Adding New Activities
```python
# 1. Add to config.py
class ActivityType(Enum):
    NEW_ACTIVITY = "new_activity"

# 2. Add detection rule
ACTIVITY_RULES[ActivityType.NEW_ACTIVITY] = {
    "required_objects": ["object_name"],
    "head_pose_criteria": {"pitch": (-20, 10)},
    "min_duration": 15,
    "priority": 3
}
```

### Adding New Detection Model
```python
# In detector.py
class YourDetector(BaseDetector):
    def detect_objects(self, frame):
        # Your implementation
        pass
    
    def detect_pose(self, frame):
        # Your implementation
        pass
    
    def detect_person(self, frame):
        # Your implementation
        pass
```

### Adding New Notification Channel
```python
# In notifier.py
def _send_slack(self, summary, suggestions):
    # Slack webhook implementation
    pass
```

## 📊 Data Schema

### Event Schema (NDJSON)
```typescript
interface ActivityEvent {
  session_id: string;        // "session_2025-10-16_21-05-34"
  timestamp: string;         // ISO 8601 format
  activity: string;          // Activity type
  confidence: number;        // 0.0 to 1.0
  duration_seconds: number;  // Event duration
  detection_details: {
    objects: Array<{
      label: string;
      score: number;
      bbox: [number, number, number, number]  // [x, y, w, h]
    }>;
    head_pose?: {
      yaw: number;
      pitch: number;
      roll: number;
    }
  }
}
```

### Weekly Summary Schema
```typescript
interface WeeklySummary {
  week_start: string;                    // "2025-10-13"
  week_end: string;                      // "2025-10-19"
  year: number;
  week_number: number;
  total_present_hours: number;
  time_breakdown_hours: Record<string, number>;
  productive_hours: number;
  unproductive_hours: number;
  productive_percentage: number;
  average_confidences: Record<string, number>;
  daily_breakdown: Record<string, Record<string, number>>;
  total_events: number;
  generated_at: string;
}
```

## 🎯 Success Metrics

The system is considered successful when:
- ✅ Runs continuously for 8+ hours without crash
- ✅ Accurately detects 80%+ of activity changes
- ✅ Weekly reports generated automatically
- ✅ AI suggestions are actionable and relevant
- ✅ User can track productivity improvements over time

---

**This architecture enables reliable, privacy-focused activity monitoring with AI-powered insights!** 🚀

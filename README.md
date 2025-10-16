# Activity Monitor

A comprehensive activity tracking system that monitors your computer usage through webcam, classifies activities using AI, and generates weekly reports with personalized productivity insights.

## 🎯 Features

- **Real-time Activity Detection**: Automatically detects what you're doing (working, watching phone/TV, reading, idle)
- **Smart Classification**: Uses object detection and pose estimation for accurate activity recognition
- **Weekly Reports**: Automated weekly summaries with productivity metrics
- **AI-Powered Insights**: Get personalized suggestions from Groq AI based on your activity patterns
- **Trend Analysis**: Track improvements and changes week-over-week
- **Multi-channel Notifications**: Receive reports via email, desktop notifications, or console
- **Privacy-Focused**: All data stored locally in JSON format

## 📋 Architecture

```
┌─────────────┐
│   Webcam    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Activity Detector  │  (Object detection + Pose estimation)
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │    Logger    │  (NDJSON files, weekly rotation)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  Aggregator  │  (Weekly summaries, trends)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  Predictor   │  (Groq AI for suggestions)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  Notifier    │  (Email via Resend / Desktop / Console)
    └──────────────┘
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Webcam
- (Optional) Groq API key for AI suggestions
- (Optional) Resend API key for email notifications

### Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd "E:\Vijay tv\Assistant\Activity Monitor"
   ```

2. **Activate the virtual environment** (if using one):
   ```powershell
   .\env\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   copy .env.example .env
   ```
   Then edit `.env` and fill in your API keys (optional for testing)

### Quick Start (Mock Mode)

Test the system without ML models or API keys:

```bash
python main.py
```

This will:
- Start webcam capture
- Run mock detection (cycles through different activities)
- Log events to `logs/` directory
- Show real-time activity on screen

**Keyboard Controls**:
- `q`: Quit
- `p`: Pause/Resume
- `s`: Show session summary
- `r`: Generate weekly report now

### Advanced Usage

**View weekly report**:
```bash
python main.py --report
```

**View daily report**:
```bash
python main.py --daily
# Or for specific date:
python main.py --daily 2025-10-15
```

**Clean up old logs** (keep last 12 weeks):
```bash
python main.py --cleanup 12
```

**Test email configuration**:
```bash
python main.py --test-email
```

**Run without camera display**:
```bash
python main.py --no-camera
```

## 📁 Project Structure

```
Activity Monitor/
├── main.py           # Main application entry point
├── config.py         # Configuration and constants
├── detector.py       # Activity detection (object + pose)
├── logger.py         # Event logging with weekly rotation
├── aggregator.py     # Data aggregation and analysis
├── predictor.py      # AI predictions using Groq
├── notifier.py       # Multi-channel notifications
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variables template
├── README.md         # This file
└── logs/             # Activity logs (NDJSON format)
    └── 2025-W42.ndjson
```

## ⚙️ Configuration

### Detection Settings

Edit `config.py` or set environment variables:

```python
DETECTION_MODEL=mock  # mock | mediapipe | yolo
```

### Activity Types

The system detects:
- `watching_reels`: Using phone (looking down)
- `watching_tv`: Watching TV/monitor
- `working`: Using laptop/keyboard
- `reading`: Reading a book
- `idle`: Present but no specific activity
- `absent`: Not present

### Thresholds

Customize in `config.py`:
- `min_confidence`: Minimum detection confidence (default: 0.6)
- `temporal_smoothing_frames`: Frames to smooth activity changes (default: 10)
- `frame_skip`: Process every Nth frame (default: 30)

## 📊 Data Format

Events are logged in NDJSON format (one JSON per line):

```json
{
  "session_id": "session_2025-10-16_21-05-34",
  "timestamp": "2025-10-16T21:05:40+05:30",
  "activity": "watching_reels",
  "confidence": 0.92,
  "duration_seconds": 65,
  "detection_details": {
    "objects": [
      {"label": "phone", "score": 0.93, "bbox": [100, 150, 80, 160]}
    ],
    "head_pose": {"yaw": 2.1, "pitch": -20.5, "roll": 0.3}
  }
}
```

## 🤖 AI Integration

### Groq API

The system sends weekly summaries to Groq for AI-powered analysis:

```python
# Features sent to Groq:
- Total active hours
- Activity breakdown (% time in each activity)
- Productivity percentage
- Week-over-week trends

# Response includes:
- Risk assessment (Low/Medium/High)
- Personalized suggestions
- Motivational insights
```

If Groq API is not configured, falls back to rule-based suggestions.

### Example Groq Prompt

```
Weekly Activity Summary:
- Total present: 42.5 hours
- Working: 12.5 hours
- Phone/Reels: 18.2 hours
- TV: 7.3 hours
- Productivity: 29.4%

Trends: +8% phone time, -5% working time

Provide: Risk assessment and 3-5 actionable suggestions.
```

## 📧 Notifications

### Email (via Resend)

Beautifully formatted HTML emails with:
- Weekly metrics dashboard
- Activity breakdown with visual bars
- Trend indicators
- AI suggestions
- Risk assessment

### Desktop Notifications

Quick summary popups (requires `plyer` package).

### Console Output

Detailed reports in terminal with:
- ASCII bar charts
- Color-coded metrics
- Trend summaries

## 🔒 Privacy & Security

- **All data stays local**: Events stored in local `logs/` directory
- **No cloud storage**: Only API calls are for AI suggestions (optional)
- **Webcam privacy**: Camera feed never saved to disk
- **API keys**: Store in `.env` file (never commit)
- **Data cleanup**: Automatic log rotation and cleanup tools

## 🛠️ Development

### Adding New Activity Types

1. Add to `config.py`:
   ```python
   class ActivityType(Enum):
       YOUR_ACTIVITY = "your_activity"
   ```

2. Add detection rules in `ACTIVITY_RULES`:
   ```python
   ActivityType.YOUR_ACTIVITY: {
       "required_objects": ["object_name"],
       "head_pose_criteria": {"pitch": (-30, 0)},
       "min_duration": 15,
       "priority": 3
   }
   ```

### Switching to Real Detection

1. Install MediaPipe:
   ```bash
   pip install mediapipe
   ```

2. Update `.env`:
   ```
   DETECTION_MODEL=mediapipe
   ```

3. For object detection, integrate YOLO in `detector.py`

### Custom Schedulers

Add jobs in `ReportScheduler`:

```python
self.scheduler.add_job(
    your_function,
    'cron',
    day_of_week='mon,fri',
    hour=9,
    minute=0
)
```

## 📝 Example Weekly Report

```
📊 WEEKLY ACTIVITY REPORT
Week: 2025-10-13 to 2025-10-19

🔴 Risk Level: MEDIUM
Some habits could be improved to boost productivity.

Total Active Time: 42.5 hours
Productivity: 29.4%

🎯 Activity Breakdown:
  Watching Reels      18.2h [████████████████████ ] 42.8%
  Working             12.5h [█████████████        ] 29.4%
  Watching Tv          7.3h [████████             ] 17.2%
  Idle                 4.5h [█████                ] 10.6%

📊 Trends:
  📈 Phone usage increased by 8%
  📉 Working time decreased by 5%

💡 AI Suggestions:
1. Reduce phone time by 2 hours daily using app blockers
2. Try Pomodoro Technique for focused work sessions
3. Schedule work in mornings when fresh and focused
4. Use physical distance - keep phone in another room
5. Set specific 'no phone' hours during peak work time

🌱 Keep pushing forward! Small changes lead to big results.
```

## 🤝 Contributing

Ideas for improvements:
- [ ] Add sound-based activity detection
- [ ] Machine learning classifier for complex activities
- [ ] Mobile app integration
- [ ] Calendar integration for context
- [ ] Focus mode with website blockers
- [ ] Pomodoro timer integration
- [ ] Goal setting and tracking

## 📄 License

This project is for personal use. Modify as needed!

## 🙏 Acknowledgments

- MediaPipe for pose detection
- Groq for AI inference
- Resend for email delivery
- OpenCV for computer vision

---

**Made with ❤️ for better productivity and self-awareness**

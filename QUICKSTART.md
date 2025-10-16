# Quick Start Guide for Activity Monitor

## First Time Setup

### 1. Check Python Installation
```powershell
python --version
# Should show Python 3.10 or higher
```

### 2. Install Dependencies
```powershell
# If you haven't activated the virtual environment:
.\env\Scripts\Activate.ps1

# Install required packages:
pip install opencv-python numpy requests APScheduler
```

### 3. Test the Installation
```powershell
# Run a quick test to verify all modules load correctly:
python -c "from config import Config; from detector import ActivityDetector; from logger import ActivityLogger; print('✓ All modules loaded successfully')"
```

### 4. Start in Mock Mode (No API Keys Required)
```powershell
python main.py
```

This will:
- Open your webcam
- Show simulated activity detection (cycling through activities)
- Log events to `logs/` folder
- Display real-time activity on screen

**Controls:**
- Press `q` to quit
- Press `p` to pause/resume
- Press `s` to show session summary

### 5. View Your First Report
After running for a few minutes, stop the app (press `q`), then:
```powershell
python main.py --report
```

## Optional: Add AI Suggestions

### 1. Get Groq API Key
1. Visit https://console.groq.com
2. Sign up / log in
3. Create an API key
4. Copy the key

### 2. Configure Environment
```powershell
# Copy the example environment file:
copy .env.example .env

# Edit .env file and add your key:
# GROQ_API_KEY=your_actual_key_here
```

### 3. Run with AI Suggestions
```powershell
python main.py
# Now when you generate reports, you'll get AI-powered suggestions!
```

## Optional: Add Email Notifications

### 1. Get Resend API Key
1. Visit https://resend.com
2. Sign up / log in
3. Create an API key
4. Verify your email domain (or use test mode)

### 2. Configure Email
Edit `.env`:
```
RESEND_API_KEY=your_resend_key_here
NOTIFICATION_EMAIL=your-email@example.com
```

### 3. Test Email
```powershell
python main.py --test-email
```

## Usage Examples

### Normal Monitoring
```powershell
# Start monitoring with camera display:
python main.py

# Start without camera display (lighter on resources):
python main.py --no-camera
```

### View Reports
```powershell
# Current week report:
python main.py --report

# Today's report:
python main.py --daily

# Specific date:
python main.py --daily 2025-10-15
```

### Maintenance
```powershell
# Clean up old logs (keep last 12 weeks):
python main.py --cleanup 12
```

## Troubleshooting

### Camera Not Opening
- Make sure no other app is using the webcam
- Check Windows privacy settings (Camera access)
- Try closing other apps that might use the camera

### Import Errors
```powershell
# Reinstall dependencies:
pip install --force-reinstall -r requirements.txt
```

### No Events Logged
- Check that `logs/` directory exists
- Verify you have write permissions
- Let the app run for at least 30 seconds before checking

### API Errors
- Verify your API keys in `.env` file
- Check internet connection
- Try running `python main.py --test-email` to diagnose

## Tips for Best Results

1. **Good Lighting**: Ensure your face is well-lit for better detection
2. **Stable Camera**: Mount webcam steadily for consistent results
3. **Regular Position**: Sit in a consistent position for accurate tracking
4. **Run Continuously**: Leave running during work hours for best insights
5. **Weekly Reviews**: Check reports every Monday to track progress

## Next Steps

1. Run the app for a full week
2. Review your first weekly report
3. Adjust your habits based on insights
4. Track improvements week-over-week

Happy tracking! 📊✨

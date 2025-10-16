"""
Test script to verify Activity Monitor setup
Run this to check if all components are working correctly
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all modules can be imported"""
    print("Testing module imports...")
    try:
        from config import Config, ActivityType
        from detector import ActivityDetector
        from logger import ActivityLogger, SessionTracker
        from aggregator import ActivityAggregator
        from predictor import GroqPredictor
        from notifier import NotificationManager
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    try:
        from config import Config
        config = Config.from_env()
        is_valid, errors = config.validate()
        if is_valid:
            print("✓ Configuration valid")
        else:
            print("⚠️ Configuration warnings:")
            for error in errors:
                print(f"  - {error}")
        return True
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False

def test_detector():
    """Test detector initialization"""
    print("\nTesting detector...")
    try:
        from config import Config
        from detector import ActivityDetector
        import numpy as np
        
        config = Config.from_env()
        detector = ActivityDetector(config)
        
        # Test with dummy frame
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.detect_activity(dummy_frame)
        
        print(f"✓ Detector working - detected activity: {result.activity}")
        return True
    except Exception as e:
        print(f"✗ Detector failed: {e}")
        return False

def test_logger():
    """Test logger"""
    print("\nTesting logger...")
    try:
        from config import Config
        from logger import ActivityLogger
        
        config = Config.from_env()
        logger = ActivityLogger(config)
        
        # Test logging
        logger.log_activity(
            activity="test_activity",
            confidence=0.9,
            duration=10,
            objects=[{"label": "test", "score": 0.9, "bbox": (0, 0, 10, 10)}],
            head_pose={"yaw": 0, "pitch": 0, "roll": 0}
        )
        
        # Test reading
        events = logger.read_events()
        
        print(f"✓ Logger working - {len(events)} events in current log")
        
        # Cleanup test
        logger.close()
        return True
    except Exception as e:
        print(f"✗ Logger failed: {e}")
        return False

def test_aggregator():
    """Test aggregator"""
    print("\nTesting aggregator...")
    try:
        from config import Config
        from logger import ActivityLogger
        from aggregator import ActivityAggregator
        
        config = Config.from_env()
        logger = ActivityLogger(config)
        aggregator = ActivityAggregator(logger, config)
        
        summary = aggregator.get_weekly_summary()
        print(f"✓ Aggregator working - weekly summary generated")
        print(f"  Total events: {summary.get('total_events', 0)}")
        print(f"  Total hours: {summary.get('total_present_hours', 0):.1f}")
        
        return True
    except Exception as e:
        print(f"✗ Aggregator failed: {e}")
        return False

def test_predictor():
    """Test predictor"""
    print("\nTesting predictor...")
    try:
        from config import Config
        from predictor import GroqPredictor
        
        config = Config.from_env()
        predictor = GroqPredictor(config)
        
        # Test with dummy summary
        dummy_summary = {
            "week_start": "2025-10-13",
            "week_end": "2025-10-19",
            "total_present_hours": 40.0,
            "productive_percentage": 50.0,
            "time_breakdown_hours": {
                "working": 20.0,
                "watching_reels": 15.0,
                "idle": 5.0
            }
        }
        
        suggestions = predictor.get_suggestions(dummy_summary)
        risk = predictor.predict_risk_level(dummy_summary)
        
        print(f"✓ Predictor working")
        print(f"  Risk level: {risk['risk_category']}")
        print(f"  Suggestions generated: {len(suggestions)} characters")
        
        return True
    except Exception as e:
        print(f"✗ Predictor failed: {e}")
        return False

def test_notifier():
    """Test notifier"""
    print("\nTesting notifier...")
    try:
        from config import Config
        from notifier import NotificationManager
        
        config = Config.from_env()
        # Force console-only for testing
        config.notification.enable_email = False
        config.notification.enable_desktop = False
        config.notification.enable_console = True
        
        notifier = NotificationManager(config)
        
        print("✓ Notifier initialized")
        print(f"  Email: {'enabled' if config.notification.enable_email else 'disabled'}")
        print(f"  Desktop: {'enabled' if config.notification.enable_desktop else 'disabled'}")
        
        return True
    except Exception as e:
        print(f"✗ Notifier failed: {e}")
        return False

def test_camera():
    """Test camera access"""
    print("\nTesting camera access...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("✗ Cannot open camera")
            print("  Make sure:")
            print("  1. Camera is connected")
            print("  2. No other app is using it")
            print("  3. Camera permissions are enabled")
            return False
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            print(f"✓ Camera working - frame size: {frame.shape}")
            return True
        else:
            print("✗ Camera opened but cannot read frame")
            return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print("\nChecking dependencies...")
    required = ['cv2', 'numpy', 'requests', 'apscheduler']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️ Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_api_keys():
    """Check if API keys are configured"""
    print("\nChecking API configuration...")
    import os
    
    groq_key = os.getenv("GROQ_API_KEY")
    resend_key = os.getenv("RESEND_API_KEY")
    email = os.getenv("NOTIFICATION_EMAIL")
    
    if groq_key:
        print(f"✓ Groq API key: {groq_key[:10]}...")
    else:
        print("ℹ️ Groq API key: Not set (will use fallback suggestions)")
    
    if resend_key and email:
        print(f"✓ Email configured: {email}")
    else:
        print("ℹ️ Email: Not configured (will use console/desktop notifications)")
    
    return True

def main():
    """Run all tests"""
    print("="*60)
    print("ACTIVITY MONITOR - System Test")
    print("="*60)
    
    results = {
        "Dependencies": check_dependencies(),
        "Imports": test_imports(),
        "Configuration": test_config(),
        "API Keys": check_api_keys(),
        "Detector": test_detector(),
        "Logger": test_logger(),
        "Aggregator": test_aggregator(),
        "Predictor": test_predictor(),
        "Notifier": test_notifier(),
        "Camera": test_camera()
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test:20} {status}")
    
    print("="*60)
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! You're ready to use Activity Monitor.")
        print("\nRun: python main.py")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues above.")
    
    print("="*60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

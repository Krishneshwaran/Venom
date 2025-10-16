"""
Activity Monitor - Main Application
Real-time activity tracking with AI-powered insights

This application monitors user activity through webcam, classifies activities,
logs events, and generates weekly reports with AI suggestions.
"""

import cv2
import time
import sys
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler

# Import our modules
from config import Config, ActivityType
from detector import ActivityDetector
from logger import ActivityLogger, SessionTracker
from aggregator import ActivityAggregator
from predictor import GroqPredictor
from notifier import NotificationManager


# ============================================================================
# CAMERA CAPTURE & PROCESSING
# ============================================================================

class ActivityCapture:
    """
    Handles webcam capture and real-time activity detection
    """
    
    def __init__(self, config: Config, logger: ActivityLogger, 
                 detector: ActivityDetector, session_tracker: SessionTracker):
        self.config = config
        self.logger = logger
        self.detector = detector
        self.session_tracker = session_tracker
        
        self.running = False
        self.paused = False
        self.frame_count = 0
        
        self.current_activity = None
        self.activity_start_time = None
        self.last_detection_result = None
        
        print("✓ Activity capture initialized")
    
    def start(self) -> None:
        """Start capturing from webcam"""
        self.running = True
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Cannot open webcam")
            return
        
        print("\n" + "="*60)
        print("🎬 ACTIVITY MONITOR STARTED")
        print("="*60)
        print("Press 'q' to quit")
        print("Press 'p' to pause/resume")
        print("Press 's' to show session summary")
        print("Press 'r' to generate report now")
        print("="*60 + "\n")
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to grab frame")
                    break
                
                if not self.paused:
                    self.frame_count += 1
                    
                    # Run detection every N frames
                    if self.frame_count % self.config.detection.frame_skip == 0:
                        self._process_frame(frame)
                
                # Display frame if enabled
                if self.config.show_camera_feed:
                    display_frame = self._prepare_display_frame(frame)
                    cv2.imshow('Activity Monitor', display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n⏹️  Stopping...")
                    break
                elif key == ord('p'):
                    self.paused = not self.paused
                    print(f"\n{'⏸️  Paused' if self.paused else '▶️  Resumed'}")
                elif key == ord('s'):
                    self._show_session_summary()
                elif key == ord('r'):
                    print("\n📊 Generating report...")
                    # Would trigger report generation
        
        finally:
            self._cleanup(cap)
    
    def _process_frame(self, frame) -> None:
        """Process a single frame"""
        # Run detection
        result = self.detector.detect_activity(frame)
        self.last_detection_result = result
        
        # Check for activity change
        if result.activity != self.current_activity:
            self._handle_activity_change(result)
    
    def _handle_activity_change(self, result) -> None:
        """Handle when activity changes"""
        # End previous activity
        if self.current_activity and self.activity_start_time:
            duration = int(time.time() - self.activity_start_time)
            
            # Only log if duration is meaningful (> 5 seconds)
            if duration >= 5:
                self.logger.log_activity(
                    activity=self.current_activity,
                    confidence=result.confidence,
                    duration=duration,
                    objects=result.objects,
                    head_pose=result.head_pose
                )
                
                # Update session tracker
                self.session_tracker.end_activity()
                
                print(f"📝 Logged: {self.current_activity} ({duration}s)")
        
        # Start new activity
        self.current_activity = result.activity
        self.activity_start_time = time.time()
        self.session_tracker.start_activity(result.activity)
    
    def _prepare_display_frame(self, frame):
        """Prepare frame for display with overlays"""
        if self.last_detection_result:
            frame = self.detector.draw_detection(frame, self.last_detection_result)
        
        # Add pause indicator
        if self.paused:
            cv2.putText(frame, "PAUSED", (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        # Add session info
        session_duration = int(time.time() - self.session_tracker.session_start_time.timestamp())
        session_text = f"Session: {session_duration // 60}m"
        cv2.putText(frame, session_text, (frame.shape[1] - 150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def _show_session_summary(self) -> None:
        """Display current session summary"""
        summary = self.session_tracker.get_session_summary()
        print("\n" + "="*60)
        print("📊 CURRENT SESSION SUMMARY")
        print("="*60)
        print(f"Session Duration: {summary['session_duration_minutes']:.1f} minutes")
        print("\nActivity Breakdown:")
        for activity, minutes in summary['activity_durations'].items():
            print(f"  {activity}: {minutes:.1f} min")
        print(f"\nCurrent Activity: {summary['current_activity']}")
        print("="*60 + "\n")
    
    def _cleanup(self, cap) -> None:
        """Cleanup resources"""
        # End current activity
        if self.current_activity and self.activity_start_time:
            duration = int(time.time() - self.activity_start_time)
            if duration >= 5:
                self.logger.log_activity(
                    activity=self.current_activity,
                    confidence=0.8,
                    duration=duration,
                    objects=[],
                    head_pose=None
                )
        
        cap.release()
        cv2.destroyAllWindows()
        self.running = False
        print("\n✓ Camera released")


# ============================================================================
# SCHEDULER
# ============================================================================

class ReportScheduler:
    """
    Schedules periodic report generation
    """
    
    def __init__(self, config: Config, logger: ActivityLogger,
                 aggregator: ActivityAggregator, predictor: GroqPredictor,
                 notifier: NotificationManager):
        self.config = config
        self.logger = logger
        self.aggregator = aggregator
        self.predictor = predictor
        self.notifier = notifier
        
        self.scheduler = BackgroundScheduler()
        print("✓ Report scheduler initialized")
    
    def start(self) -> None:
        """Start background scheduler"""
        if self.config.scheduler.enable_weekly_report:
            # Schedule weekly report
            self.scheduler.add_job(
                self.generate_weekly_report,
                'cron',
                day_of_week=self.config.scheduler.report_day,
                hour=self.config.scheduler.report_hour,
                minute=self.config.scheduler.report_minute,
                id='weekly_report'
            )
            print(f"✓ Weekly report scheduled: Every {self.config.scheduler.report_day} "
                  f"at {self.config.scheduler.report_hour}:{self.config.scheduler.report_minute:02d}")
        
        self.scheduler.start()
    
    def stop(self) -> None:
        """Stop scheduler"""
        self.scheduler.shutdown()
        print("✓ Scheduler stopped")
    
    def generate_weekly_report(self) -> None:
        """Generate and send weekly report"""
        print("\n" + "="*60)
        print("📈 GENERATING WEEKLY REPORT")
        print("="*60)
        
        # Get weekly summary
        summary = self.aggregator.get_weekly_summary()
        
        # Get trends
        trends = self.aggregator.get_trend_comparison()
        
        # Get insights
        insights = self.aggregator.get_activity_insights()
        
        # Get risk assessment
        risk_assessment = self.predictor.predict_risk_level(summary)
        
        # Get AI suggestions
        suggestions = self.predictor.get_suggestions(summary, trends, insights)
        
        # Send notifications
        results = self.notifier.send_weekly_report(
            summary, suggestions, trends, risk_assessment
        )
        
        print(f"✓ Report generated and sent")
        print(f"  Channels: {', '.join(results['channels'].keys())}")
        print("="*60 + "\n")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class ActivityMonitorApp:
    """
    Main application that coordinates all components
    """
    
    def __init__(self, config: Optional[Config] = None):
        # Load configuration
        self.config = config or Config.from_env()
        
        # Validate configuration
        is_valid, errors = self.config.validate()
        if not is_valid:
            print("⚠️ Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nContinuing with current configuration...")
        
        # Initialize components
        print("\n🚀 Initializing Activity Monitor...")
        print("="*60)
        
        self.logger = ActivityLogger(self.config)
        self.session_tracker = SessionTracker(self.logger)
        self.detector = ActivityDetector(self.config)
        self.aggregator = ActivityAggregator(self.logger, self.config)
        self.predictor = GroqPredictor(self.config)
        self.notifier = NotificationManager(self.config)
        self.scheduler = ReportScheduler(
            self.config, self.logger, self.aggregator, 
            self.predictor, self.notifier
        )
        self.capture = ActivityCapture(
            self.config, self.logger, self.detector, self.session_tracker
        )
        
        print("="*60)
        print("✓ All components initialized")
        print()
    
    def run(self) -> None:
        """Start the application"""
        try:
            # Start scheduler
            self.scheduler.start()
            
            # Start capture (blocking)
            self.capture.start()
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrupted by user")
        
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Clean shutdown of all components"""
        print("\n🛑 Shutting down...")
        
        # Stop scheduler
        self.scheduler.stop()
        
        # Show final session summary
        print("\n" + "="*60)
        print("📊 FINAL SESSION SUMMARY")
        print("="*60)
        summary = self.session_tracker.get_session_summary()
        print(f"Session Duration: {summary['session_duration_minutes']:.1f} minutes")
        print("\nActivity Breakdown:")
        for activity, minutes in summary['activity_durations'].items():
            print(f"  {activity}: {minutes:.1f} min")
        print("="*60)
        
        # Close logger
        self.logger.close()
        
        # Show stats
        stats = self.logger.get_stats()
        print(f"\n📁 Logging Statistics:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Total log files: {stats['total_log_files']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        
        print("\n✓ Shutdown complete")
    
    def generate_report_now(self) -> None:
        """Generate weekly report immediately"""
        self.scheduler.generate_weekly_report()


# ============================================================================
# CLI COMMANDS
# ============================================================================

def show_weekly_report(config: Config) -> None:
    """Show weekly report in console"""
    logger = ActivityLogger(config)
    aggregator = ActivityAggregator(logger, config)
    predictor = GroqPredictor(config)
    notifier = NotificationManager(config)
    
    # Generate report
    summary = aggregator.get_weekly_summary()
    trends = aggregator.get_trend_comparison()
    insights = aggregator.get_activity_insights()
    risk_assessment = predictor.predict_risk_level(summary)
    suggestions = predictor.get_suggestions(summary, trends, insights)
    
    # Send to console
    notifier.send_weekly_report(summary, suggestions, trends, risk_assessment)


def show_daily_report(config: Config, date: Optional[str] = None) -> None:
    """Show daily report"""
    logger = ActivityLogger(config)
    aggregator = ActivityAggregator(logger, config)
    
    if date:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
    else:
        date_obj = datetime.now()
    
    summary = aggregator.get_daily_summary(date_obj)
    
    print("\n" + "="*60)
    print(f"📅 DAILY REPORT - {summary['date']} ({summary['day_of_week']})")
    print("="*60)
    print(f"Total Time: {summary['total_hours']:.1f} hours")
    print(f"Productivity: {summary['productive_percentage']:.1f}%")
    print("\nActivity Breakdown:")
    for activity, hours in summary['time_breakdown_hours'].items():
        print(f"  {activity}: {hours:.1f}h")
    print("="*60 + "\n")


def cleanup_old_logs(config: Config, weeks: int = 12) -> None:
    """Clean up old log files"""
    logger = ActivityLogger(config)
    deleted = logger.cleanup_old_logs(keep_weeks=weeks)
    print(f"✓ Cleaned up {deleted} old log files (kept last {weeks} weeks)")


def test_email(config: Config) -> None:
    """Test email configuration"""
    notifier = NotificationManager(config)
    success = notifier.test_email()
    if success:
        print("✓ Email test successful")
    else:
        print("✗ Email test failed")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Activity Monitor - Track and analyze your daily activities"
    )
    parser.add_argument(
        '--report', '-r',
        action='store_true',
        help='Show weekly report and exit'
    )
    parser.add_argument(
        '--daily', '-d',
        nargs='?',
        const='',
        help='Show daily report (optionally specify date YYYY-MM-DD)'
    )
    parser.add_argument(
        '--cleanup',
        type=int,
        metavar='WEEKS',
        help='Clean up log files older than WEEKS'
    )
    parser.add_argument(
        '--test-email',
        action='store_true',
        help='Test email configuration'
    )
    parser.add_argument(
        '--no-camera',
        action='store_true',
        help='Disable camera feed display'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config.from_env()
    
    if args.no_camera:
        config.show_camera_feed = False
    
    # Handle CLI commands
    if args.report:
        show_weekly_report(config)
        return
    
    if args.daily is not None:
        date_str = args.daily if args.daily else None
        show_daily_report(config, date_str)
        return
    
    if args.cleanup:
        cleanup_old_logs(config, args.cleanup)
        return
    
    if args.test_email:
        test_email(config)
        return
    
    # Normal operation - start monitoring
    app = ActivityMonitorApp(config)
    app.run()


if __name__ == "__main__":
    main()

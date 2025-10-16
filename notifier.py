"""
Notification Module
Handles delivery of weekly reports via email, desktop notifications, and console
"""

import requests
from typing import Dict, Optional
from datetime import datetime
from config import Config, NotificationConfig


class NotificationManager:
    """
    Manages multi-channel notifications for activity reports
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.notification_config = config.notification
        self.api_config = config.api
        
        # Validate configuration
        if self.notification_config.enable_email:
            if not self.api_config.resend_api_key:
                print("⚠️ Email notifications enabled but Resend API key not set. Disabling email.")
                self.notification_config.enable_email = False
            elif not self.notification_config.email_to:
                print("⚠️ Email notifications enabled but recipient email not set. Disabling email.")
                self.notification_config.enable_email = False
        
        print(f"✓ Notification manager initialized")
        print(f"  - Email: {'enabled' if self.notification_config.enable_email else 'disabled'}")
        print(f"  - Desktop: {'enabled' if self.notification_config.enable_desktop else 'disabled'}")
        print(f"  - Console: {'enabled' if self.notification_config.enable_console else 'disabled'}")
    
    def send_weekly_report(self, summary: Dict, suggestions: str, 
                          trends: Optional[Dict] = None,
                          risk_assessment: Optional[Dict] = None) -> Dict:
        """
        Send weekly report through configured channels
        
        Args:
            summary: Weekly summary data
            suggestions: AI-generated suggestions
            trends: Optional trend comparison
            risk_assessment: Optional risk prediction
        
        Returns:
            Dictionary with delivery status for each channel
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "channels": {}
        }
        
        # Console notification
        if self.notification_config.enable_console:
            try:
                self._send_console(summary, suggestions, trends, risk_assessment)
                results["channels"]["console"] = "success"
            except Exception as e:
                results["channels"]["console"] = f"failed: {e}"
        
        # Desktop notification
        if self.notification_config.enable_desktop:
            try:
                self._send_desktop(summary, suggestions)
                results["channels"]["desktop"] = "success"
            except Exception as e:
                results["channels"]["desktop"] = f"failed: {e}"
        
        # Email notification
        if self.notification_config.enable_email:
            try:
                self._send_email(summary, suggestions, trends, risk_assessment)
                results["channels"]["email"] = "success"
            except Exception as e:
                results["channels"]["email"] = f"failed: {e}"
        
        return results
    
    def _send_console(self, summary: Dict, suggestions: str,
                     trends: Optional[Dict], risk_assessment: Optional[Dict]) -> None:
        """Send report to console output"""
        print("\n" + "=" * 80)
        print("📊 WEEKLY ACTIVITY REPORT")
        print("=" * 80)
        
        print(f"\n📅 Week: {summary['week_start']} to {summary['week_end']}")
        print(f"⏱️  Total Active Time: {summary['total_present_hours']:.1f} hours")
        print(f"📈 Productivity: {summary['productive_percentage']:.1f}%")
        
        # Risk assessment
        if risk_assessment:
            emoji = risk_assessment.get('risk_emoji', '')
            category = risk_assessment.get('risk_category', 'UNKNOWN')
            print(f"\n{emoji} Risk Level: {category}")
        
        # Activity breakdown
        print("\n🎯 Activity Breakdown:")
        breakdown = summary.get('time_breakdown_hours', {})
        for activity, hours in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (hours / summary['total_present_hours'] * 100) if summary['total_present_hours'] > 0 else 0
            bar = "█" * int(percentage / 5)  # Simple bar chart
            print(f"  {activity.replace('_', ' ').title():20} {hours:5.1f}h [{bar:20}] {percentage:5.1f}%")
        
        # Trends
        if trends and 'summary' in trends:
            print("\n📊 Trends:")
            for trend in trends['summary']:
                print(f"  {trend}")
        
        # Suggestions
        print("\n💡 AI Suggestions:")
        print("-" * 80)
        print(suggestions)
        print("-" * 80)
        
        print("\n" + "=" * 80 + "\n")
    
    def _send_desktop(self, summary: Dict, suggestions: str) -> None:
        """Send desktop notification"""
        try:
            # Try to use Windows toast notification (Windows 10+)
            import platform
            if platform.system() == 'Windows':
                self._send_windows_notification(summary, suggestions)
            else:
                # Fallback: just print a simple notification
                print("\n🔔 Desktop Notification:")
                print(f"Weekly Report: {summary['productive_percentage']:.1f}% productivity")
                print("Check console for full report")
        except Exception as e:
            print(f"Desktop notification failed: {e}")
    
    def _send_windows_notification(self, summary: Dict, suggestions: str) -> None:
        """Send Windows 10+ toast notification"""
        try:
            from plyer import notification
            
            title = f"Weekly Activity Report - {summary['productive_percentage']:.1f}% Productive"
            message = f"Week: {summary['week_start']}\n"
            message += f"Total: {summary['total_present_hours']:.1f}h\n"
            
            # Extract first suggestion line
            first_suggestion = suggestions.split('\n')[0][:100]
            message += f"Tip: {first_suggestion}"
            
            notification.notify(
                title=title,
                message=message,
                app_name="Activity Monitor",
                timeout=10
            )
        except ImportError:
            # Plyer not available, use simple console notification
            print("\n🔔 Desktop Notification (plyer not installed):")
            print(f"Weekly Report Ready: {summary['productive_percentage']:.1f}% productivity")
    
    def _send_email(self, summary: Dict, suggestions: str,
                   trends: Optional[Dict], risk_assessment: Optional[Dict]) -> None:
        """Send email via Resend API"""
        url = self.api_config.resend_endpoint
        headers = {
            "Authorization": f"Bearer {self.api_config.resend_api_key}",
            "Content-Type": "application/json"
        }
        
        # Build email content
        subject = self._build_email_subject(summary, risk_assessment)
        html_body = self._build_email_html(summary, suggestions, trends, risk_assessment)
        
        payload = {
            "from": self.notification_config.email_from,
            "to": [self.notification_config.email_to],
            "subject": subject,
            "html": html_body
        }
        
        response = requests.post(
            url, 
            json=payload, 
            headers=headers,
            timeout=self.api_config.resend_timeout
        )
        
        if response.status_code in [200, 201]:
            print(f"✓ Email sent to {self.notification_config.email_to}")
        else:
            error_msg = f"Email send failed: HTTP {response.status_code}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)
    
    def _build_email_subject(self, summary: Dict, risk_assessment: Optional[Dict]) -> str:
        """Build email subject line"""
        week_start = summary['week_start']
        productivity = summary['productive_percentage']
        
        if risk_assessment:
            emoji = risk_assessment.get('risk_emoji', '📊')
            return f"{emoji} Weekly Report: {productivity:.0f}% Productive - Week of {week_start}"
        else:
            return f"📊 Weekly Activity Report - {productivity:.0f}% Productive - Week of {week_start}"
    
    def _build_email_html(self, summary: Dict, suggestions: str,
                         trends: Optional[Dict], risk_assessment: Optional[Dict]) -> str:
        """Build HTML email body"""
        breakdown = summary.get('time_breakdown_hours', {})
        total_hours = summary['total_present_hours']
        
        # Start HTML
        html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
        .metric { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #667eea; }
        .metric-label { font-size: 14px; color: #666; margin-bottom: 5px; }
        .metric-value { font-size: 28px; font-weight: bold; color: #667eea; }
        .activity-bar { background: #e9ecef; height: 30px; border-radius: 15px; margin: 10px 0; overflow: hidden; position: relative; }
        .activity-fill { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); height: 100%; display: flex; align-items: center; padding-left: 10px; color: white; font-weight: bold; font-size: 12px; }
        .activity-row { margin: 15px 0; }
        .activity-label { font-weight: 600; margin-bottom: 5px; display: flex; justify-content: space-between; }
        .suggestions { background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .risk-box { padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; font-size: 18px; font-weight: bold; }
        .risk-low { background: #d4edda; color: #155724; border: 2px solid #c3e6cb; }
        .risk-medium { background: #fff3cd; color: #856404; border: 2px solid #ffeeba; }
        .risk-high { background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
        .trend { background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #007bff; }
        .footer { text-align: center; color: #666; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }
    </style>
</head>
<body>
"""
        
        # Header
        html += f"""
    <div class="header">
        <h1 style="margin: 0; font-size: 32px;">📊 Weekly Activity Report</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">{summary['week_start']} to {summary['week_end']}</p>
    </div>
"""
        
        # Risk Assessment
        if risk_assessment:
            risk_category = risk_assessment.get('risk_category', 'UNKNOWN')
            risk_class = f"risk-{risk_category.lower()}"
            emoji = risk_assessment.get('risk_emoji', '')
            interpretation = risk_assessment.get('interpretation', '')
            
            html += f"""
    <div class="risk-box {risk_class}">
        {emoji} Risk Level: {risk_category}
        <div style="font-size: 14px; font-weight: normal; margin-top: 10px;">{interpretation}</div>
    </div>
"""
        
        # Key Metrics
        html += f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0;">
        <div class="metric">
            <div class="metric-label">Total Active Time</div>
            <div class="metric-value">{total_hours:.1f}h</div>
        </div>
        <div class="metric">
            <div class="metric-label">Productivity</div>
            <div class="metric-value">{summary['productive_percentage']:.1f}%</div>
        </div>
    </div>
"""
        
        # Activity Breakdown
        html += """
    <h2 style="color: #667eea; margin-top: 30px;">🎯 Activity Breakdown</h2>
"""
        
        for activity, hours in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (hours / total_hours * 100) if total_hours > 0 else 0
            activity_name = activity.replace('_', ' ').title()
            
            html += f"""
    <div class="activity-row">
        <div class="activity-label">
            <span>{activity_name}</span>
            <span>{hours:.1f}h ({percentage:.1f}%)</span>
        </div>
        <div class="activity-bar">
            <div class="activity-fill" style="width: {min(percentage, 100)}%;">
                {activity_name if percentage > 20 else ''}
            </div>
        </div>
    </div>
"""
        
        # Trends
        if trends and 'summary' in trends:
            html += """
    <h2 style="color: #667eea; margin-top: 30px;">📊 Trends</h2>
"""
            for trend in trends['summary']:
                html += f"""
    <div class="trend">{trend}</div>
"""
        
        # Suggestions
        html += f"""
    <h2 style="color: #667eea; margin-top: 30px;">💡 AI-Powered Suggestions</h2>
    <div class="suggestions">
        {self._format_suggestions_html(suggestions)}
    </div>
"""
        
        # Footer
        html += f"""
    <div class="footer">
        <p>Generated by Activity Monitor on {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        <p>This is an automated report based on your weekly activity data.</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def _format_suggestions_html(self, suggestions: str) -> str:
        """Format suggestions text as HTML"""
        # Convert line breaks and format lists
        html = suggestions.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        # Bold headings (lines ending with :)
        lines = html.split('<br>')
        formatted_lines = []
        for line in lines:
            if line.strip().endswith(':'):
                formatted_lines.append(f'<strong>{line}</strong>')
            else:
                formatted_lines.append(line)
        
        return '<p>' + '<br>'.join(formatted_lines) + '</p>'
    
    def send_instant_notification(self, title: str, message: str) -> None:
        """
        Send instant notification (not weekly report)
        Used for alerts or immediate feedback
        """
        if self.notification_config.enable_desktop:
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Activity Monitor",
                    timeout=10
                )
            except ImportError:
                print(f"\n🔔 {title}\n{message}\n")
        
        if self.notification_config.enable_console:
            print(f"\n🔔 {title}")
            print(f"{message}\n")
    
    def test_email(self) -> bool:
        """Test email configuration by sending a test email"""
        if not self.notification_config.enable_email:
            print("Email notifications are not enabled")
            return False
        
        try:
            test_summary = {
                "week_start": "2025-01-01",
                "week_end": "2025-01-07",
                "total_present_hours": 42.5,
                "productive_percentage": 65.0,
                "time_breakdown_hours": {
                    "working": 27.6,
                    "watching_reels": 8.4,
                    "idle": 6.5
                }
            }
            
            test_suggestions = "This is a test email from Activity Monitor.\n\nIf you receive this, your email configuration is working correctly!"
            
            self._send_email(test_summary, test_suggestions, None, None)
            return True
        except Exception as e:
            print(f"Email test failed: {e}")
            return False

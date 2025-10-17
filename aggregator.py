"""
Activity Aggregation Module
Analyzes logs to compute summaries, trends, and statistics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from pathlib import Path
from config import Config, PRODUCTIVE_ACTIVITIES, UNPRODUCTIVE_ACTIVITIES
from logger import ActivityLogger
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile
import os
try:
    # Optional: matplotlib for simple charts embedded into PDF
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except Exception:
    plt = None


class ActivityAggregator:
    """
    Aggregates activity events into meaningful summaries and trends
    """
    
    def __init__(self, logger: ActivityLogger, config: Config):
        self.logger = logger
        self.config = config
    
    def get_weekly_summary(self, week_offset: int = 0) -> Dict:
        """
        Get summary for a specific week
        
        Args:
            week_offset: 0 for current week, -1 for last week, etc.
        
        Returns:
            Dictionary with weekly statistics
        """
        # Calculate week boundaries
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Get the log file for this week
        year, week_num, _ = start_of_week.isocalendar()
        log_file = self.logger.get_log_file_for_week(year, week_num)
        
        if not log_file:
            return self._empty_summary(start_of_week, end_of_week)
        
        # Read events for this week
        events = self.logger.read_events(
            file_path=log_file,
            start_time=start_of_week,
            end_time=end_of_week
        )
        
        if not events:
            return self._empty_summary(start_of_week, end_of_week)
        
        # Aggregate statistics
        return self._aggregate_events(events, start_of_week, end_of_week)
    
    def _aggregate_events(self, events: List[Dict], 
                         start_date: datetime, 
                         end_date: datetime) -> Dict:
        """Aggregate events into summary statistics"""
        # Activity duration totals
        activity_durations = defaultdict(int)
        total_duration = 0
        
        # Daily breakdown
        daily_activities = defaultdict(lambda: defaultdict(int))
        
        # Confidence scores
        activity_confidences = defaultdict(list)
        
        for event in events:
            activity = event.get('activity', 'unknown')
            duration = event.get('duration_seconds', 0)
            confidence = event.get('confidence', 0)
            
            # Add to totals
            activity_durations[activity] += duration
            total_duration += duration
            
            # Track confidence
            activity_confidences[activity].append(confidence)
            
            # Daily breakdown
            try:
                event_date = datetime.fromisoformat(event['timestamp']).date()
                daily_activities[str(event_date)][activity] += duration
            except (KeyError, ValueError):
                pass
        
        # Convert to hours
        activity_hours = {k: v / 3600 for k, v in activity_durations.items()}
        total_hours = total_duration / 3600
        
        # Calculate productivity metrics
        productive_hours = sum(
            activity_hours.get(activity, 0) 
            for activity in PRODUCTIVE_ACTIVITIES
        )
        unproductive_hours = sum(
            activity_hours.get(activity, 0)
            for activity in UNPRODUCTIVE_ACTIVITIES
        )
        
        productive_percentage = (productive_hours / total_hours * 100) if total_hours > 0 else 0
        
        # Average confidences
        avg_confidences = {
            activity: sum(scores) / len(scores)
            for activity, scores in activity_confidences.items()
            if scores
        }
        
        # Daily breakdown in hours
        daily_breakdown = {
            date: {activity: duration / 3600 for activity, duration in activities.items()}
            for date, activities in daily_activities.items()
        }
        
        return {
            "week_start": start_date.strftime("%Y-%m-%d"),
            "week_end": end_date.strftime("%Y-%m-%d"),
            "year": start_date.year,
            "week_number": start_date.isocalendar()[1],
            "total_present_hours": round(total_hours, 2),
            "time_breakdown_hours": {k: round(v, 2) for k, v in activity_hours.items()},
            "productive_hours": round(productive_hours, 2),
            "unproductive_hours": round(unproductive_hours, 2),
            "productive_percentage": round(productive_percentage, 1),
            "average_confidences": {k: round(v, 2) for k, v in avg_confidences.items()},
            "daily_breakdown": daily_breakdown,
            "total_events": len(events),
            "generated_at": datetime.now().isoformat()
        }
    
    def _empty_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        """Return empty summary for weeks with no data"""
        return {
            "week_start": start_date.strftime("%Y-%m-%d"),
            "week_end": end_date.strftime("%Y-%m-%d"),
            "year": start_date.year,
            "week_number": start_date.isocalendar()[1],
            "total_present_hours": 0,
            "time_breakdown_hours": {},
            "productive_hours": 0,
            "unproductive_hours": 0,
            "productive_percentage": 0,
            "average_confidences": {},
            "daily_breakdown": {},
            "total_events": 0,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_trend_comparison(self) -> Dict:
        """
        Compare current week with previous week to identify trends
        
        Returns:
            Dictionary with trend analysis
        """
        current_week = self.get_weekly_summary(0)
        previous_week = self.get_weekly_summary(-1)
        
        # Calculate changes
        trends = {}
        
        # Total time trend
        current_total = current_week['total_present_hours']
        previous_total = previous_week['total_present_hours']
        trends['total_time_change'] = self._calculate_percentage_change(
            previous_total, current_total
        )
        
        # Productivity trend
        current_prod = current_week['productive_percentage']
        previous_prod = previous_week['productive_percentage']
        trends['productivity_change'] = round(current_prod - previous_prod, 1)
        
        # Activity-specific trends
        activity_trends = {}
        current_activities = current_week['time_breakdown_hours']
        previous_activities = previous_week['time_breakdown_hours']
        
        all_activities = set(current_activities.keys()) | set(previous_activities.keys())
        
        for activity in all_activities:
            current_hours = current_activities.get(activity, 0)
            previous_hours = previous_activities.get(activity, 0)
            
            change_pct = self._calculate_percentage_change(previous_hours, current_hours)
            change_hours = current_hours - previous_hours
            
            activity_trends[activity] = {
                "change_percentage": change_pct,
                "change_hours": round(change_hours, 2),
                "current_hours": current_hours,
                "previous_hours": previous_hours
            }
        
        return {
            "current_week": f"{current_week['week_start']} to {current_week['week_end']}",
            "previous_week": f"{previous_week['week_start']} to {previous_week['week_end']}",
            "overall_trends": trends,
            "activity_trends": activity_trends,
            "summary": self._generate_trend_summary(trends, activity_trends),
            "generated_at": datetime.now().isoformat()
        }
    
    def _calculate_percentage_change(self, old_value: float, new_value: float) -> str:
        """Calculate percentage change and format as string"""
        if old_value == 0:
            if new_value == 0:
                return "0%"
            else:
                return "+100%"
        
        change = ((new_value - old_value) / old_value) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{round(change, 1)}%"
    
    def _generate_trend_summary(self, overall_trends: Dict, 
                               activity_trends: Dict) -> List[str]:
        """Generate human-readable trend summary"""
        summaries = []
        
        # Overall time change
        time_change = overall_trends.get('total_time_change', '0%')
        if '+' in time_change:
            summaries.append(f"📈 Overall active time increased by {time_change}")
        elif '-' in time_change and time_change != '0%':
            summaries.append(f"📉 Overall active time decreased by {time_change}")
        
        # Productivity change
        prod_change = overall_trends.get('productivity_change', 0)
        if prod_change > 5:
            summaries.append(f"✅ Productivity improved by {prod_change}%")
        elif prod_change < -5:
            summaries.append(f"⚠️ Productivity dropped by {abs(prod_change)}%")
        
        # Significant activity changes
        significant_changes = [
            (activity, data['change_percentage'], data['change_hours'])
            for activity, data in activity_trends.items()
            if abs(data.get('change_hours', 0)) > 1  # More than 1 hour change
        ]
        
        for activity, change_pct, change_hours in sorted(
            significant_changes, 
            key=lambda x: abs(x[2]), 
            reverse=True
        )[:3]:  # Top 3 changes
            direction = "increased" if change_hours > 0 else "decreased"
            summaries.append(
                f"• {activity.replace('_', ' ').title()}: {direction} by "
                f"{abs(change_hours):.1f}h ({change_pct})"
            )
        
        return summaries
    
    def get_multi_week_summary(self, num_weeks: int = 4) -> Dict:
        """
        Get aggregated summary across multiple weeks
        
        Args:
            num_weeks: Number of recent weeks to include
        
        Returns:
            Multi-week summary with averages and totals
        """
        weekly_summaries = []
        
        for week_offset in range(-(num_weeks - 1), 1):
            summary = self.get_weekly_summary(week_offset)
            if summary['total_events'] > 0:
                weekly_summaries.append(summary)
        
        if not weekly_summaries:
            return {
                "period": f"Last {num_weeks} weeks",
                "weeks_with_data": 0,
                "message": "No data available"
            }
        
        # Calculate averages and totals
        total_hours = sum(w['total_present_hours'] for w in weekly_summaries)
        avg_hours_per_week = total_hours / len(weekly_summaries)
        
        avg_productivity = sum(w['productive_percentage'] for w in weekly_summaries) / len(weekly_summaries)
        
        # Aggregate activity hours
        all_activities = defaultdict(float)
        for week in weekly_summaries:
            for activity, hours in week['time_breakdown_hours'].items():
                all_activities[activity] += hours
        
        return {
            "period": f"Last {num_weeks} weeks",
            "weeks_with_data": len(weekly_summaries),
            "first_week": weekly_summaries[0]['week_start'],
            "last_week": weekly_summaries[-1]['week_end'],
            "total_hours": round(total_hours, 2),
            "average_hours_per_week": round(avg_hours_per_week, 2),
            "average_productivity_percentage": round(avg_productivity, 1),
            "activity_totals_hours": {k: round(v, 2) for k, v in all_activities.items()},
            "weekly_data": weekly_summaries,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict:
        """
        Get summary for a specific day
        
        Args:
            date: Date to summarize (default: today)
        
        Returns:
            Daily summary
        """
        if date is None:
            date = datetime.now()
        
        # Get week file for this date
        year, week_num, _ = date.isocalendar()
        log_file = self.logger.get_log_file_for_week(year, week_num)
        
        if not log_file:
            return self._empty_daily_summary(date)
        
        # Read events for this day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        events = self.logger.read_events(
            file_path=log_file,
            start_time=start_of_day,
            end_time=end_of_day
        )
        
        if not events:
            return self._empty_daily_summary(date)
        
        # Aggregate
        activity_durations = defaultdict(int)
        total_duration = 0
        
        for event in events:
            activity = event.get('activity', 'unknown')
            duration = event.get('duration_seconds', 0)
            activity_durations[activity] += duration
            total_duration += duration
        
        activity_hours = {k: v / 3600 for k, v in activity_durations.items()}
        total_hours = total_duration / 3600
        
        productive_hours = sum(
            activity_hours.get(activity, 0)
            for activity in PRODUCTIVE_ACTIVITIES
        )
        
        productive_percentage = (productive_hours / total_hours * 100) if total_hours > 0 else 0
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "day_of_week": date.strftime("%A"),
            "total_hours": round(total_hours, 2),
            "time_breakdown_hours": {k: round(v, 2) for k, v in activity_hours.items()},
            "productive_hours": round(productive_hours, 2),
            "productive_percentage": round(productive_percentage, 1),
            "total_events": len(events),
            "generated_at": datetime.now().isoformat()
        }
    
    def _empty_daily_summary(self, date: datetime) -> Dict:
        """Return empty daily summary"""
        return {
            "date": date.strftime("%Y-%m-%d"),
            "day_of_week": date.strftime("%A"),
            "total_hours": 0,
            "time_breakdown_hours": {},
            "productive_hours": 0,
            "productive_percentage": 0,
            "total_events": 0,
            "generated_at": datetime.now().isoformat()
        }
    
    def get_activity_insights(self) -> Dict:
        """
        Generate insights about activity patterns
        
        Returns:
            Dictionary with pattern insights
        """
        current_week = self.get_weekly_summary(0)
        
        insights = []
        warnings = []
        recommendations = []
        
        total_hours = current_week['total_present_hours']
        breakdown = current_week['time_breakdown_hours']
        productivity = current_week['productive_percentage']
        
        # Check for concerning patterns
        phone_hours = breakdown.get('watching_reels', 0)
        if phone_hours > 20:
            warnings.append(
                f"⚠️ High phone usage: {phone_hours:.1f} hours this week "
                f"({phone_hours/total_hours*100:.1f}% of your time)"
            )
            recommendations.append("Try using app blockers during work hours")
        
        tv_hours = breakdown.get('watching_tv', 0)
        if tv_hours > 15:
            warnings.append(f"📺 Heavy TV watching: {tv_hours:.1f} hours this week")
            recommendations.append("Consider replacing some TV time with reading or exercise")
        
        work_hours = breakdown.get('working', 0)
        if work_hours < 10 and total_hours > 20:
            warnings.append(f"💼 Low work time: Only {work_hours:.1f} hours")
            recommendations.append("Try time-blocking dedicated work periods")
        
        # Positive patterns
        if productivity > 60:
            insights.append(f"✅ Great productivity: {productivity:.1f}%")
        
        if work_hours > 25:
            insights.append(f"💪 Strong work ethic: {work_hours:.1f} hours of productive time")
        
        # Balance insights
        work_life_ratio = work_hours / (phone_hours + tv_hours) if (phone_hours + tv_hours) > 0 else 0
        if work_life_ratio > 2:
            insights.append("⚖️ Good work-life balance")
        elif work_life_ratio < 0.5:
            warnings.append("⚖️ Consider improving work-life balance")
        
        return {
            "insights": insights,
            "warnings": warnings,
            "recommendations": recommendations,
            "metrics": {
                "total_hours": total_hours,
                "productivity_percentage": productivity,
                "work_hours": work_hours,
                "leisure_hours": phone_hours + tv_hours
            },
            "generated_at": datetime.now().isoformat()
        }

    def save_weekly_report(self, week_offset: int = 0, extras: Optional[Dict] = None) -> Optional[Path]:
        """Generate and save the weekly report JSON to logs/reports/YYYY-WNN-report.json

        extras: optional dict of additional fields to include (e.g., suggestions, risk_assessment)
        Returns the path to the saved report or None on failure.
        """
        try:
            summary = self.get_weekly_summary(week_offset)
            trends = self.get_trend_comparison()
            insights = self.get_activity_insights()

            report = {
                "summary": summary,
                "trends": trends,
                "insights": insights,
                "generated_at": datetime.now().isoformat()
            }

            if extras:
                report.update(extras)

            # Ensure reports directory exists under logs
            reports_dir = Path(self.logger.logs_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Determine filename from summary
            year = summary.get('year', datetime.now().year)
            week_num = summary.get('week_number', datetime.now().isocalendar()[1])
            filename = f"{year}-W{int(week_num):02d}-report.json"
            file_path = reports_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

            return file_path
        except Exception as e:
            print(f"Failed to save weekly report: {e}")
            return None

    def save_daily_report(self, date: Optional[datetime] = None, extras: Optional[Dict] = None) -> Optional[Path]:
        """Generate and save a daily report JSON file to logs/reports/YYYY-MM-DD-daily.json"""
        try:
            summary = self.get_daily_summary(date)

            report = {
                "daily_summary": summary,
                "generated_at": datetime.now().isoformat()
            }

            if extras:
                report.update(extras)

            reports_dir = Path(self.logger.logs_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{summary['date']}-daily-report.json"
            file_path = reports_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

            return file_path
        except Exception as e:
            print(f"Failed to save daily report: {e}")
            return None

    def save_weekly_report_pdf(self, week_offset: int = 0, output_path: Optional[Path] = None, extras: Optional[Dict] = None) -> Optional[Path]:
        """Generate a human-friendly PDF report for the requested week.

        Returns the path to the saved PDF or None on failure.
        """
        try:
            summary = self.get_weekly_summary(week_offset)
            trends = self.get_trend_comparison()
            insights = self.get_activity_insights()

            report = {
                "summary": summary,
                "trends": trends,
                "insights": insights,
                "generated_at": datetime.now().isoformat()
            }

            if extras:
                report.update(extras)

            # Prepare output path
            reports_dir = Path(self.logger.logs_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            year = summary.get('year', datetime.now().year)
            week_num = summary.get('week_number', datetime.now().isocalendar()[1])
            pdf_name = f"{year}-W{int(week_num):02d}-report.pdf"
            file_path = Path(output_path) if output_path else (reports_dir / pdf_name)

            # Build PDF using ReportLab
            doc = SimpleDocTemplate(str(file_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()
            story = []

            title = f"Activity Monitor — Weekly Report: {summary['week_start']} to {summary['week_end']}"

            # Apply theme color if provided
            theme_color = None
            try:
                if getattr(self.config, 'report_theme_color', None):
                    theme_color = colors.HexColor(self.config.report_theme_color)
                    styles['Heading2'].textColor = theme_color
                    styles['Heading3'].textColor = theme_color
            except Exception:
                theme_color = None

            # Register custom font if provided via config (TTF path)
            custom_font = getattr(self.config, 'report_font', None)
            registered_font_name = None
            if custom_font:
                try:
                    font_path = os.path.expanduser(str(custom_font))
                    if os.path.exists(font_path) and font_path.lower().endswith('.ttf'):
                        # Use filename (without extension) as the font name
                        fname = os.path.splitext(os.path.basename(font_path))[0]
                        pdfmetrics.registerFont(TTFont(fname, font_path))
                        registered_font_name = fname
                        # Apply to title style if possible
                        styles['Title'].fontName = registered_font_name
                        styles['Heading2'].fontName = registered_font_name
                        styles['Heading3'].fontName = registered_font_name
                except Exception:
                    # Non-fatal — keep defaults
                    registered_font_name = None

            # If a logo path is configured and exists, place it in a small header next to the title
            logo_path = getattr(self.config, 'report_logo_path', None)
            if logo_path:
                try:
                    logo_file = Path(logo_path)
                    if logo_file.exists():
                        logo_img = Image(str(logo_file), width=0.9 * inch, height=0.9 * inch)
                        title_para = Paragraph(title, styles['Title'])
                        header_table = Table([[logo_img, title_para]], colWidths=[0.9 * inch, None])
                        header_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
                        story.append(header_table)
                    else:
                        story.append(Paragraph(title, styles['Title']))
                except Exception:
                    story.append(Paragraph(title, styles['Title']))
            else:
                story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 12))

            meta = f"Generated: {report['generated_at']}"
            story.append(Paragraph(meta, styles['Normal']))
            story.append(Spacer(1, 12))

            # Summary table
            story.append(Paragraph("Summary", styles['Heading2']))
            summary_data = [
                ["Total Present Hours", summary.get('total_present_hours', 0)],
                ["Productive Hours", summary.get('productive_hours', 0)],
                ["Unproductive Hours", summary.get('unproductive_hours', 0)],
                ["Productive Percentage", f"{summary.get('productive_percentage', 0)}%"],
                ["Total Events", summary.get('total_events', 0)]
            ]
            table = Table(summary_data, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

            # Time breakdown table
            story.append(Paragraph("Time Breakdown (hours)", styles['Heading2']))
            breakdown = summary.get('time_breakdown_hours', {})
            breakdown_rows = [["Activity", "Hours"]] + [[k, v] for k, v in breakdown.items()]
            table = Table(breakdown_rows, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

            # Daily breakdown section
            story.append(Paragraph("Daily Breakdown", styles['Heading2']))
            daily = summary.get('daily_breakdown', {})
            for date_str, activities in daily.items():
                story.append(Paragraph(f"{date_str}", styles['Heading3']))
                rows = [["Activity", "Hours"]] + [[a, hours] for a, hours in activities.items()]
                t = Table(rows, hAlign='LEFT')
                t.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))

            # Insights
            story.append(Paragraph("Insights & Recommendations", styles['Heading2']))
            insights_text = insights.get('insights', [])
            warnings = insights.get('warnings', [])
            recs = insights.get('recommendations', [])

            if insights_text:
                for it in insights_text:
                    story.append(Paragraph(it, styles['Normal']))
            if warnings:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Warnings:", styles['Heading3']))
                for w in warnings:
                    story.append(Paragraph(w, styles['Normal']))
            if recs:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Recommendations:", styles['Heading3']))
                for r in recs:
                    story.append(Paragraph(r, styles['Normal']))

            # Snapshots section: embed up to 6 images from the snapshots weekly folder
            try:
                snapshots_dir = Path(self.logger.logs_dir) / "snapshots" / f"{year}-W{int(week_num):02d}"
                if snapshots_dir.exists() and snapshots_dir.is_dir():
                    images = sorted(
                        [p for p in snapshots_dir.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png')],
                        key=lambda p: p.stat().st_mtime,
                        reverse=True
                    )

                    max_images = 6
                    selected = images[:max_images]
                    if selected:
                        story.append(PageBreak())
                        story.append(Paragraph('Snapshots', styles['Heading2']))
                        story.append(Spacer(1, 6))

                        # Arrange images into a simple grid (3 columns)
                        cols = 3
                        rows = []
                        row = []
                        for idx, img_path in enumerate(selected):
                            try:
                                im = Image(str(img_path), width=2.0 * inch, height=1.5 * inch)
                                row.append(im)
                                if len(row) == cols:
                                    rows.append(row)
                                    row = []
                            except Exception:
                                # skip images that fail to load
                                continue

                        if row:
                            # fill remaining columns with empty cells
                            while len(row) < cols:
                                row.append(Paragraph('', styles['Normal']))
                            rows.append(row)

                        # Add the image grid
                        for r in rows:
                            t = Table([r], hAlign='LEFT')
                            t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.25, colors.white)]))
                            story.append(t)
                            story.append(Spacer(1, 6))
            except Exception:
                # don't fail the whole report if embedding snapshots fails
                pass

            # Per-person timelines: collect per-person events from the week's log and render small timelines
            try:
                # Read events for the week
                log_file = self.logger.get_log_file_for_week(year, int(week_num))
                if log_file and log_file.exists():
                    events = self.logger.read_events(file_path=log_file)
                    # Extract per-person activities
                    person_timelines = {}  # key -> list of (timestamp, activity, confidence, snapshot)
                    for ev in events:
                        timestamp = ev.get('timestamp')
                        per_person = None
                        # support both nested detection_details and top-level per_person
                        if ev.get('per_person'):
                            per_person = ev.get('per_person')
                        else:
                            det = ev.get('detection_details', {})
                            per_person = det.get('per_person_activities')

                        if not per_person:
                            continue

                        for idx, p in enumerate(per_person):
                            # Prefer persistent person_id if available
                            pid = p.get('person_id') or p.get('id') or None
                            if pid is not None:
                                key = f"Person {pid}"
                            else:
                                # fallback to positional index grouping
                                key = f"Person {idx + 1}"

                            entry = (timestamp, p.get('activity', 'unknown'), p.get('confidence', 0.0), p.get('snapshot'))
                            person_timelines.setdefault(key, []).append(entry)

                    if person_timelines:
                        story.append(PageBreak())
                        story.append(Paragraph('Per-Person Timelines', styles['Heading2']))
                        story.append(Spacer(1, 12))

                        # For each person, render up to 6 timeline entries with small thumbnail and caption
                        for person_key, entries in person_timelines.items():
                            story.append(Paragraph(person_key, styles['Heading3']))
                            story.append(Spacer(1, 6))
                            
                            # Sort entries by timestamp desc and take latest 6
                            # But prioritize entries that have snapshots
                            entries_with_snapshots = [e for e in entries if e[3] and e[3].strip()]
                            entries_without_snapshots = [e for e in entries if not (e[3] and e[3].strip())]
                            
                            # Take up to 6 entries, prioritizing those with snapshots
                            entries_sorted = sorted(entries_with_snapshots, key=lambda x: x[0] if x[0] else '', reverse=True)[:6]
                            
                            # If we have fewer than 6 with snapshots, fill with recent ones without snapshots
                            if len(entries_sorted) < 6:
                                remaining_slots = 6 - len(entries_sorted)
                                entries_without_sorted = sorted(entries_without_snapshots, key=lambda x: x[0] if x[0] else '', reverse=True)[:remaining_slots]
                                entries_sorted.extend(entries_without_sorted)
                            
                            # Create 3-column grid of snapshots
                            table_data = []
                            row = []
                            
                            for i, (ts, act, conf, snap) in enumerate(entries_sorted):
                                # Create cell content
                                cell_content = []
                                
                                # Add image if snapshot exists
                                if snap and snap.strip():
                                    try:
                                        # Fix path resolution - don't double up logs directory
                                        if os.path.isabs(snap):
                                            snap_path = Path(snap)
                                        elif snap.startswith('logs'):
                                            # Path already includes logs directory
                                            snap_path = Path(snap)
                                        else:
                                            # Path needs logs directory prepended
                                            snap_path = Path(self.logger.logs_dir) / snap
                                        
                                        if snap_path.exists():
                                            img = Image(str(snap_path), width=1.6 * inch, height=1.2 * inch)
                                            cell_content.append(img)
                                        else:
                                            # Placeholder for missing image
                                            cell_content.append(Paragraph('[Image not found]', styles['Normal']))
                                    except Exception as e:
                                        cell_content.append(Paragraph('[Image error]', styles['Normal']))
                                else:
                                    # Placeholder for no snapshot
                                    cell_content.append(Paragraph('[No snapshot]', styles['Normal']))
                                
                                # Format timestamp (show only time part)
                                try:
                                    if ts:
                                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                        time_str = dt.strftime('%H:%M:%S')
                                    else:
                                        time_str = 'Unknown time'
                                except Exception:
                                    time_str = 'Invalid time'
                                
                                # Create caption with time and activity
                                caption_text = f"<b>{time_str}</b><br/>{act} ({conf:.2f})"
                                caption = Paragraph(caption_text, styles['Normal'])
                                cell_content.append(caption)
                                
                                # Create a mini table for this cell (image above caption)
                                mini_table = Table(
                                    [[cell_content[0]], [cell_content[1]]], 
                                    colWidths=[1.6 * inch],
                                    rowHeights=[1.2 * inch, 0.6 * inch]
                                )
                                mini_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                                    ('VALIGN', (0, 1), (0, 1), 'TOP'),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                                ]))
                                
                                row.append(mini_table)
                                
                                # If we have 3 columns, add to table_data and start new row
                                if len(row) == 3:
                                    table_data.append(row)
                                    row = []
                            
                            # Add remaining items in the last row (pad with empty cells)
                            if row:
                                while len(row) < 3:
                                    row.append(Paragraph('', styles['Normal']))
                                table_data.append(row)
                            
                            # Create and add the main table
                            if table_data:
                                main_table = Table(table_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch])
                                main_table.setStyle(TableStyle([
                                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                                ]))
                                story.append(main_table)
                                story.append(Spacer(1, 12))
            except Exception as e:
                # Non-fatal
                pass
            except Exception:
                # Non-fatal
                pass

            doc.build(story)

            return file_path
        except Exception as e:
            print(f"Failed to save weekly PDF report: {e}")
            return None

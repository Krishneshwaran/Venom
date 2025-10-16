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

"""
Debug Report - Check if latest data is in the aggregator
"""

import json
from datetime import datetime
from pathlib import Path

def debug_data():
    """Check what data is actually being read"""
    
    log_file = Path("logs/2025-W42.ndjson")
    
    if not log_file.exists():
        print("❌ Log file not found")
        return
    
    print("🔍 DEBUGGING ACTIVITY DATA")
    print("="*50)
    
    # Read all events
    events = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                events.append(data)
            except:
                continue
    
    print(f"📝 Total events found: {len(events)}")
    
    # Show last 5 events
    print(f"\n📋 LAST 5 EVENTS:")
    for event in events[-5:]:
        timestamp = event.get('timestamp', 'N/A')
        activity = event.get('activity', 'N/A')
        duration = event.get('duration_seconds', 0)
        session = event.get('session_id', 'N/A')
        
        print(f"  • {timestamp} | {activity} ({duration}s) | {session}")
    
    # Activity summary
    activity_counts = {}
    total_duration = 0
    
    for event in events:
        activity = event.get('activity', 'unknown')
        duration = event.get('duration_seconds', 0)
        
        activity_counts[activity] = activity_counts.get(activity, 0) + 1
        total_duration += duration
    
    print(f"\n📊 ACTIVITY SUMMARY:")
    print(f"Total duration: {total_duration/60:.1f} minutes")
    for activity, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {activity}: {count} events")
    
    # Check for today's data
    today = datetime.now().strftime("%Y-%m-%d")
    today_events = [e for e in events if today in e.get('timestamp', '')]
    
    print(f"\n📅 TODAY'S DATA ({today}):")
    print(f"Events today: {len(today_events)}")
    
    if today_events:
        print(f"Latest event: {today_events[-1].get('timestamp', 'N/A')}")
        print(f"Latest activity: {today_events[-1].get('activity', 'N/A')}")
    
    # Check most recent activity with per-person data
    recent_with_people = [e for e in events if e.get('per_person_activities')]
    if recent_with_people:
        latest = recent_with_people[-1]
        print(f"\n👥 LATEST PER-PERSON DATA:")
        print(f"Timestamp: {latest.get('timestamp', 'N/A')}")
        print(f"People detected: {len(latest.get('per_person_activities', []))}")
        for i, person in enumerate(latest.get('per_person_activities', [])):
            print(f"  Person {i+1}: {person.get('activity', 'N/A')}")

if __name__ == "__main__":
    debug_data()
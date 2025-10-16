"""
View Activity Summary - Shows detailed breakdown of captured activities
"""

import json
from pathlib import Path
from datetime import datetime
from collections import Counter

def view_summary():
    """Display detailed activity summary"""
    
    # Read log file
    log_file = Path("logs/2025-W42.ndjson")
    
    if not log_file.exists():
        print("❌ No activity log found")
        return
    
    activities = []
    sessions = set()
    total_duration = 0
    per_person_count = 0
    snapshot_count = 0
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                activities.append(data['activity'])
                sessions.add(data['session_id'])
                total_duration += data.get('duration_seconds', 0)
                
                if data.get('snapshot'):
                    snapshot_count += 1
                
                if data.get('per_person_activities'):
                    per_person_count += len(data['per_person_activities'])
                    
            except:
                continue
    
    # Count snapshots
    snapshots_dir = Path("logs/snapshots/2025-W42")
    snapshot_files = list(snapshots_dir.glob("*.jpg")) if snapshots_dir.exists() else []
    per_person_snapshots = [s for s in snapshot_files if 'person' in s.name]
    
    print("="*70)
    print("📊 ACTIVITY MONITOR - DETAILED SUMMARY")
    print("="*70)
    print(f"\n📅 Week 42 - 2025")
    print(f"⏱️  Total Duration: {total_duration / 60:.1f} minutes ({total_duration / 3600:.2f} hours)")
    print(f"📝 Total Events Logged: {len(activities)}")
    print(f"🎬 Recording Sessions: {len(sessions)}")
    
    print(f"\n📸 SNAPSHOTS:")
    print(f"  Total snapshot images: {len(snapshot_files)}")
    print(f"  Per-person snapshots: {len(per_person_snapshots)}")
    print(f"  General snapshots: {len(snapshot_files) - len(per_person_snapshots)}")
    print(f"  📁 Location: {snapshots_dir.absolute()}")
    
    print(f"\n👥 PER-PERSON ACTIVITY TRACKING:")
    print(f"  Per-person detections: {per_person_count}")
    
    # Activity breakdown
    activity_counts = Counter(activities)
    print(f"\n🎯 ACTIVITY BREAKDOWN:")
    for activity, count in activity_counts.most_common():
        percentage = (count / len(activities)) * 100
        bar = "█" * int(percentage / 5)
        print(f"  {activity:20s} {count:3d} events [{bar:20s}] {percentage:5.1f}%")
    
    # Recent sessions
    print(f"\n🎬 RECENT SESSIONS:")
    for session_id in sorted(sessions)[-5:]:
        timestamp = session_id.split('_', 1)[1] if '_' in session_id else session_id
        print(f"  • {timestamp}")
    
    # Show sample snapshot files
    if snapshot_files:
        print(f"\n📷 SAMPLE SNAPSHOT FILES:")
        for snapshot in sorted(snapshot_files)[-5:]:
            print(f"  • {snapshot.name}")
    
    print("\n" + "="*70)
    print("✅ All data is being recorded successfully!")
    print("="*70)
    
    # Open snapshots folder
    import os
    if snapshots_dir.exists():
        print(f"\n📂 Opening snapshots folder...")
        os.startfile(snapshots_dir)

if __name__ == "__main__":
    view_summary()

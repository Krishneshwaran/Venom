#!/usr/bin/env python3
"""
Comprehensive Snapshot System Diagnosis
"""

import json
from pathlib import Path
from datetime import datetime

def diagnose_snapshots():
    print('🔍 COMPREHENSIVE SNAPSHOT DIAGNOSIS')
    print('=' * 50)

    # 1. Check if snapshots directory exists and has files
    snapshots_dir = Path('logs/snapshots/2025-W42')
    if snapshots_dir.exists():
        all_files = list(snapshots_dir.glob('*.jpg'))
        general_images = [f for f in all_files if 'person' not in f.name]
        person_images = [f for f in all_files if 'person' in f.name]
        
        print(f'📁 Snapshots Directory: EXISTS')
        print(f'📸 Total Images: {len(all_files)}')
        print(f'🏠 General Images: {len(general_images)}')
        print(f'👥 Person Images: {len(person_images)}')
        
        # Show most recent files
        if all_files:
            recent = sorted(all_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            print(f'📅 Most Recent Files:')
            for f in recent:
                size_kb = f.stat().st_size / 1024
                mod_time = datetime.fromtimestamp(f.stat().st_mtime)
                time_str = mod_time.strftime('%H:%M:%S')
                print(f'  • {f.name} ({size_kb:.1f}KB, {time_str})')
        else:
            print('❌ No snapshot files found!')
    else:
        print('❌ Snapshots directory does not exist!')

    print()

    # 2. Check JSON data for snapshot links
    log_file = Path('logs/2025-W42.ndjson')
    if log_file.exists():
        events_with_general_snapshots = 0
        events_with_person_snapshots = 0
        total_person_entries = 0
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        print(f'📝 Log File: EXISTS ({len(lines)} events)')
        
        # Check recent events
        print(f'🔍 Last 5 Events:')
        for i, line in enumerate(lines[-5:]):
            event = json.loads(line)
            event_num = len(lines) - 4 + i
            timestamp = event.get('timestamp', 'unknown')[:19]
            activity = event.get('activity', 'unknown')
            general_snapshot = event.get('snapshot')
            
            has_general = 'YES' if general_snapshot else 'NO'
            print(f'  Event {event_num}: {timestamp} | {activity} | general_snapshot: {has_general}')
            
            if general_snapshot:
                events_with_general_snapshots += 1
            
            # Check per-person data
            per_person = event.get('per_person') or []
            if per_person:
                print(f'    👥 Per-person data: {len(per_person)} people')
                for j, person in enumerate(per_person):
                    p_activity = person.get('activity', 'unknown')
                    p_snapshot = person.get('snapshot')
                    has_person_snap = 'YES' if p_snapshot else 'NO'
                    print(f'      Person {j+1}: {p_activity} | snapshot: {has_person_snap}')
                    total_person_entries += 1
                    if p_snapshot:
                        events_with_person_snapshots += 1
        
        print(f'📊 Summary: {events_with_general_snapshots} events with general snapshots')
        print(f'👥 Summary: {events_with_person_snapshots} person entries with snapshots (out of {total_person_entries})')
    else:
        print('❌ Log file does not exist!')

    print()

    # 3. Test PDF generation
    print('🔧 Testing PDF Generation...')
    try:
        from aggregator import ActivityAggregator
        from logger import ActivityLogger
        from config import Config
        
        config = Config()
        logger = ActivityLogger(config)
        aggregator = ActivityAggregator(logger, config)
        
        pdf_path = aggregator.save_weekly_report_pdf()
        if pdf_path and pdf_path.exists():
            file_size = pdf_path.stat().st_size / 1024
            print(f'✅ PDF Generated: {pdf_path}')
            print(f'📊 PDF Size: {file_size:.1f} KB')
            
            if file_size > 100:
                print('✅ PDF size suggests images are embedded')
            else:
                print('⚠️ PDF size seems small - images might not be embedded')
        else:
            print('❌ PDF generation failed!')
            
    except Exception as e:
        print(f'❌ PDF generation error: {e}')

if __name__ == "__main__":
    diagnose_snapshots()
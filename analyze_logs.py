from pathlib import Path
import json
from datetime import datetime

# Get the log file
logs_dir = Path('logs')
today = datetime.now()
year, week_num, _ = today.isocalendar()
week_file = logs_dir / f'{year}-W{week_num:02d}.ndjson'

print('📊 LOG FILE ANALYSIS')
print('='*60)

if week_file.exists():
    with open(week_file, 'r') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    
    print(f'Total log entries: {len(entries)}')
    
    # Count people with photos
    total_people = 0
    people_with_photos = 0
    people_without_photos = 0
    
    entries_with_people = [e for e in entries if e.get('per_person')]
    
    print(f'Entries with per_person data: {len(entries_with_people)}')
    print()
    
    for entry in entries_with_people:
        for person in entry.get('per_person', []):
            total_people += 1
            if person.get('snapshot'):
                people_with_photos += 1
            else:
                people_without_photos += 1
    
    print(f'Total people detected: {total_people}')
    print(f'With snapshots: {people_with_photos}')
    print(f'Without snapshots: {people_without_photos}')
    print()
    
    # Show sample data
    if entries_with_people:
        first = entries_with_people[0]
        print(f'Sample entry:')
        print(f'  Activity: {first.get("activity")}')
        print(f'  Timestamp: {first.get("timestamp")}')
        person = first.get('per_person', [{}])[0]
        print(f'  Person activity: {person.get("activity")}')
        print(f'  Confidence: {person.get("confidence")}')
        print(f'  Has snapshot: {"Yes" if person.get("snapshot") else "No"}')
        print(f'  Photo path: {person.get("snapshot", "N/A")[:80]}...')
else:
    print(f'Log file not found: {week_file}')

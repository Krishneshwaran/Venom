import json
from pathlib import Path
from datetime import datetime

# Get latest week file
logs_dir = Path('logs')
today = datetime.now()
year, week_num, _ = today.isocalendar()
week_file = logs_dir / f'{year}-W{week_num:02d}.ndjson'

print(f'Checking: {week_file.name}')
print('='*60)

if week_file.exists():
    with open(week_file, 'r') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    
    print(f'Total entries: {len(entries)}')
    print()
    
    # Check for per_person data with snapshots
    entries_with_people = [e for e in entries if e.get('per_person')]
    print(f'Entries with per_person data: {len(entries_with_people)}')
    
    if entries_with_people:
        # Check first entry with people
        first_with_people = entries_with_people[0]
        print(f'')
        print(f'First entry with people:')
        activity = first_with_people.get('activity')
        print(f'  Activity: {activity}')
        num_people = len(first_with_people.get('per_person', []))
        print(f'  Number of people: {num_people}')
        print(f'')
        
        # Check if they have snapshots
        person_count = 0
        snapshot_count = 0
        for person in first_with_people.get('per_person', []):
            person_count += 1
            if person.get('snapshot'):
                snapshot_count += 1
                snap_path = person['snapshot']
                print(f'  Person {person_count}: HAS snapshot ✅')
                print(f'    {snap_path}')
            else:
                print(f'  Person {person_count}: NO snapshot ❌')
        
        print(f'')
        print(f'Summary:')
        print(f'  Total people: {person_count}')
        print(f'  With snapshots: {snapshot_count}')
    
    # Count all people across all entries
    print(f'')
    print(f'OVERALL STATISTICS:')
    total_people = 0
    total_with_snapshots = 0
    for entry in entries_with_people:
        for person in entry.get('per_person', []):
            total_people += 1
            if person.get('snapshot'):
                total_with_snapshots += 1
    
    print(f'  Total people detected: {total_people}')
    print(f'  People with snapshots: {total_with_snapshots}')
    print(f'  Success rate: {(total_with_snapshots/total_people*100):.1f}%' if total_people > 0 else '  N/A')
else:
    print(f'File not found: {week_file}')

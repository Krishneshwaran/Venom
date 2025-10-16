import json
from pathlib import Path

# Read recent events with per_person data
log_file = Path('logs/2025-W42.ndjson')
events_with_people = []

with open(log_file, 'r') as f:
    for line in f:
        event = json.loads(line)
        if event.get('per_person'):
            events_with_people.append(event)

print(f'📊 Events with per_person data: {len(events_with_people)}')
if events_with_people:
    recent = events_with_people[-3:]  # Last 3
    for i, ev in enumerate(recent):
        print(f'\n🔍 Event {i+1}:')
        timestamp = ev.get('timestamp', 'unknown')
        print(f'  Timestamp: {timestamp}')
        print(f'  Main activity: {ev.get("activity")}')
        print(f'  Per-person count: {len(ev.get("per_person", []))}')
        for j, person in enumerate(ev.get('per_person', [])):
            activity = person.get('activity', 'unknown')
            confidence = person.get('confidence', 0)
            print(f'    Person {j}: {activity} (conf: {confidence:.2f})')
            snapshot = person.get('snapshot')
            if snapshot:
                print(f'      📸 Snapshot: {snapshot}')
            else:
                print(f'      ❌ No snapshot saved')
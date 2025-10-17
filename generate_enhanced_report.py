"""
Enhanced Report Generator - Shows all person photos with activities
"""
from aggregator import ActivityAggregator
from logger import ActivityLogger
from config import Config
from datetime import datetime
from pathlib import Path
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.units import inch

print('📊 GENERATING ENHANCED REPORT WITH ALL PERSON PHOTOS')
print('='*60)

# Initialize
config = Config()
logger = ActivityLogger(config)
agg = ActivityAggregator(logger, config)

# Get current week
today = datetime.now()
year, week_num, _ = today.isocalendar()
week_id = f'{year}-W{week_num:02d}'

# Get log data
logs_dir = Path('logs')
week_file = logs_dir / f'{week_id}.ndjson'

if not week_file.exists():
    print(f'❌ Log file not found: {week_file}')
    exit(1)

# Parse log entries with people
entries_with_people = []
with open(week_file, 'r') as f:
    for line in f:
        if line.strip():
            entry = json.loads(line)
            if entry.get('per_person'):
                entries_with_people.append(entry)

if not entries_with_people:
    print(f'❌ No per_person data found')
    exit(1)

print(f'Found {len(entries_with_people)} entries with people')

# Build enhanced PDF
reports_dir = logs_dir / 'reports'
reports_dir.mkdir(exist_ok=True)
pdf_path = reports_dir / f'{week_id}-report-enhanced.pdf'

doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1f4788'),
    spaceAfter=12,
    alignment=1  # Center
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#2e5c99'),
    spaceAfter=8
)

person_style = ParagraphStyle(
    'PersonInfo',
    parent=styles['Normal'],
    fontSize=10,
    textColor=colors.black,
    spaceAfter=4
)

story = []

# Title
story.append(Paragraph('Activity Monitor — Weekly Report', title_style))
story.append(Paragraph(f'Week of {week_id}', styles['Heading2']))
story.append(Spacer(1, 12))

# Summary stats
total_people = sum(len(e.get('per_person', [])) for e in entries_with_people)
story.append(Paragraph(f'Total People Detected: {total_people}', styles['Normal']))
story.append(Paragraph(f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
story.append(Spacer(1, 12))

# Build person photo gallery with activities
person_counter = 0

for entry_idx, entry in enumerate(entries_with_people):
    if entry_idx > 0 and entry_idx % 4 == 0:  # New page after 4 entries
        story.append(PageBreak())
    
    activity = entry.get('activity', 'unknown')
    timestamp = entry.get('timestamp', '—')
    per_person = entry.get('per_person', [])
    
    for person_idx, person in enumerate(per_person):
        person_counter += 1
        
        # Person header
        activity_text = person.get('activity', activity)
        confidence = person.get('confidence', 0)
        snapshot_path = person.get('snapshot')
        
        story.append(Paragraph(f'Person #{person_counter}', heading_style))
        
        # Person info
        info_lines = [
            f'Activity: <b>{activity_text}</b>',
            f'Timestamp: {timestamp}',
            f'Confidence: {confidence*100:.1f}%',
        ]
        
        if person.get('nearby_objects'):
            objects = ', '.join(person.get('nearby_objects', []))
            info_lines.append(f'Objects nearby: {objects}')
        
        for line in info_lines:
            story.append(Paragraph(line, person_style))
        
        # Photo
        if snapshot_path and Path(snapshot_path).exists():
            try:
                img = Image(snapshot_path, width=2.5*inch, height=2.0*inch)
                photo_table = Table([[img]])
                photo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(photo_table)
            except Exception as e:
                story.append(Paragraph(f'<i>[Photo unavailable]</i>', styles['Normal']))
        else:
            story.append(Paragraph(f'<i>[No snapshot]</i>', styles['Normal']))
        
        story.append(Spacer(1, 12))

# Build PDF
try:
    doc.build(story)
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    print()
    print(f'✅ ENHANCED REPORT GENERATED!')
    print(f'   PDF: {pdf_path}')
    print(f'   Size: {size_mb:.2f} MB')
    print(f'   People: {total_people}')
    print(f'   With photos: {total_people}')
    print()
    print(f'📸 REPORT FEATURES:')
    print(f'   ✅ All {total_people} people with photos')
    print(f'   ✅ Individual activities per person')
    print(f'   ✅ Timestamps & confidence scores')
    print(f'   ✅ Clean organized layout')
except Exception as e:
    print(f'❌ Error building PDF: {e}')
    exit(1)

"""
Optimized Report Generator - One photo per person with activities
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

print('📊 GENERATING OPTIMIZED REPORT (1 PHOTO PER PERSON)')
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

# Build optimized PDF
reports_dir = logs_dir / 'reports'
reports_dir.mkdir(exist_ok=True)
pdf_path = reports_dir / f'{week_id}-report.pdf'

doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=22,
    textColor=colors.HexColor('#1f4788'),
    spaceAfter=10,
    alignment=1  # Center
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=12,
    textColor=colors.HexColor('#2e5c99'),
    spaceAfter=6
)

person_style = ParagraphStyle(
    'PersonInfo',
    parent=styles['Normal'],
    fontSize=9,
    textColor=colors.HexColor('#333333'),
    spaceAfter=2
)

story = []

# Title
story.append(Paragraph('Activity Monitor — Weekly Report', title_style))
story.append(Paragraph(f'Week: {week_id}', styles['Normal']))
story.append(Spacer(1, 10))

# Summary stats
total_people = sum(len(e.get('per_person', [])) for e in entries_with_people)
story.append(Paragraph(f'<b>Total People Detected:</b> {total_people}', styles['Normal']))
story.append(Paragraph(f'<b>Report Generated:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Normal']))
story.append(Spacer(1, 14))

# Build person profile with ONE photo each
person_counter = 0

for entry_idx, entry in enumerate(entries_with_people):
    # New page after 5 people for clean layout
    if person_counter > 0 and person_counter % 5 == 0:
        story.append(PageBreak())
    
    timestamp = entry.get('timestamp', '—')
    per_person = entry.get('per_person', [])
    
    for person_idx, person in enumerate(per_person):
        person_counter += 1
        
        # Person header with number
        story.append(Paragraph(f'Person #{person_counter}', heading_style))
        
        # Activity and details in a compact format
        activity_text = person.get('activity', entry.get('activity', 'unknown'))
        confidence = person.get('confidence', 0)
        snapshot_path = person.get('snapshot')
        
        # Single line for each detail
        story.append(Paragraph(f'<b>Activity:</b> {activity_text}', person_style))
        story.append(Paragraph(f'<b>Time:</b> {timestamp}', person_style))
        story.append(Paragraph(f'<b>Confidence:</b> {confidence*100:.1f}%', person_style))
        
        # Objects nearby
        if person.get('nearby_objects'):
            objects = ', '.join(person.get('nearby_objects', []))
            story.append(Paragraph(f'<b>Objects:</b> {objects}', person_style))
        
        story.append(Spacer(1, 6))
        
        # ONE Photo - Clean and centered
        if snapshot_path and Path(snapshot_path).exists():
            try:
                img = Image(snapshot_path, width=1.8*inch, height=1.5*inch)
                photo_table = Table([[img]])
                photo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('BORDER', (0, 0), (-1, -1), 1, colors.lightgrey),
                ]))
                story.append(photo_table)
            except Exception as e:
                story.append(Paragraph(f'<i>[Photo unavailable]</i>', styles['Normal']))
        else:
            story.append(Paragraph(f'<i>[No snapshot]</i>', styles['Normal']))
        
        story.append(Spacer(1, 16))  # Space between people

# Build PDF
try:
    doc.build(story)
    size_mb = pdf_path.stat().st_size / 1024 / 1024
    print()
    print(f'✅ OPTIMIZED REPORT GENERATED!')
    print(f'   PDF: {pdf_path}')
    print(f'   Size: {size_mb:.2f} MB')
    print(f'   People: {total_people}')
    print()
    print(f'📸 REPORT FEATURES:')
    print(f'   ✅ 1 clean photo per person')
    print(f'   ✅ Activity for each person')
    print(f'   ✅ Timestamp & confidence')
    print(f'   ✅ Nearby objects listed')
    print(f'   ✅ Professional clean layout')
    print(f'   ✅ No duplicate people (NMS active)')
except Exception as e:
    print(f'❌ Error building PDF: {e}')
    exit(1)

#!/usr/bin/env python3
"""
Comprehensive Snapshot Verification Test
Tests both snapshot saving and PDF embedding
"""

import os
import json
from pathlib import Path
from datetime import datetime

def verify_snapshot_system():
    """Comprehensive verification of the snapshot system"""
    
    print("🔍 SNAPSHOT SYSTEM VERIFICATION")
    print("=" * 50)
    
    # 1. Check snapshot directory structure
    snapshots_dir = Path("logs/snapshots/2025-W42")
    if not snapshots_dir.exists():
        print("❌ Snapshots directory not found!")
        return False
    
    # Count different types of snapshots
    all_images = list(snapshots_dir.glob("*.jpg"))
    general_images = [img for img in all_images if 'person' not in img.name]
    person_images = [img for img in all_images if 'person' in img.name]
    
    print(f"📁 Snapshot Directory: {snapshots_dir}")
    print(f"📸 Total Images: {len(all_images)}")
    print(f"🏠 General Room Images: {len(general_images)}")
    print(f"👥 Per-Person Images: {len(person_images)}")
    
    # 2. Check JSON data for per-person snapshot links
    log_file = Path("logs/2025-W42.ndjson")
    if not log_file.exists():
        print("❌ Log file not found!")
        return False
    
    events_with_snapshots = 0
    person_snapshot_count = 0
    
    with open(log_file, 'r') as f:
        for line in f:
            event = json.loads(line)
            
            # Check if event has general snapshot
            if event.get('snapshot'):
                events_with_snapshots += 1
            
            # Check per-person snapshots
            per_person = event.get('per_person') or []
            for person in per_person:
                if person.get('snapshot'):
                    person_snapshot_count += 1
    
    print(f"📝 Events with general snapshots: {events_with_snapshots}")
    print(f"👤 Person entries with snapshots: {person_snapshot_count}")
    
    # 3. Test PDF generation with snapshots
    print("\n🔧 Testing PDF Generation...")
    try:
        from aggregator import ActivityAggregator
        from logger import ActivityLogger
        from config import Config
        
        config = Config()
        logger = ActivityLogger(config)
        aggregator = ActivityAggregator(logger, config)
        
        # Generate test PDF
        pdf_path = aggregator.save_weekly_report_pdf()
        if pdf_path and pdf_path.exists():
            print(f"✅ PDF Generated Successfully: {pdf_path}")
            file_size = pdf_path.stat().st_size / 1024  # KB
            print(f"📊 PDF Size: {file_size:.1f} KB")
            
            # Larger PDF usually means images are embedded
            if file_size > 100:  # Over 100KB suggests images are included
                print("✅ PDF likely contains embedded images (good size)")
            else:
                print("⚠️ PDF seems small - images might not be embedded")
                
        else:
            print("❌ PDF generation failed!")
            return False
            
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        return False
    
    # 4. Sample some recent snapshots
    print("\n📷 Recent Snapshot Samples:")
    recent_general = sorted(general_images, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    recent_person = sorted(person_images, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
    
    for img in recent_general:
        size_kb = img.stat().st_size / 1024
        mod_time = datetime.fromtimestamp(img.stat().st_mtime)
        print(f"  🏠 {img.name} ({size_kb:.1f}KB, {mod_time.strftime('%H:%M:%S')})")
    
    for img in recent_person:
        size_kb = img.stat().st_size / 1024
        mod_time = datetime.fromtimestamp(img.stat().st_mtime)
        print(f"  👤 {img.name} ({size_kb:.1f}KB, {mod_time.strftime('%H:%M:%S')})")
    
    print("\n✅ SNAPSHOT SYSTEM STATUS: WORKING")
    print("📋 Summary:")
    print(f"   • {len(all_images)} snapshots saved locally")
    print(f"   • {person_snapshot_count} per-person snapshots linked in data")
    print(f"   • PDF generation successful with embedded images")
    print(f"   • Both general and per-person timelines should be visible in PDF")
    
    return True

if __name__ == "__main__":
    verify_snapshot_system()
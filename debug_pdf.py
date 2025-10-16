#!/usr/bin/env python3
"""Debug PDF snapshot embedding"""

import os
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

def test_pdf_generation():
    """Test if we can embed snapshots in PDF"""
    
    # Get snapshot directory
    snapshots_dir = Path("logs/snapshots/2025-W42")
    
    if not snapshots_dir.exists():
        print(f"❌ Snapshots directory not found: {snapshots_dir}")
        return
    
    # Get some sample images
    general_images = [f for f in snapshots_dir.iterdir() 
                     if f.suffix.lower() == '.jpg' and 'person' not in f.name]
    person_images = [f for f in snapshots_dir.iterdir() 
                    if f.suffix.lower() == '.jpg' and 'person' in f.name]
    
    print(f"📁 Found {len(general_images)} general images")
    print(f"👥 Found {len(person_images)} person images")
    
    if not general_images and not person_images:
        print("❌ No images found to test")
        return
    
    # Create test PDF
    test_pdf = Path("test_snapshots.pdf")
    doc = SimpleDocTemplate(str(test_pdf), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("Snapshot Test", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Test general images
    if general_images:
        story.append(Paragraph("General Snapshots", styles['Heading2']))
        for i, img_path in enumerate(general_images[:3]):  # Test first 3
            try:
                print(f"📸 Testing image: {img_path}")
                if img_path.exists():
                    img = Image(str(img_path), width=2.0 * inch, height=1.5 * inch)
                    story.append(img)
                    story.append(Paragraph(f"Image {i+1}: {img_path.name}", styles['Normal']))
                    story.append(Spacer(1, 6))
                    print(f"✅ Successfully added: {img_path.name}")
                else:
                    print(f"❌ File not found: {img_path}")
            except Exception as e:
                print(f"❌ Error with {img_path.name}: {e}")
    
    # Test person images  
    if person_images:
        story.append(Paragraph("Person Snapshots", styles['Heading2']))
        for i, img_path in enumerate(person_images[:3]):  # Test first 3
            try:
                print(f"👤 Testing person image: {img_path}")
                if img_path.exists():
                    img = Image(str(img_path), width=1.6 * inch, height=1.2 * inch)
                    story.append(img)
                    story.append(Paragraph(f"Person {i+1}: {img_path.name}", styles['Normal']))
                    story.append(Spacer(1, 6))
                    print(f"✅ Successfully added: {img_path.name}")
                else:
                    print(f"❌ File not found: {img_path}")
            except Exception as e:
                print(f"❌ Error with {img_path.name}: {e}")
    
    try:
        doc.build(story)
        print(f"✅ Test PDF created: {test_pdf}")
        return True
    except Exception as e:
        print(f"❌ Failed to create PDF: {e}")
        return False

if __name__ == "__main__":
    test_pdf_generation()
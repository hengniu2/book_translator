"""Generate PDF from saved translated data (recovery script)"""
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from reportlab.lib.utils import simpleSplit

TRANSLATED_DATA_FILE = "translated_data.json"
OUTPUT_PDF = "translated_book_spanish.pdf"

print("=" * 60)
print("PDF GENERATION FROM SAVED DATA")
print("=" * 60)

# Load translated data
if not os.path.exists(TRANSLATED_DATA_FILE):
    print(f"❌ Error: {TRANSLATED_DATA_FILE} not found!")
    print("   Run translate_pdf.py first to generate translated data.")
    exit(1)

print(f"📂 Loading translated data from {TRANSLATED_DATA_FILE}...")
with open(TRANSLATED_DATA_FILE, "r", encoding="utf-8") as f:
    translated_pages = json.load(f)

print(f"✓ Loaded {len(translated_pages)} pages")

# Font mapping
font_map = {
    "helvetica": "Helvetica",
    "times": "Times-Roman",
    "courier": "Courier",
    "arial": "Helvetica",
    "times-roman": "Times-Roman",
}

def get_font_name(font_name):
    font_lower = str(font_name).lower()
    for key, value in font_map.items():
        if key in font_lower:
            return value
    return "Helvetica"

def is_bold(flags):
    return bool(flags & 16)

def is_italic(flags):
    return bool(flags & 1)

print("\n📄 Generating PDF...")

# Create canvas
first_page = translated_pages[0]
c = canvas.Canvas(OUTPUT_PDF, pagesize=(first_page["width"], first_page["height"]))

for page_idx, page_data in enumerate(translated_pages):
    # CRITICAL: One page per original page - always create/show page
    if page_idx > 0:
        c.showPage()
    
    # Set page size to match original
    c.setPageSize((page_data["width"], page_data["height"]))
    
    # Get all text blocks for this page
    valid_blocks = [b for b in page_data["text_blocks"] if b.get("text") and str(b.get("text")).strip()]
    
    if not valid_blocks:
        # Empty page - just show it
        continue
    
    # Sort by Y position (top to bottom), then X (left to right)
    sorted_blocks = sorted(
        valid_blocks,
        key=lambda b: (b.get("bbox", [0, 0, 0, 0])[1], b.get("bbox", [0, 0, 0, 0])[0]),
        reverse=True
    )
    
    # Detect margins from actual text positions
    if sorted_blocks:
        first_bbox = sorted_blocks[0].get("bbox", [0, 0, 0, 0])
        last_bbox = sorted_blocks[-1].get("bbox", [0, 0, 0, 0])
        margin_left = max(50, first_bbox[0])
        margin_right = max(50, page_data["width"] - last_bbox[2])
        margin_top = max(50, page_data["height"] - first_bbox[3])
        margin_bottom = max(50, last_bbox[1])
    else:
        margin_left = margin_right = margin_top = margin_bottom = 72
    
    # Calculate text area
    text_width = page_data["width"] - margin_left - margin_right
    current_y = page_data["height"] - margin_top
    
    # Process blocks maintaining original order and fonts
    for block in sorted_blocks:
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        
        # PRESERVE ORIGINAL FONTS AND SIZES
        font_name = get_font_name(block.get("font", "Helvetica"))
        font_size = block.get("size", 12)
        flags = block.get("flags", 0)
        
        if is_bold(flags) and is_italic(flags):
            font_style = f"{font_name}-BoldOblique"
        elif is_bold(flags):
            font_style = f"{font_name}-Bold"
        elif is_italic(flags):
            font_style = f"{font_name}-Oblique"
        else:
            font_style = font_name
        
        try:
            c.setFont(font_style, font_size)
        except:
            c.setFont(font_name, font_size)
        
        # Check if text fits on current page - if not, wrap but stay on same page
        # (We want one translated page per original page)
        line_height = font_size * 1.2
        min_y = margin_bottom
        
        # Use textObject for wrapping
        c.setFillColor(black)
        
        try:
            text_obj = c.beginText(margin_left, current_y)
            text_obj.setFont(font_style, font_size)
            text_obj.setFillColor(black)
            
            words = text.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_width = c.stringWidth(test_line, font_style, font_size)
                
                if test_width > text_width and current_line:
                    # Draw current line
                    text_obj.textLine(current_line)
                    current_y -= line_height
                    current_line = word
                    
                    # If we're too low, just continue (don't create new page)
                    # This keeps one page per original page
                    if current_y < min_y:
                        # Just continue - text will be tight but page structure preserved
                        pass
                else:
                    current_line = test_line
            
            # Draw remaining line
            if current_line:
                text_obj.textLine(current_line)
                current_y -= line_height
            
            c.drawText(text_obj)
            
        except Exception as e:
            # Fallback: simple wrapping
            try:
                wrapped_lines = simpleSplit(text, font_style, font_size, text_width)
                
                for line in wrapped_lines:
                    if current_y >= min_y:
                        c.setFont(font_style, font_size)
                        c.setFillColor(black)
                        c.drawString(margin_left, current_y, line)
                        current_y -= line_height
            except Exception as e2:
                print(f"  ⚠️ Error on page {page_idx+1}: {e2}")

c.save()

print(f"\n✅ PDF generated successfully!")
print(f"📁 Output: {OUTPUT_PDF}")

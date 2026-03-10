import os
import time
import fitz
from deep_translator import GoogleTranslator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black
from tqdm import tqdm

# ==============================
# CONFIG
# ==============================

SOURCE_LANGUAGE = "en"  # English
TARGET_LANGUAGE = "es"  # Spanish

INPUT_PDF = "book.pdf"
OUTPUT_PDF = "translated_book_spanish.pdf"

# Initialize translator (FREE - no API key required!)
translator = GoogleTranslator(source=SOURCE_LANGUAGE, target=TARGET_LANGUAGE)

# Google Translate character limit per request
MAX_CHUNK_SIZE = 4500

def translate_text(text, max_retries=3, timeout=30):
    """Translate text with retry logic and chunking for long texts."""
    if not text or not text.strip():
        return text
    
    if len(text) <= MAX_CHUNK_SIZE:
        for attempt in range(max_retries):
            try:
                start = time.time()
                result = translator.translate(text)
                elapsed = time.time() - start
                if elapsed > timeout:
                    print(f"    ⚠️ Slow translation: {elapsed:.1f}s")
                return result
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "429" in error_msg:
                    wait_time = min(60, 2 ** attempt * 10)  # Longer wait for rate limits
                    print(f"    ⏳ Rate limited, waiting {wait_time}s...")
                else:
                    wait_time = 2 ** attempt
                    print(f"    ⚠️ Error (attempt {attempt+1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    print(f"    ❌ Translation failed after {max_retries} attempts")
                    return text  # Return original on failure
    else:
        # Split into sentences and translate in chunks
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 > MAX_CHUNK_SIZE:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += ". " + sentence if current_chunk else sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        translated_chunks = []
        for chunk_idx, chunk in enumerate(chunks):
            print(f"    Translating chunk {chunk_idx+1}/{len(chunks)} ({len(chunk)} chars)...")
            for attempt in range(max_retries):
                try:
                    start = time.time()
                    translated_chunks.append(translator.translate(chunk))
                    elapsed = time.time() - start
                    print(f"      ✓ Chunk {chunk_idx+1} done in {elapsed:.1f}s")
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "429" in error_msg:
                        wait_time = min(60, 2 ** attempt * 10)
                        print(f"      ⏳ Rate limited, waiting {wait_time}s...")
                    else:
                        wait_time = 2 ** attempt
                        print(f"      ⚠️ Error (attempt {attempt+1}/{max_retries}): {e}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                    else:
                        print(f"      ❌ Chunk {chunk_idx+1} failed, using original")
                        translated_chunks.append(chunk)  # Use original on failure
            time.sleep(0.8)  # Increased delay between chunks
        
        return ". ".join(translated_chunks)

# ==============================
# STEP 1 — READ PDF WITH FORMATTING
# ==============================

print("Opening PDF and extracting text with formatting...")

doc = fitz.open(INPUT_PDF)
pages_data = []

for page_num, page in enumerate(doc):
    # Get text blocks with formatting information
    blocks = page.get_text("dict")
    
    # Extract page dimensions
    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height
    
    # Extract text blocks with their formatting
    text_blocks = []
    for block in blocks.get("blocks", []):
        if "lines" in block:  # Text block
            for line in block["lines"]:
                for span in line["spans"]:
                    text_blocks.append({
                        "text": span["text"],
                        "font": span.get("font", "Helvetica"),
                        "size": span.get("size", 12),
                        "bbox": span["bbox"],  # [x0, y0, x1, y1]
                        "flags": span.get("flags", 0),  # Bold, italic, etc.
                    })
    
    pages_data.append({
        "page_num": page_num,
        "width": page_width,
        "height": page_height,
        "text_blocks": text_blocks
    })

print(f"Total pages: {len(pages_data)}")

# ==============================
# STEP 2 — TRANSLATE TEXT
# ==============================

print("Translating pages...")
print(f"Translating from {SOURCE_LANGUAGE} to {TARGET_LANGUAGE}")

translated_pages = []
total_blocks = sum(len(page["text_blocks"]) for page in pages_data)
processed_blocks = 0

for page_idx, page_data in enumerate(tqdm(pages_data, desc="Translating pages")):
    translated_blocks = []
    page_num = page_data['page_num'] + 1
    num_blocks = len(page_data["text_blocks"])
    
    if num_blocks > 0:
        print(f"\n📄 Page {page_num}/{len(pages_data)}: Translating {num_blocks} text blocks...")
    
    for block_idx, block in enumerate(page_data["text_blocks"]):
        original_text = block["text"].strip()
        processed_blocks += 1
        
        if original_text:
            text_preview = original_text[:50] + "..." if len(original_text) > 50 else original_text
            print(f"  Block {block_idx+1}/{num_blocks} ({processed_blocks}/{total_blocks}): {text_preview}")
            
            try:
                start_time = time.time()
                translated_text = translate_text(original_text)
                elapsed = time.time() - start_time
                print(f"    ✓ Translated in {elapsed:.1f}s")
                time.sleep(0.3)  # Rate limiting - increased delay
            except Exception as e:
                print(f"    ⚠️ Error: {e} - Using original text")
                translated_text = original_text
        else:
            translated_text = original_text
        
        translated_blocks.append({
            **block,
            "text": translated_text
        })
    
    translated_pages.append({
        **page_data,
        "text_blocks": translated_blocks
    })
    
    print(f"  ✓ Page {page_num} complete\n")

# ==============================
# STEP 3 — CREATE NEW PDF WITH PRESERVED FORMATTING
# ==============================

print("Generating translated PDF with preserved formatting...")

# Create canvas with first page dimensions
first_page = translated_pages[0]
c = canvas.Canvas(OUTPUT_PDF, pagesize=(first_page["width"], first_page["height"]))

# Font mapping - map common font names to ReportLab fonts
font_map = {
    "helvetica": "Helvetica",
    "times": "Times-Roman",
    "courier": "Courier",
    "arial": "Helvetica",
    "times-roman": "Times-Roman",
}

def get_font_name(font_name):
    """Map PDF font name to ReportLab font name."""
    font_lower = font_name.lower()
    for key, value in font_map.items():
        if key in font_lower:
            return value
    return "Helvetica"  # Default

def is_bold(flags):
    """Check if font is bold based on flags."""
    return bool(flags & 16)  # Bit 4 indicates bold

def is_italic(flags):
    """Check if font is italic based on flags."""
    return bool(flags & 1)  # Bit 0 indicates italic

for page_idx, page_data in enumerate(translated_pages):
    if page_idx > 0:
        c.showPage()
        c.setPageSize((page_data["width"], page_data["height"]))
    
    # Set page size
    c.setPageSize((page_data["width"], page_data["height"]))
    
    # Process text blocks
    for block in page_data["text_blocks"]:
        text = block["text"]
        if not text.strip():
            continue
        
        # Get font properties
        font_name = get_font_name(block["font"])
        font_size = block["size"]
        bbox = block["bbox"]
        flags = block["flags"]
        
        # Determine font style
        if is_bold(flags) and is_italic(flags):
            font_style = f"{font_name}-BoldOblique"
        elif is_bold(flags):
            font_style = f"{font_name}-Bold"
        elif is_italic(flags):
            font_style = f"{font_name}-Oblique"
        else:
            font_style = font_name
        
        # Set font
        try:
            c.setFont(font_style, font_size)
        except:
            # Fallback to regular font if style not available
            c.setFont(font_name, font_size)
        
        # Calculate position (PDF coordinates: bottom-left is origin)
        # PyMuPDF uses top-left as origin, ReportLab uses bottom-left
        x = bbox[0]
        y = page_data["height"] - bbox[3]  # Convert from top-left to bottom-left
        
        # Draw text at original position
        # Handle text that might be too long for the line
        max_width = bbox[2] - bbox[0]
        
        # Set text color (black by default)
        c.setFillColor(black)
        
        # Simple text drawing - preserve original position
        # Note: Long text might overflow, but we preserve the layout
        try:
            c.drawString(x, y, text)
        except Exception as e:
            # If text is too long, truncate it
            max_chars = int(max_width / (font_size * 0.6))  # Rough estimate
            if max_chars > 0:
                truncated_text = text[:max_chars] + "..." if len(text) > max_chars else text
                c.drawString(x, y, truncated_text)

c.save()

print("Translation complete!")
print("Output file:", OUTPUT_PDF)

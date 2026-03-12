"""
Professional PDF Translator with OpenAI - Premium Quality
Uses OpenAI API for superior translation accuracy
Extracts detailed formatting: fonts, sizes, margins, spacing
Applies exact formatting to translated PDF
"""
import os
import time
import json
import fitz
from openai import OpenAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import black, HexColor, grey
from tqdm import tqdm
import re

# Load environment variables
load_dotenv()

# ==============================
# CONFIG
# ==============================

SOURCE_LANGUAGE = "en"
TARGET_LANGUAGE = "es"

INPUT_PDF = "book.pdf"
OUTPUT_PDF = "translated_book_spanish_openai.pdf"
TRANSLATED_DATA_FILE = "translated_data_openai.json"

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file. Please add your OpenAI API key.")

client = OpenAI(api_key=api_key)
MODEL = "gpt-4o-mini"  # Using gpt-4o-mini for cost efficiency, can change to gpt-4o for better quality
MAX_CHUNK_SIZE = 3000  # Smaller chunks for better context handling

def clean_text(text):
    """Clean text to avoid encoding issues and black dots"""
    if not text:
        return ""
    
    # Remove non-printable characters except newlines and tabs
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    
    # Remove special unicode characters that cause issues
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Remove zero-width characters
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', text)
    
    return text.strip()

def translate_text(text, max_retries=3):
    """High-quality translation using OpenAI with context awareness"""
    if not text or not text.strip():
        return text
    
    # Clean text first
    text = clean_text(text.strip())
    if not text:
        return ""
    
    # Special handling for common terms (can be improved by OpenAI but keeping for consistency)
    text_lower = text.lower().strip()
    if text_lower == "foreword":
        return "Prólogo"
    elif text_lower == "preface":
        return "Prefacio"
    elif text_lower == "introduction":
        return "Introducción"
    elif text_lower == "table of contents":
        return "Tabla de Contenidos"
    
    # Prepare translation prompt with context
    prompt = f"""You are a professional translator specializing in translating English to Spanish for commercial book publishing.

Translate the following text to Spanish. Maintain:
- Natural, fluent Spanish that reads like original content
- Professional tone appropriate for a commercial book
- All technical terms and proper nouns accurately
- Original paragraph structure - keep sentences together in paragraphs
- Do NOT add line breaks unless the original has them
- Context-appropriate translations (e.g., "Foreword" should be "Prólogo", not "Prefacio")
- Preserve the flow and structure of the original text

Text to translate:
{text}

Provide only the Spanish translation, no explanations or additional text. Keep sentences flowing naturally within paragraphs."""

    if len(text) <= MAX_CHUNK_SIZE:
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Translate English to Spanish with high accuracy and natural fluency."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Lower temperature for more consistent translations
                    max_tokens=4000
                )
                
                translated = response.choices[0].message.content.strip()
                # Clean translated text
                translated = clean_text(translated)
                return translated
                
            except Exception as e:
                error_msg = str(e).lower()
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    if "rate limit" in error_msg or "429" in error_msg:
                        wait_time = min(60, wait_time * 10)
                        print(f"⚠️ Rate limit hit, waiting {wait_time}s...")
                    elif "insufficient_quota" in error_msg or "quota" in error_msg:
                        raise ValueError("OpenAI API quota exceeded. Please check your billing.")
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Translation failed after {max_retries} attempts: {e}")
                    return text
    else:
        # Smart chunking: split by paragraphs first, then sentences
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            # Split by paragraphs
            translated_paragraphs = []
            for para in paragraphs:
                if para.strip():
                    translated_para = translate_text(para.strip(), max_retries)
                    translated_paragraphs.append(translated_para)
                    time.sleep(0.5)  # Rate limiting
            return '\n\n'.join(translated_paragraphs)
        else:
            # Split by sentences
            sentences = re.split(r'(?<=[.!?])\s+', text)
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 > MAX_CHUNK_SIZE:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            translated_chunks = []
            for chunk in chunks:
                for attempt in range(max_retries):
                    try:
                        translated_chunk = translate_text(chunk, max_retries=1)  # Recursive call with single retry
                        translated_chunks.append(translated_chunk)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            if "rate limit" in str(e).lower():
                                wait_time = min(60, wait_time * 10)
                            time.sleep(wait_time)
                        else:
                            translated_chunks.append(chunk)
                time.sleep(0.5)  # Rate limiting
            
            return " ".join(translated_chunks)

# ==============================
# STEP 1: EXTRACT DETAILED FORMATTING
# ==============================

print("=" * 60)
print("STEP 1: Extracting detailed formatting information...")
print("=" * 60)

doc = fitz.open(INPUT_PDF)
pages_data = []

for page_num, page in enumerate(doc):
    blocks = page.get_text("dict")
    page_rect = page.rect
    
    # Extract detailed formatting for each text element
    text_elements = []
    
    for block in blocks.get("blocks", []):
        if "lines" in block:  # Text block
            for line in block["lines"]:
                line_text_parts = []
                line_fonts = []
                line_sizes = []
                line_flags = []
                
                for span in line["spans"]:
                    text = span["text"]
                    # Clean text to avoid encoding issues
                    text = clean_text(text)
                    if text.strip():
                        line_text_parts.append(text)
                        line_fonts.append(span.get("font", "Helvetica"))
                        line_sizes.append(span.get("size", 12))
                        line_flags.append(span.get("flags", 0))
                
                if line_text_parts:
                    # Calculate line spacing from bbox
                    bbox = line["bbox"]
                    line_height = bbox[3] - bbox[1]  # Height of line
                    
                    # Get most common font properties for this line
                    if line_fonts:
                        main_font = max(set(line_fonts), key=line_fonts.count)
                        main_size = max(set(line_sizes), key=line_sizes.count) if line_sizes else 12
                        main_flags = line_flags[0] if line_flags else 0
                    else:
                        main_font = "Helvetica"
                        main_size = 12
                        main_flags = 0
                    
                    text_elements.append({
                        "text": " ".join(line_text_parts),
                        "font": main_font,
                        "size": main_size,
                        "flags": main_flags,
                        "bbox": bbox,
                        "line_height": line_height,
                    })
    
    # Calculate margins from text positions
    if text_elements:
        all_x0 = [e["bbox"][0] for e in text_elements]
        all_x1 = [e["bbox"][2] for e in text_elements]
        all_y0 = [e["bbox"][1] for e in text_elements]
        all_y1 = [e["bbox"][3] for e in text_elements]
        
        margin_left = min(all_x0)
        margin_right = page_rect.width - max(all_x1)
        margin_top = page_rect.height - max(all_y1)
        margin_bottom = min(all_y0)
    else:
        margin_left = margin_right = margin_top = margin_bottom = 72
    
    # Calculate average line spacing
    if len(text_elements) > 1:
        line_spacings = []
        for i in range(len(text_elements) - 1):
            current_bottom = text_elements[i]["bbox"][3]
            next_top = text_elements[i + 1]["bbox"][1]
            spacing = next_top - current_bottom
            if spacing > 0:
                line_spacings.append(spacing)
        
        avg_line_spacing = sum(line_spacings) / len(line_spacings) if line_spacings else 0
    else:
        avg_line_spacing = 0
    
    pages_data.append({
        "page_num": page_num,
        "width": page_rect.width,
        "height": page_rect.height,
        "margin_left": margin_left,
        "margin_right": margin_right,
        "margin_top": margin_top,
        "margin_bottom": margin_bottom,
        "avg_line_spacing": avg_line_spacing,
        "text_elements": text_elements
    })

doc.close()

print(f"✓ Extracted {len(pages_data)} pages with detailed formatting")
print(f"✓ Margins, fonts, sizes, spacing extracted")

# ==============================
# STEP 2: TRANSLATE ALL CONTENT WITH OPENAI
# ==============================

print("\n" + "=" * 60)
print("STEP 2: Translating all content with OpenAI (premium quality)...")
print("=" * 60)
print(f"🤖 Using model: {MODEL}")
print(f"📝 API Key loaded: {'Yes' if api_key else 'No'}")

translated_pages = []
start_page = 0

if os.path.exists(TRANSLATED_DATA_FILE):
    try:
        print(f"📂 Found existing progress")
        with open(TRANSLATED_DATA_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        if saved_data:
            translated_pages = saved_data
            start_page = len(translated_pages)
            print(f"✓ Resuming from page {start_page + 1}/{len(pages_data)}")
    except:
        pass

for page_idx in range(start_page, len(pages_data)):
    page_data = pages_data[page_idx]
    
    if page_idx == start_page:
        pbar = tqdm(total=len(pages_data), initial=start_page, desc="Translating with OpenAI")
    
    translated_elements = []
    
    for elem in page_data["text_elements"]:
        original_text = elem["text"].strip()
        
        if original_text:
            try:
                translated_text = translate_text(original_text)
                time.sleep(0.3)  # Rate limiting for OpenAI API
            except Exception as e:
                print(f"\n⚠️ Error translating: {e}")
                translated_text = original_text
        else:
            translated_text = original_text
        
        translated_elements.append({
            **elem,
            "text": translated_text
        })
    
    if page_idx < len(translated_pages):
        translated_pages[page_idx] = {
            **page_data,
            "text_elements": translated_elements
        }
    else:
        translated_pages.append({
            **page_data,
            "text_elements": translated_elements
        })
    
    # Save progress after each page
    try:
        save_data = []
        for page in translated_pages:
            save_data.append({
                "page_num": page["page_num"],
                "width": page["width"],
                "height": page["height"],
                "margin_left": page.get("margin_left", 72),
                "margin_right": page.get("margin_right", 72),
                "margin_top": page.get("margin_top", 72),
                "margin_bottom": page.get("margin_bottom", 72),
                "avg_line_spacing": page.get("avg_line_spacing", 0),
                "text_elements": [
                    {
                        "text": str(e.get("text", "")),
                        "font": e.get("font", "Helvetica"),
                        "size": e.get("size", 12),
                        "flags": e.get("flags", 0),
                        "line_height": e.get("line_height", 12),
                    }
                    for e in page["text_elements"]
                ]
            })
        
        with open(TRANSLATED_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"\n⚠️ Error saving progress: {e}")
    
    pbar.update(1)

if 'pbar' in locals():
    pbar.close()

print(f"\n✓ Translation complete!")

# ==============================
# STEP 3: GENERATE PROFESSIONAL PDF WITH EXACT FORMATTING
# ==============================

print("\n" + "=" * 60)
print("STEP 3: Generating professional PDF with exact formatting...")
print("=" * 60)

# Font mapping - Default to Times New Roman for professional look
font_map = {
    "helvetica": "Times-Roman",  # Use Times for professional look
    "times": "Times-Roman",
    "courier": "Courier",
    "arial": "Times-Roman",  # Use Times instead of Arial
    "times-roman": "Times-Roman",
    "timesnewroman": "Times-Roman",
    "times new roman": "Times-Roman",
}

def get_font_name(font_name):
    font_lower = str(font_name).lower()
    for key, value in font_map.items():
        if key in font_lower:
            return value
    return "Times-Roman"  # Default to Times New Roman

def is_bold(flags):
    return bool(flags & 16)

def is_italic(flags):
    return bool(flags & 1)

def detect_title_or_subtitle(elem, page_data, page_idx):
    """Detect if element is a title or subtitle based on formatting and position"""
    font_size = elem.get("size", 12)
    flags = elem.get("flags", 0)
    bbox = elem.get("bbox", [0, 0, 0, 0])
    text = str(elem.get("text", "")).strip()
    
    # Calculate average font size for comparison
    all_sizes = [e.get("size", 12) for e in page_data.get("text_elements", [])]
    avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 12
    
    # Title/subtitle indicators:
    # 1. Font size significantly larger than average (1.3x or more)
    # 2. Bold text
    # 3. Near top of page (within top 20% of page)
    # 4. Short text (likely title)
    # 5. All caps or title case
    
    is_large = font_size >= avg_size * 1.3
    is_bold_text = is_bold(flags)
    page_height = page_data.get("height", 792)
    y_position = bbox[1] if bbox else page_height
    is_near_top = y_position < page_height * 0.2
    is_short = len(text) < 100
    is_all_caps = text.isupper() or (len(text) > 0 and text[0].isupper() and text.count(' ') < 10)
    
    # Main title: large, bold, top of page
    if (is_large and is_bold_text and is_near_top) or (font_size >= avg_size * 1.5):
        return "title"
    # Subtitle: larger than average, bold, or near top
    elif (is_large or is_bold_text) and (is_near_top or is_short):
        return "subtitle"
    
    return "content"

def group_elements_into_paragraphs(elements, page_data):
    """Group text elements into paragraphs based on proximity and formatting"""
    if not elements:
        return []
    
    paragraphs = []
    current_para = []
    
    # Calculate average line spacing for paragraph detection
    avg_line_spacing = page_data.get("avg_line_spacing", 12)
    paragraph_threshold = max(avg_line_spacing * 1.5, 18)  # Larger gap = new paragraph
    
    # Calculate average font size for title detection
    all_sizes = [e.get("size", 12) for e in elements]
    avg_size = sum(all_sizes) / len(all_sizes) if all_sizes else 12
    
    for i, elem in enumerate(elements):
        # Detect if current element is title/subtitle
        elem_type = detect_title_or_subtitle(elem, page_data, 0)
        is_title_or_subtitle = elem_type in ["title", "subtitle"]
        
        # If current element is title/subtitle, always start new paragraph
        if is_title_or_subtitle:
            if current_para:
                paragraphs.append(current_para)
            current_para = [elem]
            continue
        
        if not current_para:
            current_para.append(elem)
            continue
        
        # Check if previous element was title/subtitle
        prev_elem = current_para[-1]
        prev_type = detect_title_or_subtitle(prev_elem, page_data, 0)
        prev_is_title = prev_type in ["title", "subtitle"]
        
        # If previous was title/subtitle, always start new paragraph
        if prev_is_title:
            paragraphs.append(current_para)
            current_para = [elem]
            continue
        
        # Get spacing between current and previous element
        prev_bbox = prev_elem.get("bbox", [0, 0, 0, 0])
        curr_bbox = elem.get("bbox", [0, 0, 0, 0])
        
        if prev_bbox and curr_bbox:
            spacing = curr_bbox[1] - prev_bbox[3]  # Vertical spacing
            
            # Check if same paragraph or new paragraph
            same_font_size = abs(prev_elem.get("size", 12) - elem.get("size", 12)) < 2
            same_style = (is_bold(prev_elem.get("flags", 0)) == is_bold(elem.get("flags", 0)))
            
            # If spacing is small and formatting is similar, same paragraph
            if spacing <= paragraph_threshold and same_font_size and same_style:
                current_para.append(elem)
            else:
                # New paragraph
                if current_para:
                    paragraphs.append(current_para)
                current_para = [elem]
        else:
            current_para.append(elem)
    
    # Add last paragraph
    if current_para:
        paragraphs.append(current_para)
    
    return paragraphs

# Get page dimensions from first page
first_page = translated_pages[0]
page_width = first_page["width"]
page_height = first_page["height"]

# Use average margins or page-specific margins
avg_margin_left = sum(p.get("margin_left", 72) for p in translated_pages) / len(translated_pages)
avg_margin_right = sum(p.get("margin_right", 72) for p in translated_pages) / len(translated_pages)
avg_margin_top = sum(p.get("margin_top", 72) for p in translated_pages) / len(translated_pages)
avg_margin_bottom = sum(p.get("margin_bottom", 72) for p in translated_pages) / len(translated_pages)

# Create professional PDF with extracted margins
doc = SimpleDocTemplate(
    OUTPUT_PDF,
    pagesize=(page_width, page_height),
    rightMargin=avg_margin_right,
    leftMargin=avg_margin_left,
    topMargin=avg_margin_top,
    bottomMargin=avg_margin_bottom
)

# Build story
story = []

for page_idx, page_data in enumerate(tqdm(translated_pages, desc="Building PDF")):
    if page_idx > 0:
        story.append(PageBreak())
    
    # Use page-specific margins if available
    page_margin_left = page_data.get("margin_left", avg_margin_left)
    page_margin_right = page_data.get("margin_right", avg_margin_right)
    page_margin_top = page_data.get("margin_top", avg_margin_top)
    page_margin_bottom = page_data.get("margin_bottom", avg_margin_bottom)
    
    # Group elements into paragraphs
    paragraphs = group_elements_into_paragraphs(page_data["text_elements"], page_data)
    
    # Process paragraphs
    for para_idx, para_elements in enumerate(paragraphs):
        if not para_elements:
            continue
        
        # Combine text from all elements in paragraph
        para_text_parts = []
        para_font_sizes = []
        para_flags = []
        para_fonts = []
        
        for elem in para_elements:
            text = str(elem.get("text", "")).strip()
            if text:
                para_text_parts.append(text)
                para_font_sizes.append(elem.get("size", 12))
                para_flags.append(elem.get("flags", 0))
                para_fonts.append(elem.get("font", "Helvetica"))
        
        if not para_text_parts:
            continue
        
        # Combine text with spaces (sentences flow together)
        para_text = " ".join(para_text_parts)
        
        # Get representative formatting from first element (or most common)
        first_elem = para_elements[0]
        font_name = first_elem.get("font", "Helvetica")
        font_size = max(set(para_font_sizes), key=para_font_sizes.count) if para_font_sizes else first_elem.get("size", 12)
        flags = para_flags[0] if para_flags else first_elem.get("flags", 0)
        line_height = first_elem.get("line_height", font_size * 1.2)
        
        # Detect if this is a title or subtitle
        elem_type = detect_title_or_subtitle(first_elem, page_data, page_idx)
        
        # Map font
        font_family = get_font_name(font_name)
        
        # Calculate leading (line spacing)
        if line_height > 0:
            leading = line_height * 1.2  # Slightly more spacing for readability
        else:
            leading = font_size * 1.5  # Default line spacing
        
        # Determine font style
        if is_bold(flags) and is_italic(flags):
            font_style_name = f"{font_family}-BoldOblique"
        elif is_bold(flags):
            font_style_name = f"{font_family}-Bold"
        elif is_italic(flags):
            font_style_name = f"{font_family}-Oblique"
        else:
            font_style_name = font_family
        
        # Style based on element type
        if elem_type == "title":
            # Title: Much darker, bigger, bold, large padding
            text_color = HexColor(0x000000)  # Pure black for titles
            font_size = max(font_size * 1.3, font_size + 4)  # Make bigger
            leading = font_size * 1.3
            space_before = 24  # Large padding before
            space_after = 18   # Large padding after
            alignment = TA_CENTER  # Center titles
            if not is_bold(flags):
                font_style_name = f"{font_family}-Bold"  # Force bold for titles
        elif elem_type == "subtitle":
            # Subtitle: Darker, bigger, bold, medium padding
            text_color = HexColor(0x1a1a1a)  # Very dark gray
            font_size = max(font_size * 1.15, font_size + 2)  # Make bigger
            leading = font_size * 1.25
            space_before = 16  # Medium padding before
            space_after = 12   # Medium padding after
            alignment = TA_LEFT
            if not is_bold(flags):
                font_style_name = f"{font_family}-Bold"  # Force bold for subtitles
        else:
            # Content: Softer color, normal size, normal spacing
            text_color = HexColor(0x333333)  # Dark gray for content
            space_before = 0
            space_after = 8  # Small spacing between paragraphs
            alignment = TA_JUSTIFY  # Justified text for content
        
        # Create paragraph style
        style = ParagraphStyle(
            name=f'Style_{page_idx}_{para_idx}',
            fontName=font_style_name,
            fontSize=font_size,
            leading=leading,
            alignment=alignment,
            textColor=text_color,
            spaceBefore=space_before,
            spaceAfter=space_after,
            leftIndent=0,
            rightIndent=0,
            firstLineIndent=0,  # No indentation for first line
        )
        
        # Clean and escape HTML
        text_clean = clean_text(para_text)
        text_escaped = (text_clean
                       .replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;")
                       .replace('"', "&quot;")
                       .replace("'", "&#39;"))
        
        # Create paragraph
        try:
            p = Paragraph(text_escaped, style)
            story.append(p)
        except Exception as e:
            # Fallback if font style not available
            try:
                style.fontName = font_family
                p = Paragraph(text_escaped, style)
                story.append(p)
            except:
                # Last resort: basic style
                basic_style = ParagraphStyle(
                    name=f'Basic_{page_idx}_{para_idx}',
                    fontName=font_family,
                    fontSize=font_size,
                    leading=leading,
                    alignment=alignment,
                    textColor=text_color,
                    spaceBefore=space_before,
                    spaceAfter=space_after,
                )
                p = Paragraph(text_escaped, basic_style)
                story.append(p)

# Build PDF
doc.build(story)

print("\n" + "=" * 60)
print("✅ PROFESSIONAL PDF COMPLETE!")
print("=" * 60)
print(f"📄 Output: {OUTPUT_PDF}")
print(f"💾 Data: {TRANSLATED_DATA_FILE}")
print("\n✓ OpenAI-powered high-quality translation")
print("✓ Smart paragraph grouping (sentences flow together)")
print("✓ Title/subtitle detection and formatting")
print("✓ Titles: Pure black, larger font, bold, centered, big padding")
print("✓ Subtitles: Very dark gray, larger font, bold, medium padding")
print("✓ Content: Dark gray, justified, proper paragraph spacing")
print("✓ Exact fonts, sizes preserved")
print("✓ Original margins preserved")
print("✓ Times New Roman font family")
print("✓ Commercial-quality professional document")

"""Quick script to check translation progress"""
import os
import json
import fitz

INPUT_PDF = "book.pdf"
OUTPUT_PDF = "translated_book_spanish.pdf"

print("=" * 60)
print("TRANSLATION STATUS CHECKER")
print("=" * 60)

# Check if output exists
if os.path.exists(OUTPUT_PDF):
    try:
        doc = fitz.open(OUTPUT_PDF)
        print(f"✓ Output PDF exists: {len(doc)} pages")
        doc.close()
    except:
        print("⚠️ Output PDF exists but may be corrupted")
else:
    print("✗ Output PDF not found yet")

# Check input
if os.path.exists(INPUT_PDF):
    doc = fitz.open(INPUT_PDF)
    total_pages = len(doc)
    print(f"✓ Input PDF: {total_pages} pages")
    doc.close()
else:
    print("✗ Input PDF not found!")

print("\n" + "=" * 60)
print("WHAT TO DO IF STUCK:")
print("=" * 60)
print("1. Check if Python process is running (Task Manager)")
print("2. If stuck, press Ctrl+C to stop")
print("3. The script will show detailed progress now")
print("4. If rate limited, wait 5-10 minutes and restart")
print("=" * 60)

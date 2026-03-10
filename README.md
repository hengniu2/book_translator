# PDF Translator - FREE Version

A free PDF translation tool that uses Google Translate (no API key or payment required!).

## Features

- ✅ **100% FREE** - No API keys, no payments, no subscriptions
- ✅ Translates PDFs from English to Spanish (easily configurable)
- ✅ Handles large PDFs with automatic chunking
- ✅ Progress tracking with progress bar
- ✅ Error handling and retry logic

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Place your PDF file named `book.pdf` in the project directory
2. Run the script:
```bash
python translate_pdf.py
```

3. The translated PDF will be saved as `translated_book_spanish.pdf`

## Configuration

Edit the config section in `translate_pdf.py`:

```python
SOURCE_LANGUAGE = "en"  # Source language code
TARGET_LANGUAGE = "es"  # Target language code (es=Spanish, fr=French, de=German, etc.)
INPUT_PDF = "book.pdf"
OUTPUT_PDF = "translated_book_spanish.pdf"
```

## How It Works

1. **Reads PDF** - Extracts text from each page
2. **Translates** - Uses Google Translate (free, no API key needed)
3. **Handles Long Text** - Automatically splits long pages into chunks
4. **Creates PDF** - Generates a new PDF with translated text

## Notes

- Google Translate has rate limits, so the script includes delays between requests
- For very large PDFs, translation may take some time
- Translation quality depends on Google Translate (generally very good for common languages)

## Troubleshooting

If you encounter rate limiting:
- The script will automatically retry with delays
- For very large PDFs, you may need to run it multiple times or increase delays

## Free Translation Services Used

- **Google Translate** - Free, no API key required
- Alternative services available: MyMemory, LibreTranslate (can be configured)

# Intelligent Web Scraper

A scalable, intelligent web scraper that automatically detects content types and applies the most appropriate scraping strategy for websites, PDFs, and Google Drive folders.

## Features

- **Intelligent Content Detection**: Automatically detects whether a URL is a website, PDF, or Google Drive folder
- **Multi-Strategy Scraping**: 
  - Simple websites: Fast HTML extraction
  - Complex websites: JavaScript-based card clicking for dynamic content
  - PDFs: Text extraction and chunking
  - Google Drive: Folder parsing and PDF extraction
- **Depth Control**: Configurable recursion depth (default: 1 level)
- **Optimized Performance**: Skips unnecessary JavaScript extraction when HTML extraction is sufficient
- **Clean Output**: Structured JSON output with metadata

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Basic usage
python main.py <team_id> <user_id> <url1> [url2] [url3] ...

# Examples
python main.py team1 user1 https://interviewing.io/blog
python main.py team1 user1 https://quill.co/blog
python main.py team1 user1 https://drive.google.com/drive/folders/...
python main.py team1 user1 https://example.com/document.pdf
```

## Architecture

### Core Components

- **`main.py`**: Main entry point with intelligent routing logic
- **`scraper.py`**: Web scraping with HTML and JavaScript support
- **`pdf_scraper.py`**: PDF text extraction and chunking
- **`google_drive_handler.py`**: Google Drive folder parsing
- **`url_processor.py`**: URL extraction and processing
- **`output_formatter.py`**: JSON output formatting

### Content Type Detection

The scraper automatically detects content types:

1. **Google Drive**: URLs containing `drive.google.com`
2. **PDF**: URLs ending with `.pdf` or serving PDF content
3. **Simple Website**: Individual blog posts and static pages
4. **Complex Website**: Listing pages requiring card clicking

### Performance Optimizations

- **HTML-First Strategy**: Always tries HTML extraction before JavaScript
- **Smart Fallback**: Only uses JavaScript when HTML extraction finds < 5 URLs
- **Depth Limiting**: Configurable recursion depth to prevent infinite crawling
- **Content Filtering**: Filters out navigation, legal, and unrelated pages

## Output Format

```json
{
  "team_id": "team1",
  "user_id": "user1",
  "items": [
    {
      "title": "Article Title",
      "content": "Extracted content...",
      "source_url": "https://example.com/article",
      "user_id": "user1",
      "content_type": "blog",
      "author": "Author Name",
      "date": "2024-01-01",
      "chunk_index": 1,
      "total_chunks": 5
    }
  ]
}
```

## Testing

```bash
# Test PDF scraping
python test_pdf_scraper.py

# Test web scraping
python test_scraper.py
```

## Configuration

Key configuration options in `config.py`:
- `MAX_RETRIES`: Number of retry attempts for failed requests
- `REQUEST_TIMEOUT`: Request timeout in seconds
- `CHUNK_SIZE`: PDF text chunk size
- `CHUNK_OVERLAP`: Overlap between PDF chunks

## Requirements

See `requirements.txt` for the complete list of dependencies, including:
- `aiohttp`: Async HTTP client
- `playwright`: Browser automation
- `PyPDF2`, `pdfplumber`, `PyMuPDF`: PDF processing
- `beautifulsoup4`: HTML parsing
- `lxml`: XML/HTML parser
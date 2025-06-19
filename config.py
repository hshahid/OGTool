"""
Configuration settings for the web scraper.
"""

# Scraping settings
SCRAPING_DELAY = 1.0  # Delay between requests in seconds
MAX_RETRIES = 3  # Maximum number of retry attempts
MAX_PAGES = 1  # Maximum number of pages to process for pagination (link depth limit)
REQUEST_TIMEOUT = 30  # Request timeout in seconds

# Content filtering
MIN_CONTENT_LENGTH = 50  # Minimum content length to consider valid
MIN_TITLE_LENGTH = 10  # Minimum title length
MAX_TITLE_LENGTH = 200  # Maximum title length

# Markdown conversion settings
MARKDOWN_HEADING_STYLE = "ATX"  # Use # style headers
MARKDOWN_BULLETS = "-"  # Use - for bullet points
MARKDOWN_CODE_STYLE = "fenced"  # Use ``` for code blocks

# User agent for requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Content type patterns
CONTENT_TYPE_PATTERNS = {
    'blog': ['blog', 'post', 'article'],
    'podcast_transcript': ['podcast', 'transcript'],
    'linkedin_post': ['linkedin.com'],
    'reddit_comment': ['reddit.com'],
    'book': ['book'],
    'call_transcript': ['call', 'transcript'],
    'other': []
}

# URL patterns to skip
SKIP_URL_PATTERNS = [
    '/tag/',
    '/category/',
    '/author/',
    '/search',
    '/page/',
    '/#',
    'javascript:',
    'mailto:',
    'tel:',
    '.pdf',
    '.jpg',
    '.png',
    '.gif',
    '.css',
    '.js'
]

# Content selectors for different types of content
CONTENT_SELECTORS = [
    'main',
    'article',
    '[class*="content"]',
    '[class*="post"]',
    '[class*="blog"]',
    '.entry-content',
    '.post-content',
    '.article-content',
    'main article',
    'div[role="main"]'
]

# Title selectors
TITLE_SELECTORS = [
    'h1',
    'title',
    '[class*="title"]',
    '[class*="heading"]',
    'h2',
    'h3'
]

# Author selectors
AUTHOR_SELECTORS = [
    '[class*="author"]',
    '[class*="byline"]',
    '.author',
    '.byline',
    '[rel="author"]',
    'meta[name="author"]'
] 
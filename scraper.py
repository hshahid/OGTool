"""
Web scraper that can handle both HTML and JavaScript pages.
Uses multiple strategies for different types of content.
"""

import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from markdownify import markdownify
from typing import Dict, Any, Optional
import re
from urllib.parse import urljoin, urlparse
import time
from config import *


class WebScraper:
    """Main web scraper class that handles both HTML and JavaScript pages."""
    
    def __init__(self, delay: float = SCRAPING_DELAY, max_retries: int = MAX_RETRIES):
        self.delay = delay
        self.max_retries = max_retries
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_page(self, url: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single page and return structured data."""
        try:
            # Try simple HTML scraping first
            content = await self._scrape_html(url)
            
            # If no content found, try JavaScript rendering
            if not content or not content.get('content'):
                content = await self._scrape_javascript(url)
            
            if not content or not content.get('content'):
                print(f"No content found for {url}")
                return None
            
            # Add metadata
            content['source_url'] = url
            content['user_id'] = user_id
            
            # Determine content type
            content['content_type'] = self._determine_content_type(url, content)
            
            # Clean and format content
            content['content'] = self._clean_content(content['content'])
            
            await asyncio.sleep(self.delay)
            return content
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    async def _scrape_html(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape content using simple HTTP requests."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, timeout=REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(html, url)
                    else:
                        print(f"HTTP {response.status} for {url}")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.delay * (attempt + 1))
        
        return None
    
    async def _scrape_javascript(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape content using Playwright for JavaScript-rendered pages."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set user agent to avoid detection
                await page.set_extra_http_headers({
                    'User-Agent': USER_AGENT
                })
                
                await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT * 1000)
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Get the rendered HTML
                html = await page.content()
                await browser.close()
                
                return self._parse_html(html, url)
                
        except Exception as e:
            print(f"JavaScript scraping failed for {url}: {e}")
            return None
    
    def _parse_html(self, html: str, url: str) -> Dict[str, Any]:
        """Parse HTML content and extract structured data."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract title
        title = self._extract_title(soup)
        
        # Extract main content
        content = self._extract_main_content(soup)
        
        # Extract author
        author = self._extract_author(soup)
        
        return {
            'title': title,
            'content': content,
            'author': author
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        for selector in TITLE_SELECTORS:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                title = title_elem.get_text().strip()
                if MIN_TITLE_LENGTH <= len(title) <= MAX_TITLE_LENGTH:
                    return title
        
        return ""
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from the page."""
        for selector in CONTENT_SELECTORS:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Preserve HTML structure for markdown conversion
                html_content = str(content_elem)
                if len(content_elem.get_text().strip()) > MIN_CONTENT_LENGTH:
                    return html_content
        
        # Fallback: get HTML from body
        body = soup.find('body')
        if body:
            return str(body)
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract the author information."""
        for selector in AUTHOR_SELECTORS:
            author_elem = soup.select_one(selector)
            if author_elem:
                if author_elem.name == 'meta':
                    return author_elem.get('content', '')
                else:
                    return author_elem.get_text().strip()
        
        return ""
    
    def _determine_content_type(self, url: str, content: Dict[str, Any]) -> str:
        """Determine the content type based on URL and content."""
        url_lower = url.lower()
        title_lower = content.get('title', '').lower()
        
        for content_type, patterns in CONTENT_TYPE_PATTERNS.items():
            if content_type == 'other':
                continue
            for pattern in patterns:
                if pattern in url_lower or pattern in title_lower:
                    return content_type
        
        return 'other'
    
    def _clean_content(self, content: str) -> str:
        """Clean and format the content."""
        if not content:
            return ""
        
        # If content is already HTML, convert to markdown
        if '<' in content and '>' in content:
            # Convert HTML to markdown with configured settings
            markdown_content = markdownify(
                content, 
                heading_style=MARKDOWN_HEADING_STYLE,
                bullets=MARKDOWN_BULLETS
            )
        else:
            # If it's plain text, just clean it up
            markdown_content = content
        
        # Clean up extra whitespace
        markdown_content = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown_content)
        markdown_content = re.sub(r' +', ' ', markdown_content)
        
        # Remove excessive line breaks
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
        
        # Ensure proper markdown formatting
        markdown_content = self._improve_markdown_formatting(markdown_content)
        
        return markdown_content.strip()
    
    def _improve_markdown_formatting(self, content: str) -> str:
        """Improve markdown formatting for better readability."""
        # Ensure headers have proper spacing
        content = re.sub(r'(\n#+\s+[^\n]+)', r'\n\n\1\n', content)
        
        # Ensure lists have proper spacing
        content = re.sub(r'(\n[-*+]\s+[^\n]+)', r'\n\1', content)
        
        # Ensure paragraphs have proper spacing
        content = re.sub(r'(\n\n[^\n#\-\*\+][^\n]*\n[^\n#\-\*\+][^\n]*)', r'\1\n', content)
        
        # Clean up multiple newlines at the end
        content = re.sub(r'\n+$', '\n\n', content)
        
        return content 
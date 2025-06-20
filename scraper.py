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
from typing import Dict, Any, Optional, List
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
    
    async def scrape_listing_page(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Scrape a listing page and return all individual blog post items."""
        try:
            # Check if this is a listing page
            if self._is_listing_page(url):
                return await self._scrape_listing_page(url, user_id)
            else:
                # If not a listing page, scrape as single page
                item = await self.scrape_page(url, user_id)
                return [item] if item else []
            
        except Exception as e:
            print(f"Error scraping listing page {url}: {e}")
            return []
    
    async def scrape_page(self, url: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Scrape a single page and return structured data."""
        try:
            # Check if this is a listing page
            if self._is_listing_page(url):
                items = await self._scrape_listing_page(url, user_id)
                # For now, return the first item if there are multiple
                # In the future, this could be modified to return all items
                return items[0] if items else None
            
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
    
    def _is_listing_page(self, url: str) -> bool:
        """Determine if a URL is a listing page."""
        url_lower = url.lower()
        
        # Common patterns for listing pages
        listing_patterns = [
            '/blog',
            '/posts',
            '/articles',
            '/topics',
            '/learn',
            '/category',
            '/tag',
            '/archive',
            '/search'
        ]
        
        return any(pattern in url_lower for pattern in listing_patterns)
    
    async def _scrape_listing_page(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Scrape a listing page, simulate clicks on blog cards, and extract full content for each post."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_extra_http_headers({'User-Agent': USER_AGENT})
                await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT * 1000)
                await page.wait_for_timeout(3000)  # Wait for dynamic content

                # Try to remove any overlays that might be blocking clicks
                try:
                    await page.evaluate("""
                        // Remove any gradient overlays that might block clicks
                        document.querySelectorAll('div[class*="gradient"], div[class*="overlay"], div[style*="z-index"]').forEach(el => {
                            if (el.style.zIndex > 1000 || el.className.includes('gradient')) {
                                el.remove();
                            }
                        });
                    """)
                except Exception as e:
                    print(f"    Note: Could not remove overlays: {e}")
                
                # Function to find blog cards
                async def find_blog_cards():
                    all_elements = await page.query_selector_all('a, button, div, article, section')
                    cards = []
                    
                    for i, element in enumerate(all_elements):
                        try:
                            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                            text_content = await element.evaluate('el => el.textContent || ""')
                            class_name = await element.evaluate('el => el.className || ""')
                            
                            # Check if this looks like a blog card
                            is_clickable = (
                                'cursor' in class_name or 
                                'hover' in class_name or
                                'click' in class_name or
                                tag_name in ['a', 'button'] or
                                await element.evaluate('el => el.onclick !== null || el.getAttribute("role") === "button"')
                            )
                            
                            # Check if it has blog-like content
                            has_blog_content = (
                                any(word in text_content.lower() for word in ['blog', 'post', 'article', 'read', 'more']) or
                                any(word in class_name.lower() for word in ['card', 'post', 'article', 'blog'])
                            )
                            
                            if is_clickable and has_blog_content and len(text_content.strip()) > 50:
                                cards.append({
                                    'element': element,
                                    'tag': tag_name,
                                    'text': text_content[:100],
                                    'class': class_name,
                                    'text_key': text_content.strip()[:50]  # For deduplication
                                })
                        except Exception as e:
                            continue
                    
                    # Remove duplicates based on text content
                    seen_texts = set()
                    unique_cards = []
                    for card in cards:
                        if card['text_key'] not in seen_texts:
                            seen_texts.add(card['text_key'])
                            unique_cards.append(card)
                    
                    return unique_cards
                
                # Initial card finding
                card_selectors = await find_blog_cards()
                print(f"Found {len(card_selectors)} unique clickable blog cards:")
                for i, card in enumerate(card_selectors[:5], 1):  # Show first 5
                    print(f"  {i}. {card['tag'].upper()} - {card['text'][:50]}...")
                if len(card_selectors) > 5:
                    print(f"  ... and {len(card_selectors) - 5} more")
                
                print(f"Processing {len(card_selectors)} elements...")
                items = []
                processed_urls = set()  # Track URLs we've already processed
                processed_cards = set()  # Track which cards we've already clicked
                
                i = 0
                while i < len(card_selectors):
                    card = card_selectors[i]
                    
                    # Skip if we've already processed this card
                    card_key = card['text_key']
                    if card_key in processed_cards:
                        print(f"  ⏭ Skipping card {i+1} (already processed)")
                        i += 1
                        continue
                    
                    print(f"  Attempting to click card {i+1}...")
                    
                    try:
                        # Get current URL before click
                        prev_url = page.url
                        
                        # Try to click with multiple strategies
                        click_success = False
                        for attempt in range(3):
                            try:
                                # Strategy 1: Direct click
                                await card['element'].click(timeout=5000)
                                click_success = True
                                break
                            except Exception as e1:
                                try:
                                    # Strategy 2: Click with force
                                    await card['element'].click(force=True, timeout=5000)
                                    click_success = True
                                    break
                                except Exception as e2:
                                    try:
                                        # Strategy 3: Use JavaScript click
                                        await page.evaluate('el => el.click()', card['element'])
                                        click_success = True
                                        break
                                    except Exception as e3:
                                        if attempt == 2:  # Last attempt
                                            print(f"    ✗ All click strategies failed: {e1}, {e2}, {e3}")
                                        else:
                                            await page.wait_for_timeout(1000)
                        
                        if not click_success:
                            print(f"    ✗ Could not click card {i+1}")
                            processed_cards.add(card_key)  # Mark as processed to avoid retrying
                            i += 1  # Move to next card
                            continue
                        
                        # Wait for navigation
                        await page.wait_for_timeout(3000)
                        new_url = page.url
                        
                        print(f"    ✓ Click successful")
                        print(f"    URL before: {prev_url}")
                        print(f"    URL after: {new_url}")
                        
                        # Only extract content if we actually navigated to a different page
                        if new_url != prev_url and '/blog/' in new_url:
                            # Check if we've already processed this URL
                            if new_url in processed_urls:
                                print(f"    ⚠ Already processed this URL, skipping...")
                                processed_cards.add(card_key)  # Mark card as processed
                                # Navigate back and move to next card
                                await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT * 1000)
                                await page.wait_for_timeout(2000)
                                card_selectors = await find_blog_cards()
                                i += 1  # Move to next card
                                continue
                            
                            # Extract the full content and title
                            html = await page.content()
                            data = self._parse_html(html, new_url)
                            if data and data.get('content'):
                                print(f"    ✓ Content extracted: {len(data.get('content', ''))} chars")
                                # Clean and format the content
                                data['content'] = self._clean_content(data['content'])
                                data['source_url'] = new_url
                                data['user_id'] = user_id
                                data['content_type'] = 'blog'
                                data['author'] = data.get('author', '')
                                items.append(data)
                                processed_urls.add(new_url)  # Mark as processed
                                processed_cards.add(card_key)  # Mark card as processed
                            else:
                                print(f"    ✗ No content found after click")
                                processed_cards.add(card_key)  # Mark card as processed
                            
                            # Navigate back to the listing page
                            print(f"    ↶ Navigating back to listing page...")
                            await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT * 1000)
                            await page.wait_for_timeout(2000)
                            
                            # Re-find the elements since we're back on the listing page
                            card_selectors = await find_blog_cards()
                            print(f"    ✓ Back on listing page, {len(card_selectors)} elements available")
                            # Don't reset index - continue from where we left off
                            i += 1
                        else:
                            print(f"    ⚠ No navigation detected or not a blog post URL")
                            processed_cards.add(card_key)  # Mark card as processed
                            i += 1  # Move to next card
                        
                    except Exception as e:
                        print(f"    ✗ Error clicking card {i+1}: {e}")
                        processed_cards.add(card_key)  # Mark card as processed
                        # If there was an error, try to re-find elements in case we're on a different page
                        try:
                            card_selectors = await find_blog_cards()
                            print(f"    ↻ Re-finding elements after error, {len(card_selectors)} available")
                            # Don't reset index - continue from where we left off
                            i += 1
                        except Exception as refind_error:
                            print(f"    ✗ Could not re-find elements: {refind_error}")
                            i += 1  # Move to next card
                        continue
                await browser.close()
                return items
        except Exception as e:
            print(f"Error scraping listing page {url}: {e}")
            return []

    async def _scrape_full_blog_post(self, url: str, user_id: str) -> dict:
        """Visit a blog post URL and extract the full content and title."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_extra_http_headers({'User-Agent': USER_AGENT})
                await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT * 1000)
                await page.wait_for_timeout(2000)
                html = await page.content()
                await browser.close()
                data = self._parse_html(html, url)
                if not data or not data.get('content'):
                    return None
                # Clean and format the content
                data['content'] = self._clean_content(data['content'])
                data['source_url'] = url
                data['user_id'] = user_id
                data['content_type'] = 'blog'
                data['author'] = data.get('author', '')
                return data
        except Exception as e:
            print(f"Error scraping blog post {url}: {e}")
            return None 
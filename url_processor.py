"""
URL processor that handles pagination and extracts individual page URLs.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from typing import List, Set
import re
from config import *


class URLProcessor:
    """Processes URLs to extract individual page URLs, handling pagination."""
    
    def __init__(self, max_pages: int = MAX_PAGES):
        self.max_pages = max_pages
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def process_url(self, url: str) -> List[str]:
        """Process a URL and return a list of individual page URLs."""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Check if it's a listing page or individual page
        if self._is_listing_page(url):
            return await self._extract_from_listing_page(url)
        else:
            return [url]
    
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
    
    async def _extract_from_listing_page(self, url: str) -> List[str]:
        """Extract individual page URLs from a listing page."""
        urls = set()
        
        # Try HTML first
        print(f"Debug: Trying HTML extraction for {url}")
        html_urls = await self._extract_urls_html(url)
        print(f"Debug: HTML extraction found {len(html_urls)} URLs")
        urls.update(html_urls)
        
        # Only try JavaScript if HTML extraction found very few URLs (less than 5)
        # This avoids unnecessary JavaScript extraction when HTML already works
        if len(html_urls) < 5:
            print(f"Debug: HTML extraction found few URLs, trying JavaScript extraction for {url}")
            js_urls = await self._extract_urls_javascript(url)
            print(f"Debug: JavaScript extraction found {len(js_urls)} URLs")
            urls.update(js_urls)
        else:
            print(f"Debug: HTML extraction found sufficient URLs ({len(html_urls)}), skipping JavaScript extraction")
        
        # Handle pagination
        paginated_urls = await self._handle_pagination(url, urls)
        urls.update(paginated_urls)
        
        return list(urls)
    
    async def _extract_urls_html(self, url: str) -> Set[str]:
        """Extract URLs using simple HTTP requests."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(url, timeout=REQUEST_TIMEOUT) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_urls_from_html(html, url)
        except Exception as e:
            print(f"Error extracting URLs from {url}: {e}")
        
        return set()
    
    async def _extract_urls_javascript(self, url: str) -> Set[str]:
        """Extract URLs using Playwright for JavaScript-rendered pages."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.set_extra_http_headers({'User-Agent': USER_AGENT})
                await page.goto(url, wait_until='networkidle', timeout=REQUEST_TIMEOUT * 1000)
                await page.wait_for_selector('a[href]')  # Wait for links to load
                
                # Wait a bit longer for dynamic content
                await page.wait_for_timeout(3000)

                # Debug: Check for different types of clickable elements
                print(f"Debug: Checking for blog post links...")
                
                # Look for elements that might be blog post links
                blog_links = await page.eval_on_selector_all(
                    'a, [role="link"], [class*="post"], [class*="blog"], [class*="article"]',
                    '''
                    elements => elements.map(el => ({
                        tag: el.tagName,
                        href: el.href || null,
                        text: el.textContent?.trim() || '',
                        className: el.className || '',
                        role: el.getAttribute('role') || null
                    }))
                    '''
                )
                
                print(f"Debug: Found {len(blog_links)} potential link elements:")
                for i, link in enumerate(blog_links[:10], 1):
                    print(f"  {i}. {link['tag']} - href: {link['href']} - text: {link['text'][:50]}... - class: {link['className'][:30]}...")
                
                # Also check for any elements with blog-related text
                blog_text_elements = await page.eval_on_selector_all(
                    '*',
                    '''
                    elements => elements
                        .filter(el => {
                            const text = el.textContent?.trim() || '';
                            return text.length > 10 && text.length < 200 && 
                                   (text.includes('Read more') || text.includes('blog') || text.includes('post'));
                        })
                        .map(el => ({
                            tag: el.tagName,
                            text: el.textContent?.trim() || '',
                            className: el.className || '',
                            parentTag: el.parentElement?.tagName || null
                        }))
                    '''
                )
                
                print(f"Debug: Found {len(blog_text_elements)} elements with blog-related text:")
                for i, elem in enumerate(blog_text_elements[:5], 1):
                    print(f"  {i}. {elem['tag']} - text: {elem['text'][:50]}... - class: {elem['className'][:30]}...")
                
                # Extract all hrefs from anchor tags
                hrefs = await page.eval_on_selector_all(
                    'a[href]',
                    'elements => elements.map(el => el.href)'
                )
                await browser.close()

                # Debug: Show all hrefs found
                print(f"Debug: Found {len(hrefs)} total hrefs from {url}")
                for i, href in enumerate(hrefs[:10], 1):  # Show first 10
                    print(f"  {i}. {href}")
                if len(hrefs) > 10:
                    print(f"  ... and {len(hrefs) - 10} more")

                # Filter and normalize URLs as needed
                valid_urls = set()
                for href in hrefs:
                    if self._is_valid_content_url(href, url):
                        valid_urls.add(href)
                
                print(f"Debug: After filtering, {len(valid_urls)} valid URLs remain")
                return valid_urls
        except Exception as e:
            print(f"JavaScript URL extraction failed for {url}: {e}")
            return set()
    
    def _parse_urls_from_html(self, html: str, base_url: str) -> Set[str]:
        """Parse URLs from HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        urls = set()
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Filter URLs based on domain and content
            if self._is_valid_content_url(absolute_url, base_url):
                urls.add(absolute_url)
        
        return urls
    
    def _is_valid_content_url(self, url: str, base_url: str) -> bool:
        """Check if a URL is a valid content URL."""
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
        
        # Must be same domain
        if parsed_url.netloc != parsed_base.netloc:
            return False
        
        # Skip common non-content URLs
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in SKIP_URL_PATTERNS):
            return False
        
        # Must have some path (not just domain)
        if not parsed_url.path or parsed_url.path == '/':
            return False
        
        return True
    
    async def _handle_pagination(self, base_url: str, existing_urls: Set[str]) -> Set[str]:
        """Handle pagination to find more URLs."""
        urls = set()
        page = 1
        
        while page <= self.max_pages:
            # Try different pagination patterns
            pagination_urls = await self._try_pagination_patterns(base_url, page)
            
            if not pagination_urls:
                break
            
            # Extract URLs from this page
            for pagination_url in pagination_urls:
                page_urls = await self._extract_urls_html(pagination_url)
                urls.update(page_urls)
            
            # If we didn't find any new URLs, stop
            if not urls - existing_urls:
                break
            
            page += 1
        
        return urls
    
    async def _try_pagination_patterns(self, base_url: str, page: int) -> List[str]:
        """Try different pagination URL patterns."""
        patterns = [
            f"{base_url}?page={page}",
            f"{base_url}?p={page}",
            f"{base_url}/page/{page}",
            f"{base_url}/p/{page}",
            f"{base_url}?pg={page}",
            f"{base_url}?pagination={page}"
        ]
        
        valid_urls = []
        for pattern in patterns:
            if await self._url_exists(pattern):
                valid_urls.append(pattern)
        
        return valid_urls
    
    async def _url_exists(self, url: str) -> bool:
        """Check if a URL exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.head(url, timeout=10) as response:
                return response.status == 200
        except:
            return False 
import requests
import asyncio
import time
import random
from urllib.parse import urljoin, urlparse
from typing import List, Set
from bs4 import BeautifulSoup
from .base import BaseScraper, ContentItem

class WebScraper(BaseScraper):
    """Simple, scalable web scraper that works for any website"""
    
    def __init__(self, team_id: str, max_pages: int = 50, delay: float = 1.0):
        super().__init__(team_id)
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.session = requests.Session()
        
        # Set realistic headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def can_handle(self, source: str) -> bool:
        """Check if this is a web URL"""
        try:
            result = urlparse(source)
            return bool(result.scheme and result.netloc)
        except:
            return False
    
    def get_page(self, url: str) -> BeautifulSoup:
        """Get and parse a single page"""
        try:
            # Add delay to be respectful
            time.sleep(random.uniform(self.delay, self.delay * 2))
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page title"""
        # Try different title selectors
        title_selectors = [
            'h1',
            '.title', '[class*="title"]',
            '.post-title', '[class*="post-title"]',
            '.article-title', '[class*="article-title"]',
            'title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = self.clean_text(title_elem.get_text())
                if title and len(title) > 5:
                    return title
        
        # Fallback to page title
        title_tag = soup.find('title')
        if title_tag:
            return self.clean_text(title_tag.get_text())
        
        # Last resort: use URL
        return urlparse(url).path.strip('/').replace('-', ' ').title()
    
    def extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from page"""
        # Remove unwanted elements
        for unwanted in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()
        
        # Try to find main content area
        content_selectors = [
            'main',
            'article',
            '.content', '[class*="content"]',
            '.post-content', '[class*="post-content"]',
            '.article-content', '[class*="article-content"]',
            '.entry-content', '[class*="entry-content"]',
            '#content', '#main'
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        # If no main content area found, use body
        if not content_elem:
            content_elem = soup.find('body')
        
        if not content_elem:
            return ""
        
        # Extract text content
        content_parts = []
        
        # Get all text elements
        for elem in content_elem.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote']):
            text = self.clean_text(elem.get_text())
            if text and len(text) > 10:  # Only include substantial text
                content_parts.append(text)
        
        return '\n\n'.join(content_parts)
    
    def find_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Find all links on the page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include links from same domain
            if urlparse(full_url).netloc == base_domain:
                links.append(full_url)
        
        return list(set(links))
    
    def should_scrape_url(self, url: str, base_domain: str) -> bool:
        """Determine if URL should be scraped"""
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != base_domain:
            return False
        
        # Skip common non-content URLs
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/page/',
            '/search', '/login', '/signup', '/contact',
            '/about', '/privacy', '/terms', '/sitemap',
            '.pdf', '.jpg', '.png', '.gif', '.css', '.js'
        ]
        
        for pattern in skip_patterns:
            if pattern in url.lower():
                return False
        
        return True
    
    def scrape(self, source: str) -> List[ContentItem]:
        """Scrape content from the source URL and linked pages"""
        base_domain = urlparse(source).netloc
        urls_to_scrape = [source]
        items = []
        
        while urls_to_scrape and len(self.visited_urls) < self.max_pages:
            url = urls_to_scrape.pop(0)
            
            if url in self.visited_urls:
                continue
            
            self.visited_urls.add(url)
            print(f"Scraping: {url}")
            
            # Get page content
            soup = self.get_page(url)
            if not soup:
                continue
            
            # Extract content
            title = self.extract_title(soup, url)
            content = self.extract_content(soup)
            author = self.extract_author(soup, url)
            
            # Only add if we have meaningful content
            if content and len(content) > 100:
                content_type = self.determine_content_type(url, title)
                
                items.append(ContentItem(
                    title=title,
                    content=content,
                    content_type=content_type,
                    source_url=url,
                    author=author
                ))
            
            # Find more links to scrape
            if len(self.visited_urls) < self.max_pages:
                new_links = self.find_links(soup, url, base_domain)
                for link in new_links:
                    if (link not in self.visited_urls and 
                        link not in urls_to_scrape and 
                        self.should_scrape_url(link, base_domain)):
                        urls_to_scrape.append(link)
        
        return items 
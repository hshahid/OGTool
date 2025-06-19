import requests
import asyncio
import aiohttp
import time
import random
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict, Optional
from bs4 import BeautifulSoup
from .base import BaseScraper, ContentItem
import concurrent.futures
from functools import lru_cache

class WebScraper(BaseScraper):
    """High-performance web scraper with async support and optimizations"""
    
    def __init__(self, team_id: str, max_pages: int = 50, delay: float = 1.0, 
                 max_concurrent: int = 10, use_async: bool = True):
        super().__init__(team_id)
        self.max_pages = max_pages
        self.delay = delay
        self.max_concurrent = max_concurrent
        self.use_async = use_async
        self.visited_urls: Set[str] = set()
        self.content_cache: Dict[str, Optional[BeautifulSoup]] = {}
        
        # Optimized session with connection pooling
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=max_concurrent,
            pool_maxsize=max_concurrent,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
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
    
    @lru_cache(maxsize=1000)
    def _cached_get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Cached version of get_page for repeated requests"""
        return self.get_page(url)
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Get and parse a single page with optimized error handling"""
        if url in self.content_cache:
            return self.content_cache[url]
        
        try:
            # Add delay to be respectful
            time.sleep(random.uniform(self.delay * 0.5, self.delay))
            
            response = self.session.get(url, timeout=15)  # Reduced timeout
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            self.content_cache[url] = soup
            return soup
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            self.content_cache[url] = None
            return None
    
    async def get_page_async(self, session: aiohttp.ClientSession, url: str) -> Optional[BeautifulSoup]:
        """Async version of get_page for concurrent requests"""
        if url in self.content_cache:
            return self.content_cache[url]
        
        try:
            # Add delay to be respectful
            await asyncio.sleep(random.uniform(self.delay * 0.5, self.delay))
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                content = await response.read()
                
                soup = BeautifulSoup(content, 'html.parser')
                self.content_cache[url] = soup
                return soup
                
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            self.content_cache[url] = None
            return None
    
    def extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract page title with optimized selectors"""
        if not soup:
            return urlparse(url).path.strip('/').replace('-', ' ').title()
        
        # Optimized title extraction with single query
        title_candidates = []
        
        # Try h1 first (most common for main titles)
        h1 = soup.find('h1')
        if h1:
            title = self.clean_text(h1.get_text())
            if title and len(title) > 5:
                title_candidates.append((title, 10))  # High priority
        
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            title = self.clean_text(title_tag.get_text())
            if title and len(title) > 5:
                title_candidates.append((title, 8))  # Medium priority
        
        # Try other selectors with lower priority
        for selector in ['.title', '.post-title', '.article-title']:
            elem = soup.select_one(selector)
            if elem:
                title = self.clean_text(elem.get_text())
                if title and len(title) > 5:
                    title_candidates.append((title, 5))
        
        # Return the highest priority title
        if title_candidates:
            title_candidates.sort(key=lambda x: x[1], reverse=True)
            return title_candidates[0][0]
        
        # Fallback to URL
        return urlparse(url).path.strip('/').replace('-', ' ').title()
    
    def extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content with optimized parsing"""
        if not soup:
            return ""
        
        # Remove unwanted elements more efficiently
        unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']
        for tag in soup.find_all(unwanted_tags):
            tag.decompose()
        
        # Try to find main content area with optimized selectors
        content_selectors = [
            'main', 'article', '.content', '.post-content', 
            '.article-content', '.entry-content', '#content', '#main'
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
        
        # Extract text content more efficiently
        content_parts = []
        text_elements = content_elem.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote'])
        
        for elem in text_elements:
            text = self.clean_text(elem.get_text())
            if text and len(text) > 10:  # Only include substantial text
                content_parts.append(text)
        
        return '\n\n'.join(content_parts)
    
    def find_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """Find all links on the page with optimized filtering"""
        if not soup:
            return []
        
        links = set()  # Use set for deduplication
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include links from same domain
            if urlparse(full_url).netloc == base_domain:
                links.add(full_url)
        
        return list(links)
    
    def should_scrape_url(self, url: str, base_domain: str) -> bool:
        """Determine if URL should be scraped with optimized patterns"""
        parsed = urlparse(url)
        
        # Must be same domain
        if parsed.netloc != base_domain:
            return False
        
        # Skip common non-content URLs with optimized patterns
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/page/',
            '/search', '/login', '/signup', '/contact',
            '/about', '/privacy', '/terms', '/sitemap',
            '.pdf', '.jpg', '.png', '.gif', '.css', '.js'
        ]
        
        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in skip_patterns)
    
    async def scrape_async(self, source: str) -> List[ContentItem]:
        """Async version of scrape for better performance"""
        base_domain = urlparse(source).netloc
        urls_to_scrape = [source]
        items = []
        
        # Create async session with optimized settings
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=self.max_concurrent,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.session.headers
        ) as session:
            
            while urls_to_scrape and len(self.visited_urls) < self.max_pages:
                # Process URLs in batches for better concurrency
                batch_size = min(self.max_concurrent, len(urls_to_scrape), 
                               self.max_pages - len(self.visited_urls))
                batch_urls = urls_to_scrape[:batch_size]
                urls_to_scrape = urls_to_scrape[batch_size:]
                
                # Filter out already visited URLs
                new_urls = [url for url in batch_urls if url not in self.visited_urls]
                
                if not new_urls:
                    continue
                
                # Mark URLs as visited
                for url in new_urls:
                    self.visited_urls.add(url)
                
                print(f"Scraping batch of {len(new_urls)} URLs...")
                
                # Fetch pages concurrently
                tasks = [self.get_page_async(session, url) for url in new_urls]
                soups = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for url, soup in zip(new_urls, soups):
                    if isinstance(soup, Exception) or not soup:
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
    
    def scrape(self, source: str) -> List[ContentItem]:
        """Scrape content from the source URL and linked pages"""
        if self.use_async:
            # Use async version for better performance
            return asyncio.run(self.scrape_async(source))
        else:
            # Fallback to synchronous version
            return self._scrape_sync(source)
    
    def _scrape_sync(self, source: str) -> List[ContentItem]:
        """Synchronous version of scrape (original implementation)"""
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
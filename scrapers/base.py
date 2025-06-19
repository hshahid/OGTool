from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict
from urllib.parse import urlparse
import re

@dataclass
class ContentItem:
    """Represents a single piece of content"""
    title: str
    content: str
    content_type: str
    source_url: str
    author: str = ""
    user_id: str = ""

class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, team_id: str):
        self.team_id = team_id
    
    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Check if this scraper can handle the given source"""
        pass
    
    @abstractmethod
    def scrape(self, source: str) -> List[ContentItem]:
        """Scrape content from the source and return ContentItems"""
        pass
    
    def determine_content_type(self, url: str, title: str = "") -> str:
        """Determine content type based on URL and title"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        # Blog posts
        if any(term in url_lower for term in ['/blog', '/post', '/article']):
            return "blog"
        
        # Company guides
        if any(term in url_lower for term in ['/guide', '/company', '/hiring']):
            return "company_guide"
        
        # Interview guides
        if any(term in url_lower for term in ['/interview', '/learn']):
            return "interview_guide"
        
        # Books
        if any(term in url_lower for term in ['.pdf', '/book']):
            return "book"
        
        # Default to blog for most web content
        return "blog"
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common unwanted patterns
        text = re.sub(r'^\s*[•\-*]\s*', '', text)  # Remove bullet points at start
        text = re.sub(r'\s*[•\-*]\s*$', '', text)  # Remove bullet points at end
        
        return text
    
    def extract_author(self, soup, url: str) -> str:
        """Extract author information from page"""
        # Common author selectors
        author_selectors = [
            '.author', '[class*="author"]', '[class*="byline"]',
            '[rel="author"]', '.byline', '.post-author'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                return self.clean_text(author_elem.get_text())
        
        return ""
    
    def to_json(self, items: List[ContentItem]) -> Dict:
        """Convert items to JSON format"""
        return {
            "team_id": self.team_id,
            "items": [
                {
                    "title": item.title,
                    "content": item.content,
                    "content_type": item.content_type,
                    "source_url": item.source_url,
                    "author": item.author,
                    "user_id": item.user_id
                }
                for item in items
            ]
        } 
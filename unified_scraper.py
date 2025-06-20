"""
Unified scraper that can handle both websites and PDFs.
Automatically detects content type and routes to appropriate scraper.
"""

import asyncio
from typing import Dict, Any, Optional, List
from scraper import WebScraper
from pdf_scraper import PDFScraper
from google_drive_handler import GoogleDriveHandler


class UnifiedScraper:
    """Unified scraper that handles both websites and PDFs."""
    
    def __init__(self, web_delay: float = 1.0, pdf_chunk_size: int = 1000, pdf_chunk_overlap: int = 200):
        self.web_scraper = WebScraper(delay=web_delay)
        self.pdf_scraper = PDFScraper(chunk_size=pdf_chunk_size, chunk_overlap=pdf_chunk_overlap)
        self.google_drive_handler = GoogleDriveHandler()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.web_scraper.__aenter__()
        await self.pdf_scraper.__aenter__()
        await self.google_drive_handler.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.web_scraper.__aexit__(exc_type, exc_val, exc_tb)
        await self.pdf_scraper.__aexit__(exc_type, exc_val, exc_tb)
        await self.google_drive_handler.__aexit__(exc_type, exc_val, exc_tb)
    
    def is_pdf_url(self, url: str) -> bool:
        """Check if the URL points to a PDF file."""
        return self.pdf_scraper.is_pdf_url(url)
    
    async def scrape_url(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Scrape a URL and return structured data, handling both websites and PDFs."""
        try:
            # Handle Google Drive URLs first
            if self.google_drive_handler.is_google_drive_url(url):
                print(f"Processing Google Drive URL: {url}")
                pdf_urls = await self.google_drive_handler.extract_pdf_urls(url)
                
                all_items = []
                for pdf_url in pdf_urls:
                    if pdf_url != url:  # Skip if it's the same URL
                        items = await self.pdf_scraper.scrape_pdf(pdf_url, user_id)
                        all_items.extend(items)
                    else:
                        # If it's a folder URL, we'll need to handle it differently
                        print(f"Google Drive folder URL detected: {url}")
                        # For now, we'll try to scrape it as a PDF (might fail)
                        items = await self.pdf_scraper.scrape_pdf(url, user_id)
                        all_items.extend(items)
                
                return all_items
            
            # Check if this is a PDF URL
            elif self.is_pdf_url(url):
                print(f"Detected PDF URL: {url}")
                return await self.pdf_scraper.scrape_pdf(url, user_id)
            else:
                print(f"Detected website URL: {url}")
                # For websites, check if it's a listing page
                if self.web_scraper._is_listing_page(url):
                    return await self.web_scraper.scrape_listing_page(url, user_id)
                else:
                    # Single page
                    item = await self.web_scraper.scrape_page(url, user_id)
                    return [item] if item else []
                    
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
    
    async def scrape_multiple_urls(self, urls: List[str], user_id: str) -> List[Dict[str, Any]]:
        """Scrape multiple URLs and return all items."""
        all_items = []
        
        for i, url in enumerate(urls, 1):
            print(f"Processing {i}/{len(urls)}: {url}")
            try:
                items = await self.scrape_url(url, user_id)
                all_items.extend(items)
                print(f"Found {len(items)} items from {url}")
            except Exception as e:
                print(f"Error processing {url}: {e}")
        
        return all_items 
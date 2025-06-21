#!/usr/bin/env python3
"""
Main entry point for the intelligent unified scraper.
Takes team_id, user_id, and URLs as input and orchestrates the scraping process.
Automatically detects content type and applies the most appropriate scraping strategy.
"""

import asyncio
import json
import sys
from typing import List, Dict, Any
from url_processor import URLProcessor
from output_formatter import OutputFormatter
from scraper import WebScraper
from pdf_scraper import PDFScraper
from google_drive_handler import GoogleDriveHandler


class IntelligentScraper:
    """Intelligent scraper that automatically detects content type and applies the best strategy."""
    
    def __init__(self):
        self.web_scraper = WebScraper()
        self.pdf_scraper = PDFScraper()
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
    
    def detect_content_type(self, url: str) -> str:
        """Detect the type of content at the URL."""
        url_lower = url.lower()
        
        # Step 1: Check if it's a Google Drive URL
        if self.google_drive_handler.is_google_drive_url(url):
            return "google_drive"
        
        # Step 2: Check if it's a PDF
        if self.pdf_scraper.is_pdf_url(url):
            return "pdf"
        
        # Step 3: Check if it's an individual blog post (should use simple scraping)
        # Look for patterns that indicate individual blog posts
        if any(pattern in url_lower for pattern in [
            '/blog/', '/post/', '/article/', 
            '/202', '/2023', '/2024', '/2025',
            '/guides/', '/questions/', '/mocks/'
        ]):
            return "simple_website"
        
        # Step 4: Check if it's a listing page (generic detection)
        if self.web_scraper._is_listing_page(url):
            return "complex_website"
        
        # Default: treat as simple website
        return "simple_website"
    
    async def scrape_url(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Scrape a URL using the most appropriate strategy."""
        content_type = self.detect_content_type(url)
        print(f"🔍 Detected content type: {content_type} for {url}")
        
        try:
            if content_type == "google_drive":
                print(f"📁 Processing Google Drive URL...")
                return await self._scrape_google_drive(url, user_id)
            
            elif content_type == "pdf":
                print(f"📄 Processing PDF...")
                return await self.pdf_scraper.scrape_pdf(url, user_id)
            
            elif content_type == "complex_website":
                print(f"🎯 Processing complex website (with card clicking)...")
                return await self._scrape_complex_website(url, user_id)
            
            else:
                # For simple websites, use simple scraping directly
                print(f"🌐 Processing simple website...")
                return await self._scrape_simple_website(url, user_id)
                
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            return []
    
    async def _scrape_google_drive(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Handle Google Drive URLs."""
        pdf_urls = await self.google_drive_handler.extract_pdf_urls(url)
        
        all_items = []
        for pdf_url in pdf_urls:
            if pdf_url != url:  # Skip if it's the same URL
                items = await self.pdf_scraper.scrape_pdf(pdf_url, user_id)
                all_items.extend(items)
        
        return all_items
    
    async def _scrape_simple_website(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Handle simple websites with basic HTML scraping."""
        try:
            # Always use simple HTML scraping for simple websites
            content = await self.web_scraper._scrape_html(url)
            
            if not content or not content.get('content'):
                print(f"⚠️ No content found with simple scraping, trying JavaScript...")
                # Fallback to JavaScript if simple scraping fails
                content = await self.web_scraper._scrape_javascript(url)
            
            if not content or not content.get('content'):
                print(f"❌ No content found for {url}")
                return []
            
            # Add metadata
            content['source_url'] = url
            content['user_id'] = user_id
            content['content_type'] = self._determine_content_type(url, content)
            content['content'] = self.web_scraper._clean_content(content['content'])
            
            return [content]
            
        except Exception as e:
            print(f"❌ Error scraping simple website {url}: {e}")
            return []
    
    def _determine_content_type(self, url: str, content: Dict[str, Any]) -> str:
        """Determine the content type based on URL and content."""
        url_lower = url.lower()
        content_lower = content.get('content', '').lower()
        
        # Check for blog indicators
        if any(word in url_lower for word in ['/blog', '/posts', '/articles']):
            return 'blog'
        
        # Check content for blog-like content
        if any(word in content_lower for word in ['blog', 'post', 'article', 'interview']):
            return 'blog'
        
        # Default
        return 'webpage'
    
    async def _scrape_complex_website(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Handle complex websites with card clicking logic."""
        return await self.web_scraper.scrape_listing_page(url, user_id)
    
    async def scrape_multiple_urls(self, urls: List[str], user_id: str) -> List[Dict[str, Any]]:
        """Scrape multiple URLs using intelligent detection."""
        all_items = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n📋 Processing {i}/{len(urls)}: {url}")
            try:
                items = await self.scrape_url(url, user_id)
                all_items.extend(items)
                print(f"✅ Found {len(items)} items from {url}")
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
        
        return all_items


async def main():
    """Main function to orchestrate the intelligent scraping process."""
    if len(sys.argv) < 4:
        print("🚀 Intelligent Web Scraper")
        print("Usage: python main.py <team_id> <user_id> <url1> [url2] [url3] ...")
        print("\nExamples:")
        print("  python main.py team1 user1 https://interviewing.io/blog")
        print("  python main.py team1 user1 https://quill.co/blog")
        print("  python main.py team1 user1 https://drive.google.com/drive/folders/...")
        print("  python main.py team1 user1 https://example.com/document.pdf")
        sys.exit(1)
    
    team_id = sys.argv[1]
    user_id = sys.argv[2]
    urls = sys.argv[3:]
    
    print(f"🚀 Starting intelligent scrape for team: {team_id}, user: {user_id}")
    print(f"📊 URLs to process: {len(urls)}")
    
    # Initialize components
    url_processor = URLProcessor(max_pages=1)  # Limit to 1 page deep
    scraper = IntelligentScraper()
    formatter = OutputFormatter()
    
    # Process URLs to get individual page URLs
    all_page_urls = []
    for url in urls:
        print(f"🔗 Processing URL: {url}")
        page_urls = await url_processor.process_url(url)
        all_page_urls.extend(page_urls)
        print(f"📄 Found {len(page_urls)} individual pages")
    
    print(f"📋 Total pages to scrape: {len(all_page_urls)}")
    
    # Scrape all pages using intelligent scraper
    async with scraper:
        scraped_items = await scraper.scrape_multiple_urls(all_page_urls, user_id)
    
    # Format output
    output = formatter.format_output(team_id, scraped_items)
    
    # Save to file
    output_file = f"scraped_data_{team_id}_{user_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Scraping completed!")
    print(f"📊 Total items found: {len(scraped_items)}")
    print(f"💾 Output saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
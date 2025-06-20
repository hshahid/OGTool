#!/usr/bin/env python3
"""
Test script for PDF scraping functionality.
"""

import asyncio
import json
from unified_scraper import UnifiedScraper


async def test_pdf_scraping():
    """Test PDF scraping with the provided Google Drive URL."""
    
    # Test URL from the assignment
    test_url = "https://drive.google.com/drive/folders/1AdUu4jh6DGwmCxfgnDQEMWWyo6_whPHJ"
    
    print(f"Testing PDF scraping with URL: {test_url}")
    
    # Initialize unified scraper
    async with UnifiedScraper() as scraper:
        # Test URL detection
        is_pdf = scraper.is_pdf_url(test_url)
        is_gdrive = scraper.google_drive_handler.is_google_drive_url(test_url)
        
        print(f"Is PDF URL: {is_pdf}")
        print(f"Is Google Drive URL: {is_gdrive}")
        
        # Scrape the URL
        items = await scraper.scrape_url(test_url, "test_user")
        
        print(f"Found {len(items)} items")
        
        # Save results
        output = {
            "test_url": test_url,
            "items": items
        }
        
        with open("test_pdf_output.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("Results saved to test_pdf_output.json")
        
        # Print summary
        for i, item in enumerate(items):
            print(f"\nItem {i+1}:")
            print(f"  Title: {item.get('title', 'N/A')}")
            print(f"  Content Type: {item.get('content_type', 'N/A')}")
            print(f"  Content Length: {len(item.get('content', ''))}")
            print(f"  Chunk: {item.get('chunk_index', 'N/A')}/{item.get('total_chunks', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(test_pdf_scraping()) 
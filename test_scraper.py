#!/usr/bin/env python3
"""
Test script to verify the web scraper functionality.
"""

import asyncio
import json
from scraper import WebScraper
from url_processor import URLProcessor
from output_formatter import OutputFormatter


async def test_scraper():
    """Test the scraper with a simple example."""
    print("Testing web scraper...")
    
    # Test URL (a simple blog post)
    test_url = "https://quill.co/blog"
    
    # Initialize components with link depth limit of 1
    url_processor = URLProcessor(max_pages=1)  # Limit to 1 page deep
    scraper = WebScraper()
    formatter = OutputFormatter()
    
    print(f"Processing URL: {test_url}")
    print(f"Link depth limit: 1 page")
    
    # Process URL to get individual pages
    page_urls = await url_processor.process_url(test_url)
    print(f"Found {len(page_urls)} individual pages")
    
    # Limit to first 3 pages for testing
    test_urls = page_urls
    
    # Scrape pages
    scraped_items = []
    for i, url in enumerate(test_urls, 1):
        print(f"Scraping {i}/{len(test_urls)}: {url}")
        try:
            item = await scraper.scrape_page(url, "test_user")
            if item:
                scraped_items.append(item)
                print(f"  ✓ Success: {item.get('title', 'No title')[:50]}...")
            else:
                print(f"  ✗ No content found")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Format output
    output = formatter.format_output("test_team", scraped_items)
    
    # Save test results
    with open("test_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nTest completed!")
    print(f"Successfully scraped {len(scraped_items)} items")
    print(f"Output saved to: test_output.json")
    
    # Show sample output
    if scraped_items:
        print(f"\nSample item:")
        sample = scraped_items[0]
        print(f"  Title: {sample.get('title', 'No title')}")
        print(f"  Content type: {sample.get('content_type', 'unknown')}")
        print(f"  Content length: {len(sample.get('content', ''))} characters")
        print(f"  Author: {sample.get('author', 'Unknown')}")


if __name__ == "__main__":
    asyncio.run(test_scraper()) 
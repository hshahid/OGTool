#!/usr/bin/env python3
"""
Main entry point for the unified scraper.
Takes team_id, user_id, and URLs as input and orchestrates the scraping process.
Handles both websites and PDFs automatically.
"""

import asyncio
import json
import sys
from typing import List, Dict, Any
from unified_scraper import UnifiedScraper
from url_processor import URLProcessor
from output_formatter import OutputFormatter


async def main():
    """Main function to orchestrate the scraping process."""
    if len(sys.argv) < 4:
        print("Usage: python main.py <team_id> <user_id> <url1> [url2] [url3] ...")
        sys.exit(1)
    
    team_id = sys.argv[1]
    user_id = sys.argv[2]
    urls = sys.argv[3:]
    
    print(f"Starting unified scrape for team: {team_id}, user: {user_id}")
    print(f"URLs to process: {len(urls)}")
    
    # Initialize components
    url_processor = URLProcessor(max_pages=1)  # Limit to 1 page deep
    scraper = UnifiedScraper()
    formatter = OutputFormatter()
    
    # Process URLs to get individual page URLs
    all_page_urls = []
    for url in urls:
        print(f"Processing URL: {url}")
        page_urls = await url_processor.process_url(url)
        all_page_urls.extend(page_urls)
        print(f"Found {len(page_urls)} individual pages")
    
    print(f"Total pages to scrape: {len(all_page_urls)}")
    
    # Scrape all pages using unified scraper
    async with scraper:
        scraped_items = await scraper.scrape_multiple_urls(all_page_urls, user_id)
    
    # Format output
    output = formatter.format_output(team_id, scraped_items)
    
    # Save to file
    output_file = f"scraped_data_{team_id}_{user_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Scraping completed! Found {len(scraped_items)} items")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Example script demonstrating how to use the web scraper.
"""

import asyncio
import json
from scraper import WebScraper
from url_processor import URLProcessor
from output_formatter import OutputFormatter


async def scrape_example():
    """Example of scraping the provided sample URLs."""
    
    # Sample URLs from the requirements
    sample_urls = [
        "https://interviewing.io/blog",
        "https://interviewing.io/topics#companies", 
        "https://interviewing.io/learn#interview-guides",
        "https://nilmamano.com/blog/category/dsa-"
    ]
    
    # Configuration
    team_id = "example_team"
    user_id = "example_user"
    
    print("Starting example scrape...")
    print(f"Team ID: {team_id}")
    print(f"User ID: {user_id}")
    print(f"URLs to process: {len(sample_urls)}")
    print("-" * 50)
    
    # Initialize components
    url_processor = URLProcessor(max_pages=1)  # Limit to 1 page deep
    scraper = WebScraper()
    formatter = OutputFormatter()
    
    all_items = []
    
    for i, url in enumerate(sample_urls, 1):
        print(f"\n[{i}/{len(sample_urls)}] Processing: {url}")
        
        try:
            # Get individual page URLs
            page_urls = await url_processor.process_url(url)
            print(f"  Found {len(page_urls)} individual pages")
            
            # Limit to first 5 pages per source for demo
            demo_urls = page_urls[:5]
            
            # Scrape each page
            for j, page_url in enumerate(demo_urls, 1):
                print(f"    Scraping {j}/{len(demo_urls)}: {page_url}")
                
                try:
                    item = await scraper.scrape_page(page_url, user_id)
                    if item:
                        all_items.append(item)
                        print(f"      ✓ {item.get('title', 'No title')[:60]}...")
                    else:
                        print(f"      ✗ No content found")
                except Exception as e:
                    print(f"      ✗ Error: {e}")
                    
        except Exception as e:
            print(f"  ✗ Error processing {url}: {e}")
    
    # Format and save output
    output = formatter.format_output(team_id, all_items)
    
    output_file = f"example_output_{team_id}_{user_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 50)
    print("SCRAPING COMPLETED!")
    print(f"Total items scraped: {len(all_items)}")
    print(f"Output saved to: {output_file}")
    
    # Show summary by content type
    content_types = {}
    for item in all_items:
        content_type = item.get('content_type', 'unknown')
        content_types[content_type] = content_types.get(content_type, 0) + 1
    
    print("\nContent type breakdown:")
    for content_type, count in content_types.items():
        print(f"  {content_type}: {count} items")
    
    # Show sample item
    if all_items:
        print(f"\nSample item:")
        sample = all_items[0]
        print(f"  Title: {sample.get('title', 'No title')}")
        print(f"  Type: {sample.get('content_type', 'unknown')}")
        print(f"  Author: {sample.get('author', 'Unknown')}")
        print(f"  Content length: {len(sample.get('content', ''))} characters")
        print(f"  URL: {sample.get('source_url', 'No URL')}")


if __name__ == "__main__":
    asyncio.run(scrape_example()) 
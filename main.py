import argparse
import json
import os
from typing import List
from scrapers.base import BaseScraper, ContentItem
from scrapers.web import WebScraper
from scrapers.pdf import PDFScraper

def get_scraper(source: str, team_id: str, **kwargs) -> BaseScraper:
    """Get the appropriate scraper for the given source"""
    # Only pass relevant arguments to each scraper
    web_kwargs = {k: kwargs[k] for k in ['max_pages', 'delay', 'max_concurrent', 'use_async'] if k in kwargs}
    pdf_kwargs = {k: kwargs[k] for k in ['chunk_size'] if k in kwargs}
    scrapers = [
        WebScraper(team_id, **web_kwargs),
        PDFScraper(team_id, **pdf_kwargs)
    ]
    
    for scraper in scrapers:
        if scraper.can_handle(source):
            return scraper
    
    return None

def main():
    parser = argparse.ArgumentParser(description='High-performance content scraper for knowledge base')
    parser.add_argument('sources', nargs='+', help='URLs or file paths to scrape')
    parser.add_argument('--team-id', default='default_team', help='Team ID for the output')
    parser.add_argument('--max-pages', type=int, default=50, help='Maximum number of pages to scrape')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--max-concurrent', type=int, default=10, help='Maximum concurrent requests (async mode)')
    parser.add_argument('--no-async', action='store_true', help='Disable async mode (use synchronous scraping)')
    parser.add_argument('--chunk-size', type=int, default=5000, help='Chunk size for PDF splitting')
    parser.add_argument('--output', default='results.json', help='Output JSON file path')
    
    args = parser.parse_args()
    
    all_items: List[ContentItem] = []
    
    for source in args.sources:
        print(f"\nProcessing source: {source}")
        
        scraper = get_scraper(
            source,
            args.team_id,
            max_pages=args.max_pages,
            delay=args.delay,
            max_concurrent=args.max_concurrent,
            use_async=not args.no_async,
            chunk_size=args.chunk_size
        )
        
        if not scraper:
            print(f"No suitable scraper found for: {source}")
            continue
            
        items = scraper.scrape(source)
        all_items.extend(items)
        print(f"Found {len(items)} items from {source}")
    
    # Convert to final format
    output = {
        "team_id": args.team_id,
        "items": [
            {
                "title": item.title,
                "content": item.content,
                "content_type": item.content_type,
                "source_url": item.source_url,
                "author": item.author,
                "user_id": item.user_id
            }
            for item in all_items
        ]
    }
    
    # Save to file
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete! Found {len(all_items)} total items")
    print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main() 
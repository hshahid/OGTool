#!/usr/bin/env python3
"""
Performance test script to compare old vs new scraping methods
"""

import time
import asyncio
from scrapers.web import WebScraper

def test_sync_scraping(url: str, max_pages: int = 10):
    """Test synchronous scraping performance"""
    print(f"\n=== Testing SYNC Scraping (max_pages={max_pages}) ===")
    start_time = time.time()
    
    scraper = WebScraper(
        team_id="test_team",
        max_pages=max_pages,
        delay=0.5,  # Reduced delay for testing
        use_async=False
    )
    
    items = scraper.scrape(url)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Sync scraping completed in {duration:.2f} seconds")
    print(f"Found {len(items)} items")
    print(f"Average time per page: {duration/max_pages:.2f} seconds")
    
    return duration, len(items)

def test_async_scraping(url: str, max_pages: int = 10, max_concurrent: int = 5):
    """Test asynchronous scraping performance"""
    print(f"\n=== Testing ASYNC Scraping (max_pages={max_pages}, concurrent={max_concurrent}) ===")
    start_time = time.time()
    
    scraper = WebScraper(
        team_id="test_team",
        max_pages=max_pages,
        delay=0.5,  # Reduced delay for testing
        max_concurrent=max_concurrent,
        use_async=True
    )
    
    items = scraper.scrape(url)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Async scraping completed in {duration:.2f} seconds")
    print(f"Found {len(items)} items")
    print(f"Average time per page: {duration/max_pages:.2f} seconds")
    
    return duration, len(items)

def main():
    # Test URL - using a simple blog that allows scraping
    test_url = "https://httpbin.org/html"  # Simple test URL
    
    print("Performance Test: Sync vs Async Web Scraping")
    print("=" * 50)
    
    # Test with different configurations
    test_configs = [
        (5, 3),   # 5 pages, 3 concurrent
        (10, 5),  # 10 pages, 5 concurrent
        (10, 10), # 10 pages, 10 concurrent
    ]
    
    results = []
    
    for max_pages, max_concurrent in test_configs:
        print(f"\n{'='*60}")
        print(f"Testing with {max_pages} pages, {max_concurrent} concurrent requests")
        print(f"{'='*60}")
        
        # Test sync
        sync_duration, sync_items = test_sync_scraping(test_url, max_pages)
        
        # Test async
        async_duration, async_items = test_async_scraping(test_url, max_pages, max_concurrent)
        
        # Calculate improvement
        speedup = sync_duration / async_duration if async_duration > 0 else float('inf')
        
        results.append({
            'max_pages': max_pages,
            'max_concurrent': max_concurrent,
            'sync_duration': sync_duration,
            'async_duration': async_duration,
            'speedup': speedup,
            'sync_items': sync_items,
            'async_items': async_items
        })
        
        print(f"\n📊 RESULTS:")
        print(f"   Sync: {sync_duration:.2f}s")
        print(f"   Async: {async_duration:.2f}s")
        print(f"   Speedup: {speedup:.2f}x faster")
        print(f"   Items found: {sync_items} vs {async_items}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        print(f"Pages: {result['max_pages']}, Concurrent: {result['max_concurrent']}")
        print(f"  Speedup: {result['speedup']:.2f}x faster")
        print(f"  Time saved: {result['sync_duration'] - result['async_duration']:.2f}s")
        print()

if __name__ == "__main__":
    main() 
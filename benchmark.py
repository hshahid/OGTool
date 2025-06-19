#!/usr/bin/env python3
"""
Simple benchmark script to test scraping performance
"""

import time
import sys
from scrapers.web import WebScraper

def benchmark_scraping(url: str, max_pages: int = 5):
    """Benchmark both sync and async scraping"""
    
    print(f"Benchmarking scraping for: {url}")
    print(f"Max pages: {max_pages}")
    print("=" * 60)
    
    # Test sync scraping
    print("\n🔄 Testing SYNC scraping...")
    start_time = time.time()
    
    sync_scraper = WebScraper(
        team_id="benchmark",
        max_pages=max_pages,
        delay=0.5,
        use_async=False
    )
    
    sync_items = sync_scraper.scrape(url)
    sync_time = time.time() - start_time
    
    print(f"✅ Sync completed in {sync_time:.2f}s")
    print(f"   Found {len(sync_items)} items")
    
    # Test async scraping
    print("\n⚡ Testing ASYNC scraping...")
    start_time = time.time()
    
    async_scraper = WebScraper(
        team_id="benchmark",
        max_pages=max_pages,
        delay=0.5,
        max_concurrent=5,
        use_async=True
    )
    
    async_items = async_scraper.scrape(url)
    async_time = time.time() - start_time
    
    print(f"✅ Async completed in {async_time:.2f}s")
    print(f"   Found {len(async_items)} items")
    
    # Calculate improvement
    if async_time > 0:
        speedup = sync_time / async_time
        time_saved = sync_time - async_time
        improvement_pct = ((sync_time - async_time) / sync_time) * 100
        
        print(f"\n📊 PERFORMANCE RESULTS:")
        print(f"   Sync time:    {sync_time:.2f}s")
        print(f"   Async time:   {async_time:.2f}s")
        print(f"   Speedup:      {speedup:.2f}x faster")
        print(f"   Time saved:   {time_saved:.2f}s ({improvement_pct:.1f}%)")
        print(f"   Items found:  {len(sync_items)} vs {len(async_items)}")
        
        if speedup > 1.5:
            print(f"   🎉 Significant improvement!")
        elif speedup > 1.1:
            print(f"   👍 Good improvement")
        else:
            print(f"   ⚠️  Minimal improvement (may be network limited)")
    else:
        print(f"\n❌ Async scraping failed or took 0 time")
    
    return {
        'sync_time': sync_time,
        'async_time': async_time,
        'sync_items': len(sync_items),
        'async_items': len(async_items)
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmark.py <url> [max_pages]")
        print("Example: python benchmark.py https://example.com 10")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    try:
        results = benchmark_scraping(url, max_pages)
        
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"URL: {url}")
        print(f"Max pages: {max_pages}")
        print(f"Sync performance: {results['sync_time']:.2f}s for {results['sync_items']} items")
        print(f"Async performance: {results['async_time']:.2f}s for {results['async_items']} items")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
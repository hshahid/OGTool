#!/usr/bin/env python3
"""
Test script to verify the output format matches the required structure.
"""

import json
from output_formatter import OutputFormatter


def test_output_format():
    """Test that the output formatter produces the correct format."""
    
    # Sample data
    sample_items = [
        {
            'title': 'Test Blog Post',
            'content': 'This is a test blog post content in markdown format.',
            'content_type': 'blog',
            'source_url': 'https://example.com/blog/test',
            'author': 'Test Author',
            'user_id': 'test_user'
        },
        {
            'title': 'Test PDF Document - Part 1',
            'content': '## Chapter 1\n\nThis is the first chapter of the PDF document.',
            'content_type': 'book',
            'source_url': 'https://example.com/document.pdf',
            'author': 'PDF Author',
            'user_id': 'test_user'
        }
    ]
    
    # Test the formatter
    formatter = OutputFormatter()
    output = formatter.format_output('test_team', sample_items)
    
    # Print the output
    print("Generated Output:")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    
    # Verify structure
    required_fields = ['team_id', 'items']
    item_fields = ['title', 'content', 'content_type', 'source_url', 'author', 'user_id']
    
    print("\nVerifying structure...")
    
    # Check top-level fields
    for field in required_fields:
        if field not in output:
            print(f"❌ Missing required field: {field}")
        else:
            print(f"✅ Found required field: {field}")
    
    # Check items
    if 'items' in output and isinstance(output['items'], list):
        print(f"✅ Found {len(output['items'])} items")
        
        for i, item in enumerate(output['items']):
            print(f"\nChecking item {i+1}:")
            for field in item_fields:
                if field not in item:
                    print(f"❌ Missing field in item {i+1}: {field}")
                else:
                    print(f"✅ Found field in item {i+1}: {field}")
    else:
        print("❌ Items field is missing or not a list")
    
    # Check content types
    print("\nChecking content types...")
    valid_content_types = ['blog', 'podcast_transcript', 'call_transcript', 'linkedin_post', 'reddit_comment', 'book', 'other']
    
    for i, item in enumerate(output.get('items', [])):
        content_type = item.get('content_type', '')
        if content_type in valid_content_types:
            print(f"✅ Item {i+1} has valid content type: {content_type}")
        else:
            print(f"❌ Item {i+1} has invalid content type: {content_type}")
    
    # Save test output
    with open('test_format_output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nTest output saved to test_format_output.json")


if __name__ == "__main__":
    test_output_format() 
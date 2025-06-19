"""
Output formatter that formats scraped data into the required JSON structure.
"""

from typing import List, Dict, Any
from config import MIN_CONTENT_LENGTH


class OutputFormatter:
    """Formats scraped data into the required output structure."""
    
    def format_output(self, team_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format the scraped items into the required output structure."""
        formatted_items = []
        
        for item in items:
            formatted_item = self._format_item(item)
            if formatted_item:
                formatted_items.append(formatted_item)
        
        return {
            "team_id": team_id,
            "items": formatted_items
        }
    
    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single item according to the required structure."""
        # Ensure all required fields are present
        formatted_item = {
            "title": item.get('title', ''),
            "content": item.get('content', ''),
            "content_type": item.get('content_type', 'other'),
            "source_url": item.get('source_url', ''),
            "author": item.get('author', ''),
            "user_id": item.get('user_id', '')
        }
        
        # Validate and clean the item
        if self._is_valid_item(formatted_item):
            return formatted_item
        else:
            return None
    
    def _is_valid_item(self, item: Dict[str, Any]) -> bool:
        """Check if an item is valid and should be included."""
        # Must have a title
        if not item.get('title', '').strip():
            return False
        
        # Must have content
        if not item.get('content', '').strip():
            return False
        
        # Must have a source URL
        if not item.get('source_url', '').strip():
            return False
        
        # Content should be reasonably long
        if len(item.get('content', '')) < MIN_CONTENT_LENGTH:
            return False
        
        return True 
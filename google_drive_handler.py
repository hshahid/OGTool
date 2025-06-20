"""
Google Drive handler to extract direct PDF links from Google Drive URLs.
Handles both folder and file links, including download confirmation for large files.
"""

import re
import asyncio
import aiohttp
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import PyPDF2
from io import BytesIO

CONFIRM_TOKEN_RE = re.compile(r"confirm=([0-9A-Za-z_]+)")

class GoogleDriveHandler:
    """Handler for Google Drive links to extract and download PDF URLs."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def is_google_drive_url(self, url: str) -> bool:
        """Check if the URL is a Google Drive link."""
        return 'drive.google.com' in url.lower()
    
    async def extract_pdf_urls(self, url: str) -> List[str]:
        """Extract direct PDF URLs from Google Drive links."""
        if not self.is_google_drive_url(url):
            return [url]  # Return original URL if not Google Drive
        
        try:
            parsed_url = urlparse(url)
            
            # Handle folder links
            if '/folders/' in url:
                return await self._extract_from_folder(url)
            
            # Handle file links
            elif '/file/' in url:
                file_id = self._extract_file_id(url)
                if file_id:
                    return [self._make_download_url(file_id)]
                return []
            
            # Handle other Google Drive formats
            else:
                # Try to extract file ID and convert to direct link
                file_id = self._extract_file_id(url)
                if file_id:
                    return [self._make_download_url(file_id)]
                
                return []
                
        except Exception as e:
            print(f"Error processing Google Drive URL {url}: {e}")
            return []
    
    async def _extract_from_folder(self, folder_url: str) -> List[str]:
        """Extract PDF URLs from a Google Drive folder."""
        try:
            print(f"Processing Google Drive folder: {folder_url}")
            async with self.session.get(folder_url, timeout=30) as response:
                if response.status != 200:
                    print(f"Failed to fetch folder page: {response.status}")
                    return []
                html_content = await response.text()
            
            # Extract file IDs and names
            files = self._parse_folder_html_for_files(html_content)
            
            # Remove duplicates and invalid IDs
            unique_files = []
            seen_ids = set()
            for file_id, file_name in files:
                if file_id and not file_id.startswith('_') and file_id not in seen_ids:
                    unique_files.append((file_id, file_name))
                    seen_ids.add(file_id)
            
            print(f"Found {len(unique_files)} files in folder:")
            for file_id, file_name in unique_files:
                print(f"  - {file_name} (ID: {file_id})")
            
            # Filter for PDF files based on file extension
            pdf_urls = []
            for file_id, file_name in unique_files:
                if file_name.lower().endswith('.pdf'):
                    url = self._make_download_url(file_id)
                    pdf_urls.append(url)
                    print(f"  ✓ Added PDF: {file_name}")
                else:
                    print(f"  ✗ Skipped non-PDF: {file_name}")
            
            print(f"Found {len(pdf_urls)} PDF files in folder")
            return pdf_urls
            
        except Exception as e:
            print(f"Error extracting from folder {folder_url}: {e}")
            return []
    
    def _parse_folder_html_for_file_ids(self, html_content: str) -> List[str]:
        """Find all file IDs in the folder HTML."""
        # Find all file IDs in the folder HTML
        file_id_pattern = r'/file/d/([a-zA-Z0-9_-]+)'
        return re.findall(file_id_pattern, html_content)
    
    def _parse_folder_html_for_files(self, html_content: str) -> List[tuple]:
        """Extract file IDs and names from the folder HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        files = []
        
        # Look for file links in Google Drive interface
        # Google Drive typically uses this pattern for file links
        file_links = soup.find_all('a', href=re.compile(r'/file/d/'))
        
        for link in file_links:
            # Extract file ID from href
            href = link.get('href', '')
            file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', href)
            if file_id_match:
                file_id = file_id_match.group(1)
                
                # Try to extract file name from various possible locations
                file_name = self._extract_file_name_from_link(link)
                
                if file_name:
                    files.append((file_id, file_name))
        
        # If we couldn't extract names from links, try alternative methods
        if not files:
            # Look for file names in the page content
            files = self._extract_files_from_content(html_content)
        
        return files
    
    def _extract_file_name_from_link(self, link) -> str:
        """Extract file name from a Google Drive file link."""
        # Try different attributes where Google Drive might store the file name
        name_attributes = [
            'title',
            'aria-label',
            'data-tooltip',
            'data-title'
        ]
        
        for attr in name_attributes:
            name = link.get(attr, '')
            if name and name.strip():
                return name.strip()
        
        # Try to get text content
        text = link.get_text(strip=True)
        if text and len(text) > 0:
            return text
        
        return ""
    
    def _extract_files_from_content(self, html_content: str) -> List[tuple]:
        """Extract file information from page content as fallback."""
        files = []
        
        # Look for patterns that might contain file information
        # This is a fallback method when the standard link parsing doesn't work
        
        # Pattern for file IDs
        file_id_pattern = r'/file/d/([a-zA-Z0-9_-]+)'
        file_ids = re.findall(file_id_pattern, html_content)
        
        # For now, we'll use the file IDs we found and assume they're PDFs
        # In a more sophisticated implementation, we could look for file names
        # in the surrounding HTML context
        for file_id in file_ids:
            files.append((file_id, f"file_{file_id}.pdf"))
        
        return files
    
    def _extract_file_id(self, url: str) -> Optional[str]:
        """Extract file ID from Google Drive URL."""
        # Pattern for file ID in various Google Drive URL formats
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'/open\?id=([a-zA-Z0-9_-]+)',
            r'/uc\?id=([a-zA-Z0-9_-]+)',
            r'/uc\?export=download&id=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _make_download_url(self, file_id: str) -> str:
        """Create a direct download URL for a file."""
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    async def _is_pdf_file_debug(self, url: str):
        """Check if the file at the given URL is a PDF, returning (is_pdf, content_type)."""
        try:
            async with self.session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    ctype = resp.headers.get('content-type', '').lower()
                    if 'pdf' in ctype:
                        return True, ctype
                    # Accept application/octet-stream as a possible PDF
                    if ctype == 'application/octet-stream':
                        # Try to read a small chunk and check if it's a PDF
                        content = await resp.read()
                        try:
                            PyPDF2.PdfReader(BytesIO(content))
                            return True, ctype
                        except Exception as e:
                            print(f"    Not a valid PDF (PyPDF2 error): {e}")
                            return False, ctype
                    if 'text' in ctype or 'html' in ctype or ctype == '' or ctype == 'application/octet-stream':
                        text = await resp.text(errors='ignore')
                        confirm_token = self._extract_confirm_token(text)
                        if confirm_token:
                            url_with_token = url + f"&confirm={confirm_token}"
                            async with self.session.get(url_with_token, timeout=30) as resp2:
                                ctype2 = resp2.headers.get('content-type', '').lower()
                                if 'pdf' in ctype2:
                                    return True, ctype2
                                if ctype2 == 'application/octet-stream':
                                    content2 = await resp2.read()
                                    try:
                                        PyPDF2.PdfReader(BytesIO(content2))
                                        return True, ctype2
                                    except Exception as e:
                                        print(f"    Not a valid PDF (PyPDF2 error): {e}")
                                        return False, ctype2
                return False, resp.headers.get('content-type', '').lower()
        except Exception as e:
            print(f"Error checking PDF file at {url}: {e}")
            return False, None
    
    def _extract_confirm_token(self, html: str) -> Optional[str]:
        """Extract confirm token from HTML content."""
        # Google sometimes puts the confirm token in a form or in the URL
        match = CONFIRM_TOKEN_RE.search(html)
        if match:
            return match.group(1)
        # Try to find confirm token in download warning page
        soup = BeautifulSoup(html, 'html.parser')
        for input_tag in soup.find_all('input'):
            if input_tag.get('name') == 'confirm':
                return input_tag.get('value')
        return None
    
    def _extract_folder_id(self, url: str) -> Optional[str]:
        """Extract folder ID from Google Drive URL."""
        pattern = r'/folders/([a-zA-Z0-9_-]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else None 
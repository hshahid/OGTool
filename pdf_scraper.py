"""
PDF scraper that can extract text from PDF files and chunk them into manageable pieces.
Supports multiple PDF processing libraries for better compatibility.
"""

import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional, List, Tuple
import re
import os
import tempfile
from urllib.parse import urlparse
import PyPDF2
import pdfplumber
from io import BytesIO
import time


class PDFScraper:
    """PDF scraper class that handles PDF extraction and chunking."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, max_retries: int = 3):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_retries = max_retries
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_pdf(self, url: str, user_id: str) -> List[Dict[str, Any]]:
        """Scrape a PDF file and return chunked content."""
        try:
            # Download the PDF
            pdf_content = await self._download_pdf(url)
            if not pdf_content:
                print(f"Failed to download PDF from {url}")
                return []
            
            # Extract text from PDF
            text_content = await self._extract_text_from_pdf(pdf_content)
            if not text_content:
                print(f"Failed to extract text from PDF {url}")
                return []
            
            # Clean and process the text
            cleaned_text = self._clean_text(text_content)
            
            # Extract metadata
            metadata = await self._extract_metadata(pdf_content, url)
            
            # Chunk the content
            chunks = self._chunk_text(cleaned_text)
            
            # Create items for each chunk
            items = []
            for i, chunk in enumerate(chunks):
                # Convert chunk to markdown format
                markdown_content = self._convert_to_markdown(chunk)
                
                item = {
                    'title': f"{metadata.get('title', 'PDF Document')} - Part {i+1}",
                    'content': markdown_content,
                    'content_type': 'book',  # PDFs are mapped to 'book' type
                    'source_url': url,
                    'author': metadata.get('author', ''),
                    'user_id': user_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'pdf_metadata': metadata
                }
                items.append(item)
            
            return items
            
        except Exception as e:
            print(f"Error scraping PDF {url}: {e}")
            return []
    
    async def _download_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF content from URL."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        # Accept both PDF and octet-stream content types
                        if ('pdf' in content_type or 
                            'octet-stream' in content_type or 
                            url.lower().endswith('.pdf')):
                            return await response.read()
                        else:
                            print(f"URL does not point to a PDF: {content_type}")
                            return None
                    else:
                        print(f"HTTP {response.status} for {url}")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 * (attempt + 1))
        
        return None
    
    async def _extract_text_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        """Extract text from PDF content using multiple libraries for better compatibility."""
        text = ""
        
        # Try pdfplumber first (better text extraction)
        try:
            text = self._extract_with_pdfplumber(pdf_content)
            if text and len(text.strip()) > 100:
                return text
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
        
        # Try PyPDF2 as fallback
        try:
            text = self._extract_with_pypdf2(pdf_content)
            if text and len(text.strip()) > 100:
                return text
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
        
        return text if text.strip() else None
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> str:
        """Extract text using pdfplumber."""
        text = ""
        
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> str:
        """Extract text using PyPDF2."""
        text = ""
        
        pdf_file = BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return text
    
    async def _extract_metadata(self, pdf_content: bytes, url: str) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        metadata = {
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'producer': '',
            'num_pages': 0
        }
        
        try:
            # Try PyPDF2 for metadata
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            metadata['num_pages'] = len(pdf_reader.pages)
            
            # Get document metadata
            if pdf_reader.metadata:
                metadata['title'] = pdf_reader.metadata.get('/Title', '')
                metadata['author'] = pdf_reader.metadata.get('/Author', '')
                metadata['subject'] = pdf_reader.metadata.get('/Subject', '')
                metadata['creator'] = pdf_reader.metadata.get('/Creator', '')
                metadata['producer'] = pdf_reader.metadata.get('/Producer', '')
            
        except Exception as e:
            print(f"Failed to extract metadata: {e}")
        
        # Fallback title from URL
        if not metadata['title']:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if filename:
                metadata['title'] = filename.replace('.pdf', '').replace('_', ' ').title()
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers
        text = re.sub(r'\b\d+\s*of\s*\d+\b', '', text)  # "Page X of Y"
        text = re.sub(r'\bPage\s+\d+\b', '', text)  # "Page X"
        
        # Remove common PDF artifacts
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\']', ' ', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _convert_to_markdown(self, text: str) -> str:
        """Convert plain text to markdown format."""
        if not text:
            return ""
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        
        markdown_lines = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if it looks like a heading (short, ends without period)
            if len(paragraph) < 100 and not paragraph.endswith('.') and not paragraph.endswith('!') and not paragraph.endswith('?'):
                # Likely a heading
                markdown_lines.append(f"## {paragraph}")
            else:
                # Regular paragraph
                markdown_lines.append(paragraph)
            
            markdown_lines.append("")  # Add blank line between paragraphs
        
        return '\n'.join(markdown_lines).strip()
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        if not text:
            return []
        
        # Split by sentences first to maintain context
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Find the last few sentences that fit within overlap
                    overlap_text = ""
                    for prev_sentence in reversed(sentences[:sentences.index(sentence)]):
                        if len(overlap_text) + len(prev_sentence) <= self.chunk_overlap:
                            overlap_text = prev_sentence + " " + overlap_text
                        else:
                            break
                    current_chunk = overlap_text + sentence
                else:
                    current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Ensure chunks are not too small
        final_chunks = []
        for chunk in chunks:
            if len(chunk) >= 100:  # Minimum chunk size
                final_chunks.append(chunk)
            elif final_chunks:
                # Merge small chunks with the previous one
                final_chunks[-1] += " " + chunk
        
        return final_chunks
    
    def is_pdf_url(self, url: str) -> bool:
        """Check if the URL points to a PDF file."""
        url_lower = url.lower()
        
        # Check file extension
        if url_lower.endswith('.pdf'):
            return True
        
        # Check for PDF in URL path
        if '/pdf' in url_lower or 'pdf' in url_lower:
            return True
        
        # Check for Google Drive PDF links
        if 'drive.google.com' in url_lower and ('/file/' in url_lower or '/folders/' in url_lower):
            return True
        
        return False 
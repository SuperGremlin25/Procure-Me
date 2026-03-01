"""
PDF Parser Module

Handles parsing of PDF quotes from vendors using multiple libraries for maximum compatibility.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import re
import io
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# Try to import PDF libraries
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import tabula
    HAS_TABULA = True
except ImportError:
    HAS_TABULA = False

try:
    import camelot
    HAS_CAMELOT = True
except ImportError:
    HAS_CAMELOT = False


class PDFParser:
    """
    Advanced PDF parser for vendor quotes.
    
    Uses multiple strategies to extract data from PDFs:
    1. pdfplumber - For text-based PDFs with tables
    2. PyMuPDF - For text extraction and OCR fallback
    3. tabula - For advanced table extraction
    4. camelot - For complex table structures
    """
    
    def __init__(self):
        """Initialize the PDF parser."""
        self.strategies = []
        
        if HAS_PDFPLUMBER:
            self.strategies.append(('pdfplumber', self._parse_with_pdfplumber))
        
        if HAS_TABULA:
            self.strategies.append(('tabula', self._parse_with_tabula))
            
        if HAS_CAMELOT:
            self.strategies.append(('camelot', self._parse_with_camelot))
            
        if HAS_PYMUPDF:
            self.strategies.append(('pymupdf', self._parse_with_pymupdf))
    
    def parse_pdf(self, pdf_file: io.BytesIO) -> pd.DataFrame:
        """
        Parse PDF file and extract quote data.
        
        Args:
            pdf_file: PDF file as BytesIO object
            
        Returns:
            DataFrame with extracted quote data
        """
        # Save PDF to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_file.getvalue())
            temp_path = tmp.name
        
        try:
            # Try each strategy until one works
            for strategy_name, strategy_func in self.strategies:
                try:
                    print(f"Trying {strategy_name}...")
                    df = strategy_func(temp_path)
                    if not df.empty:
                        print(f"Success with {strategy_name}!")
                        return self._clean_pdf_data(df)
                except Exception as e:
                    print(f"{strategy_name} failed: {str(e)}")
                    continue
            
            # If all strategies fail, try text extraction
            if HAS_PYMUPDF:
                return self._extract_from_text(temp_path)
            
            raise ValueError("Could not extract data from PDF with any available method")
            
        finally:
            # Clean up
            import os
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass
    
    def _parse_with_pdfplumber(self, file_path: str) -> pd.DataFrame:
        """Parse PDF using pdfplumber."""
        tables = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract tables
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table and len(table) > 1:  # At least header + one row
                        df = pd.DataFrame(table[1:], columns=table[0])
                        tables.append(df)
        
        if tables:
            # Combine all tables
            return pd.concat(tables, ignore_index=True)
        else:
            # Try to extract text and parse manually
            return self._parse_text_from_pdfplumber(file_path)
    
    def _parse_text_from_pdfplumber(self, file_path: str) -> pd.DataFrame:
        """Extract text and parse line by line."""
        data = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        # Try to parse line items
                        if self._looks_like_line_item(line):
                            parsed = self._parse_line_item(line)
                            if parsed:
                                data.append(parsed)
        
        return pd.DataFrame(data)
    
    def _parse_with_tabula(self, file_path: str) -> pd.DataFrame:
        """Parse PDF using tabula-py."""
        # Try different extraction modes
        dfs = tabula.read_pdf(
            file_path,
            pages='all',
            multiple_tables=True,
            guess=True,
            lattice=True
        )
        
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        else:
            # Try stream mode
            dfs = tabula.read_pdf(
                file_path,
                pages='all',
                multiple_tables=True,
                stream=True
            )
            if dfs:
                return pd.concat(dfs, ignore_index=True)
        
        return pd.DataFrame()
    
    def _parse_with_camelot(self, file_path: str) -> pd.DataFrame:
        """Parse PDF using camelot."""
        tables = camelot.read_pdf(file_path, pages='all')
        
        if tables:
            dfs = [table.df for table in tables]
            return pd.concat(dfs, ignore_index=True)
        
        return pd.DataFrame()
    
    def _parse_with_pymupdf(self, file_path: str) -> pd.DataFrame:
        """Parse PDF using PyMuPDF."""
        doc = fitz.open(file_path)
        tables = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Try to find tables
            tabs = page.find_tables()
            
            if tabs:
                for tab in tabs:
                    df = tab.to_pandas()
                    tables.append(df)
        
        doc.close()
        
        if tables:
            return pd.concat(tables, ignore_index=True)
        else:
            return self._extract_from_text(file_path)
    
    def _extract_from_text(self, file_path: str) -> pd.DataFrame:
        """Extract text and parse line items."""
        doc = fitz.open(file_path)
        data = []
        
        for page in doc:
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                if self._looks_like_line_item(line):
                    parsed = self._parse_line_item(line)
                    if parsed:
                        data.append(parsed)
        
        doc.close()
        return pd.DataFrame(data)
    
    def _looks_like_line_item(self, line: str) -> bool:
        """Check if a line looks like a quote line item."""
        # Look for patterns like: description, quantity, price
        line = line.strip()
        
        # Must have some text
        if not line or len(line) < 10:
            return False
        
        # Look for price patterns ($123.45, 123.45, etc.)
        price_pattern = r'\$?\d{1,5}[.,]\d{2}'
        has_price = re.search(price_pattern, line)
        
        # Look for quantity patterns
        qty_pattern = r'\b\d+\s*(ea|ft|each|pcs|pcs|lb|kg|m|cm)\b'
        has_qty = re.search(qty_pattern, line, re.IGNORECASE)
        
        # Look for part number patterns
        part_pattern = r'\b[A-Z]{2,}-\d{3,}\b|\b\d{6,}\b'
        has_part = re.search(part_pattern, line)
        
        return (has_price or has_qty or has_part)
    
    def _parse_line_item(self, line: str) -> Optional[Dict]:
        """Parse a line item into structured data."""
        # Try to extract quantity, description, unit price
        line = line.strip()
        
        # Common patterns
        # Pattern 1: Qty Description Unit Price Total
        pattern1 = r'^(\d+(?:\.\d+)?)\s+(.+?)\s+(\$?\d{1,5}[.,]\d{2})(?:\s+(\$?\d{1,5}[.,]\d{2}))?'
        
        # Pattern 2: Description Qty Unit Price
        pattern2 = r'^(.+?)\s+(\d+(?:\.\d+)?)\s+(\$?\d{1,5}[.,]\d{2})'
        
        # Pattern 3: Part# Description Qty Price
        pattern3 = r'^([A-Z0-9-]+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(\$?\d{1,5}[.,]\d{2})'
        
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if pattern == pattern1:
                    return {
                        'Quantity': float(groups[0]),
                        'Description': groups[1].strip(),
                        'Unit Price': groups[2].replace('$', '').replace(',', ''),
                        'Total': groups[3].replace('$', '').replace(',', '') if groups[3] else None
                    }
                elif pattern == pattern2:
                    return {
                        'Description': groups[0].strip(),
                        'Quantity': float(groups[1]),
                        'Unit Price': groups[2].replace('$', '').replace(',', ''),
                        'Total': None
                    }
                elif pattern == pattern3:
                    return {
                        'Part Number': groups[0],
                        'Description': groups[1].strip(),
                        'Quantity': float(groups[2]),
                        'Unit Price': groups[3].replace('$', '').replace(',', ''),
                        'Total': None
                    }
        
        # If no pattern matches, try to extract what we can
        numbers = re.findall(r'\$?\d{1,5}[.,]\d{2}', line)
        if numbers:
            return {
                'Description': line,
                'Unit Price': numbers[0].replace('$', '').replace(',', ''),
                'Quantity': 1,
                'Total': numbers[-1].replace('$', '').replace(',', '') if len(numbers) > 1 else None
            }
        
        return None
    
    def _clean_pdf_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize extracted PDF data."""
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Standardize column names
        column_mapping = {
            'DESCRIPTION': 'Description',
            'ITEM': 'Description',
            'PRODUCT': 'Description',
            'PART NO': 'Part Number',
            'PART#': 'Part Number',
            'QTY': 'Quantity',
            'QUANTITY': 'Quantity',
            'UNIT PRICE': 'Unit Price',
            'PRICE': 'Unit Price',
            'UNIT COST': 'Unit Cost',
            'TOTAL': 'Total',
            'AMOUNT': 'Total',
            'EXTENSION': 'Total'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Clean numeric columns
        numeric_cols = ['Quantity', 'Unit Price', 'Unit Cost', 'Total']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove empty rows
        df = df.dropna(how='all')
        
        # NOTE: Do NOT remove tax/freight/subtotal rows here.
        # They are extracted downstream by clean_vendor_quote() in pricing_calculator.py
        # before being filtered out. Removing them here loses critical data.
        
        # Fill missing quantities with 1
        if 'Quantity' in df.columns:
            df['Quantity'] = df['Quantity'].fillna(1)
        
        return df
    
    def get_pdf_info(self, pdf_file: io.BytesIO) -> Dict:
        """
        Get information about the PDF file.
        
        Args:
            pdf_file: PDF file as BytesIO object
            
        Returns:
            Dictionary with PDF information
        """
        info = {
            'strategies_available': [s[0] for s in self.strategies],
            'pages': 0,
            'has_tables': False,
            'file_size': len(pdf_file.getvalue())
        }
        
        if HAS_PYMUPDF:
            # Save to temp file to read with PyMuPDF
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(pdf_file.getvalue())
                temp_path = tmp.name
            
            try:
                doc = fitz.open(temp_path)
                info['pages'] = len(doc)
                
                # Check for tables
                for page in doc:
                    if page.find_tables():
                        info['has_tables'] = True
                        break
                
                doc.close()
            except:
                pass
            finally:
                import os
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
        
        return info
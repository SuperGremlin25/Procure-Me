"""
Vendor Detection Module

Intelligently detects vendor name from uploaded quote files.
Does not rely on hardcoded vendor list - works with any vendor.
"""

import pandas as pd
from typing import Dict, List
import re


class VendorDetector:
    """
    Detects vendor information from uploaded quote files using intelligent heuristics.
    """
    
    def __init__(self):
        self.vendor_indicators = [
            'vendor', 'supplier', 'from:', 'sold by', 'bill to', 
            'quote from', 'prepared by', 'company name', 'contractor',
            'quotation by', 'prepared for', 'seller', 'distributor'
        ]
        
    def detect_from_dataframe(self, df: pd.DataFrame) -> Dict:
        """
        Scan DataFrame for vendor name in headers, footers, metadata.
        
        Args:
            df: DataFrame loaded from quote file
            
        Returns:
            Dictionary with vendor_name, confidence, indicators, method
        """
        results = {
            "vendor_name": "Unknown",
            "confidence": 0.0,
            "indicators": [],
            "method": "manual_required"
        }
        
        if df.empty:
            return results
        
        # Strategy 1: Scan first 10 rows for vendor keywords
        for idx in range(min(10, len(df))):
            row = df.iloc[idx]
            for col_idx, val in enumerate(row):
                val_str = str(val).strip()
                
                if pd.isna(val) or not val_str or val_str == 'nan':
                    continue
                
                # Check if this cell contains a vendor indicator
                for indicator in self.vendor_indicators:
                    if indicator.lower() in val_str.lower():
                        vendor_name = self._extract_vendor_name(val_str, indicator)
                        if vendor_name and len(vendor_name) > 3:
                            results["vendor_name"] = vendor_name
                            results["confidence"] = 0.8
                            results["indicators"].append(
                                f"Found '{indicator}' in row {idx+1}, col {col_idx+1}: '{vendor_name}'"
                            )
                            results["method"] = "header_scan"
                            return results
        
        # Strategy 2: Check first cell (often company name in quotes)
        first_cell = str(df.iloc[0, 0]).strip()
        if len(first_cell) > 3 and first_cell not in ['Description', 'Item', 'Material', 'Part', 'Product', 'nan']:
            # Check if it looks like a company name (has spaces or capitals)
            if ' ' in first_cell or first_cell[0].isupper():
                results["vendor_name"] = first_cell
                results["confidence"] = 0.6
                results["indicators"].append(f"Possible vendor in first cell: '{first_cell}'")
                results["method"] = "first_cell_heuristic"
                return results
        
        # Strategy 3: Look for all-caps company names in first 5 rows
        for idx in range(min(5, len(df))):
            row = df.iloc[idx]
            for val in row:
                val_str = str(val).strip()
                if val_str and val_str != 'nan' and val_str.isupper() and len(val_str) > 5 and ' ' in val_str:
                    # Filter out common header text
                    if not any(keyword in val_str for keyword in ['DESCRIPTION', 'MATERIAL', 'PART NUMBER', 'QUANTITY', 'PRICE', 'TOTAL']):
                        results["vendor_name"] = val_str.title()
                        results["confidence"] = 0.5
                        results["indicators"].append(f"All-caps text in row {idx+1}: '{val_str}'")
                        results["method"] = "allcaps_heuristic"
                        return results
        
        # Strategy 4: Check column headers for company names
        if hasattr(df, 'columns'):
            for col in df.columns:
                col_str = str(col).strip()
                if col_str and col_str != 'nan' and len(col_str) > 5:
                    # Check if column name contains company-like words
                    company_words = ['inc', 'llc', 'corp', 'ltd', 'electric', 'supply', 'wholesale']
                    if any(word in col_str.lower() for word in company_words):
                        results["vendor_name"] = col_str
                        results["confidence"] = 0.4
                        results["indicators"].append(f"Company-like column name: '{col_str}'")
                        results["method"] = "column_header"
                        return results
        
        return results
    
    def _extract_vendor_name(self, text: str, indicator: str) -> str:
        """
        Extract vendor name from text containing indicator.
        
        Args:
            text: Text containing vendor indicator
            indicator: The indicator keyword found
            
        Returns:
            Extracted vendor name or empty string
        """
        # Split on the indicator and take the part after it
        parts = text.lower().split(indicator.lower())
        if len(parts) > 1:
            vendor_part = parts[1].strip()
            # Clean up common separators
            vendor_part = vendor_part.lstrip(':').lstrip('-').strip()
            # Return first meaningful chunk (before newline, comma, etc)
            vendor_name = re.split(r'[,\n\r\t]', vendor_part)[0].strip()
            return vendor_name.title() if vendor_name else ""
        return ""
    
    def detect_from_filename(self, filename: str) -> Dict:
        """
        Extract vendor name from filename if present.
        
        Args:
            filename: Name of the uploaded file
            
        Returns:
            Dictionary with vendor_name, confidence, indicators, method
        """
        results = {
            "vendor_name": "Unknown",
            "confidence": 0.0,
            "indicators": [],
            "method": "filename"
        }
        
        # Remove extension
        name_no_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Common patterns: "vendor_quote", "quote_vendor", "vendor-2026"
        parts = re.split(r'[-_\s]', name_no_ext.lower())
        
        # Filter out common words
        common_words = ['quote', 'bid', 'estimate', 'proposal', '2025', '2026', '2027', 
                       'final', 'revised', 'draft', 'v1', 'v2', 'v3']
        vendor_candidates = [p for p in parts if p not in common_words and len(p) > 2]
        
        if vendor_candidates:
            vendor_name = vendor_candidates[0].title()
            results["vendor_name"] = vendor_name
            results["confidence"] = 0.4
            results["indicators"].append(f"Extracted from filename: '{vendor_name}'")
        
        return results
    
    def combine_results(self, content_result: Dict, filename_result: Dict) -> Dict:
        """
        Combine results from content and filename detection.
        
        Args:
            content_result: Result from detect_from_dataframe
            filename_result: Result from detect_from_filename
            
        Returns:
            Best combined result
        """
        # Use whichever has higher confidence
        if content_result['confidence'] >= filename_result['confidence']:
            return content_result
        else:
            return filename_result

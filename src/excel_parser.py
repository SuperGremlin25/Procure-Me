"""
Excel Parser Module

Handles parsing of various Excel spreadsheet formats for vendor quotes.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import openpyxl


class ExcelParser:
    """
    Parses Excel files containing vendor quotes.
    
    Supports multiple formats and sheet structures.
    """
    
    def __init__(self):
        """Initialize the ExcelParser."""
        self.supported_formats = ['Vendor Quote Sheet']
    
    def detect_format(self, file_path: str) -> Tuple[str, List[str]]:
        """
        Detect the spreadsheet format and return available sheets.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Tuple of (format_name, list_of_sheet_names)
        """
        # Read all sheet names
        xl_file = pd.ExcelFile(file_path)
        sheet_names = xl_file.sheet_names
        
        # Check for known formats
        for format_name in self.supported_formats:
            if format_name in sheet_names:
                return format_name, sheet_names
        
        # Return generic format if no specific format detected
        return 'Generic', sheet_names
    
    def parse_vendor_format(self, file_path: str, sheet_name: str = 'Vendor Quote Sheet') -> pd.DataFrame:
        """
        Parse the vendor quote spreadsheet format.
        
        Expected columns:
        - Material Description
        - Part Number
        - BOM Qty
        - BOM Unit
        - Quote Unit
        - Quote Qty
        - Vendor Unit Cost
        - Vendor Total
        - ... (calculations)
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet to parse
            
        Returns:
            Parsed and cleaned DataFrame
        """
        # Read the Excel file with header at row 0
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Remove empty rows and summary rows
        df = df.dropna(how='all')
        
        # Filter out subtotal, tax, and summary rows
        filter_terms = ['Subtotal', 'tax', 'Vendor Invoice', 'markup', 'Total Materials']
        mask = ~df.iloc[:, 0].astype(str).str.contains('|'.join(filter_terms), na=False, case=False)
        df = df[mask]
        
        # Reset index after filtering
        df = df.reset_index(drop=True)
        
        # Clean numeric columns
        numeric_columns = ['BOM Qty', 'Quote Qty', 'Vendor Unit Cost', 'Vendor Total']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    
    def parse_generic_format(self, file_path: str, sheet_name: str) -> pd.DataFrame:
        """
        Parse a generic Excel format.
        
        Attempts to automatically detect columns for:
        - Description
        - Part Number
        - Quantity
        - Unit Cost
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the sheet to parse
            
        Returns:
            Parsed DataFrame with standardized column names
        """
        # Read the Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Remove empty rows
        df = df.dropna(how='all')
        
        # Attempt to identify columns
        column_mapping = {}
        
        for col in df.columns:
            col_lower = str(col).lower()
            
            # Description column
            if any(term in col_lower for term in ['description', 'material', 'item', 'product']):
                column_mapping[col] = 'Material Description'
            
            # Part number column
            elif any(term in col_lower for term in ['part', 'sku', 'number', 'code']):
                column_mapping[col] = 'Part Number'
            
            # Quantity column
            elif any(term in col_lower for term in ['qty', 'quantity', 'qty', 'count']):
                column_mapping[col] = 'BOM Qty'
            
            # Unit cost column
            elif any(term in col_lower for term in ['cost', 'price', 'unit']):
                column_mapping[col] = 'Vendor Unit Cost'
        
        # Rename columns based on mapping
        df = df.rename(columns=column_mapping)
        
        return df
    
    def parse_file(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Parse an Excel file, automatically detecting the format.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Optional specific sheet to parse
            
        Returns:
            Parsed DataFrame
            
        Raises:
            ValueError: If the file cannot be parsed
        """
        try:
            # Detect format
            format_name, sheet_names = self.detect_format(file_path)
            
            # Use provided sheet name or auto-detect
            if sheet_name is None:
                if format_name in self.supported_formats:
                    sheet_name = format_name
                else:
                    sheet_name = sheet_names[0] if sheet_names else 'Sheet1'
            
            # Parse based on format
            if format_name == 'Vendor Quote Sheet' and sheet_name == 'Vendor Quote Sheet':
                return self.parse_vendor_format(file_path, sheet_name)
            else:
                return self.parse_generic_format(file_path, sheet_name)
                
        except Exception as e:
            raise ValueError(f"Error parsing Excel file: {str(e)}")
    
    def get_sheet_info(self, file_path: str) -> Dict[str, Dict]:
        """
        Get information about all sheets in the Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Dictionary with sheet information
        """
        try:
            xl_file = pd.ExcelFile(file_path)
            sheet_info = {}
            
            for sheet_name in xl_file.sheet_names:
                # Read first few rows to get column info
                df_sample = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)
                
                sheet_info[sheet_name] = {
                    'columns': df_sample.columns.tolist(),
                    'row_count': len(pd.read_excel(file_path, sheet_name=sheet_name)),
                    'has_data': not df_sample.empty
                }
            
            return sheet_info
            
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {str(e)}")
"""Test script for new features"""
import pandas as pd
import sys
sys.path.append('src')

from src.excel_parser import ExcelParser

print("=" * 60)
print("TESTING NEW FEATURES")
print("=" * 60)

# Test 1: Duplicate column detection
print("\n1. Testing duplicate column detection...")
parser = ExcelParser()

# Create test DataFrame with duplicates
test_df = pd.DataFrame({
    'Description': ['Item 1', 'Item 2'],
    'Qty': [10, 20],
    'Qty': [15, 25],  # Duplicate column name
    'Cost': [1.5, 2.5]
})

print(f"   Created test DF with columns: {test_df.columns.tolist()}")
duplicates = parser.detect_duplicate_columns(test_df)
print(f"   Duplicates detected: {duplicates}")

# Test 2: Rename duplicates
print("\n2. Testing duplicate column renaming...")
fixed_df = parser.rename_duplicate_columns(test_df)
print(f"   Fixed columns: {fixed_df.columns.tolist()}")

# Test 3: Load vendor file
print("\n3. Testing vendor_quote_example.xlsx...")
try:
    df = pd.read_excel('docs/vendor_quote_example.xlsx')
    print(f"   ✓ File loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Check for duplicates
    dups = parser.detect_duplicate_columns(df)
    if dups:
        print(f"   Found duplicates: {dups}")
    else:
        print("   ✓ No duplicates found")
        
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Column detection priorities
print("\n4. Testing Quote Qty prioritization...")
# Import the detect function
import importlib.util
spec = importlib.util.spec_from_file_location("app", "app.py")
app_module = importlib.util.module_from_spec(spec)

try:
    spec.loader.exec_module(app_module)
    _detect_columns = app_module._detect_columns
    
    # Create test DF with both BOM Qty and Quote Qty
    test_df2 = pd.DataFrame({
        'Description': ['Item A', 'Item B', 'Item C'],
        'BOM Qty': [5, 10, 15],
        'Quote Qty': [6, 11, 16],
        'Cost': [1.0, 2.0, 3.0]
    })
    
    detected = _detect_columns(test_df2)
    print(f"   Detected columns: {detected}")
    if detected.get('qty') == 'Quote Qty':
        print("   ✓ Quote Qty correctly prioritized over BOM Qty")
    else:
        print(f"   ✗ Wrong qty column selected: {detected.get('qty')}")
        
except Exception as e:
    print(f"   ✗ Error testing column detection: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

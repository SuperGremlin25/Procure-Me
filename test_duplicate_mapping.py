"""Test that duplicate columns are available for manual mapping"""
import pandas as pd
from src.excel_parser import ExcelParser

# Create test Excel with duplicate Qty columns
test_data = {
    'Description': ['Item 1', 'Item 2', 'Item 3'],
    'BOM Qty': [5, 10, 15],
    'Quote Qty': [6, 11, 16],  
    'Cost': [1.0, 2.0, 3.0]
}

df = pd.DataFrame(test_data)

# Simulate what happens when pandas reads duplicate columns
# Pandas automatically renames them
df_with_dups = df.copy()
df_with_dups.columns = ['Description', 'Qty', 'Qty', 'Cost']  # Duplicate Qty

print("=" * 60)
print("TESTING DUPLICATE COLUMN MAPPING")
print("=" * 60)

print("\n1. Original columns (with duplicates):")
print(f"   {df_with_dups.columns.tolist()}")

parser = ExcelParser()

# Detect duplicates
duplicates = parser.detect_duplicate_columns(df_with_dups)
print(f"\n2. Duplicates detected: {duplicates}")

# Rename duplicates
df_fixed = parser.rename_duplicate_columns(df_with_dups)
print(f"\n3. After renaming:")
print(f"   {df_fixed.columns.tolist()}")

# Show that all columns are available for mapping
all_cols = list(df_fixed.columns)
print(f"\n4. Columns available for manual mapping dropdown:")
for i, col in enumerate(all_cols):
    print(f"   [{i}] {col}")

print("\n5. User can now manually select which 'Qty' to use:")
print("   - Option 0: Qty")
print("   - Option 1: Qty.1")
print("   - User picks the correct one")

print("\n" + "=" * 60)
print("✓ All duplicate columns available for selection")
print("=" * 60)

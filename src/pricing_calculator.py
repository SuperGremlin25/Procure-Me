"""
Pricing Calculator Module

Handles the calculation of composite rates including markup and tax
for vendor quotes to generate client-facing pricing.

Outputs:
  - Client sheet: Description | Composite Unit Rate | Total (3 cols, all-in price)
  - Audit sheet: Full formula trail for leadership verification
"""

import pandas as pd
import numpy as np
import re
import os
import tempfile
from typing import Optional, Dict, Any, Tuple, List
from io import BytesIO
from enum import Enum


class CalculationMethod(Enum):
    """How margin and tax are calculated"""
    MARGIN_THEN_TAX = "margin_then_tax"           # Current default: Cost × (1+Margin) × (1+Tax)
    TAX_SEPARATE = "tax_separate"                  # Government standard: (Cost × (1+Margin)) + (Cost × Tax)
    ADDITIVE = "additive"                          # Simplest: Cost × (1 + Margin + Tax)
    COST_PLUS_FIXED_FEE = "cost_plus_fee"         # Transparent: Cost + Tax + Fixed Fee


class InvoiceFormat(Enum):
    """How the invoice is presented"""
    DETAILED_AUDIT = "detailed_audit"              # Current format with full audit trail
    FAR_COMPLIANT = "far_compliant"                # Government contract format
    GRANT_COMPLIANCE = "grant_compliance"          # ARPA/BEAD specific
    CLEAN_CLIENT = "clean_client"                  # No breakdown shown
    COMBO = "combo"                                # Both audit + clean


class TradeType(Enum):
    """Construction trade for preset suggestions"""
    TELECOM_FIBER = "telecom"
    GENERAL_CONTRACTOR = "general_contractor"
    CIVIL_INFRASTRUCTURE = "civil"
    ELECTRICAL = "electrical"
    PLUMBING_HVAC = "plumbing_hvac"
    CONCRETE = "concrete"
    HOME_BUILDING = "home_building"
    HEAVY_EQUIPMENT = "equipment"
    GENERAL_CONSTRUCTION = "general"


class ComplianceMode(Enum):
    """Quick preset configurations"""
    COMMERCIAL = "commercial"
    GOVERNMENT_GRANT = "grant"
    GOVERNMENT_CONTRACT = "contract"
    CUSTOM = "custom"


# Trade-specific preset configurations
TRADE_PRESETS = {
    TradeType.TELECOM_FIBER: {
        'suggested_margin_min': 0.25,
        'suggested_margin_max': 0.30,
        'default_margin': 0.25,
        'government_margin': 0.15,
        'common_uoms': ['LF', 'EA', 'HR'],
        'description': 'Telecom / Fiber Optic'
    },
    TradeType.GENERAL_CONTRACTOR: {
        'suggested_margin_min': 0.30,
        'suggested_margin_max': 0.35,
        'default_margin': 0.33,
        'government_margin': 0.15,
        'common_uoms': ['LS', 'EA', 'SF'],
        'description': 'General Contractor / Commercial'
    },
    TradeType.CIVIL_INFRASTRUCTURE: {
        'suggested_margin_min': 0.20,
        'suggested_margin_max': 0.25,
        'default_margin': 0.20,
        'government_margin': 0.15,
        'common_uoms': ['CY', 'SY', 'TON'],
        'description': 'Civil / Infrastructure'
    },
    TradeType.ELECTRICAL: {
        'suggested_margin_min': 0.30,
        'suggested_margin_max': 0.35,
        'default_margin': 0.30,
        'government_margin': 0.18,
        'common_uoms': ['LF', 'EA', 'HR'],
        'description': 'Electrical'
    },
    TradeType.PLUMBING_HVAC: {
        'suggested_margin_min': 0.35,
        'suggested_margin_max': 0.40,
        'default_margin': 0.35,
        'government_margin': 0.20,
        'common_uoms': ['LF', 'EA', 'HR'],
        'description': 'Plumbing / HVAC'
    },
    TradeType.CONCRETE: {
        'suggested_margin_min': 0.20,
        'suggested_margin_max': 0.25,
        'default_margin': 0.20,
        'government_margin': 0.15,
        'common_uoms': ['CY', 'SF', 'LF'],
        'description': 'Concrete'
    },
    TradeType.HOME_BUILDING: {
        'suggested_margin_min': 0.25,
        'suggested_margin_max': 0.35,
        'default_margin': 0.30,
        'government_margin': 0.18,
        'common_uoms': ['SF', 'LF', 'EA'],
        'description': 'Home Building / Residential'
    },
    TradeType.HEAVY_EQUIPMENT: {
        'suggested_margin_min': 0.20,
        'suggested_margin_max': 0.30,
        'default_margin': 0.25,
        'government_margin': 0.15,
        'common_uoms': ['HR', 'DAY', 'WK'],
        'description': 'Heavy Equipment / Rental'
    },
    TradeType.GENERAL_CONSTRUCTION: {
        'suggested_margin_min': 0.25,
        'suggested_margin_max': 0.30,
        'default_margin': 0.25,
        'government_margin': 0.15,
        'common_uoms': ['LS', 'EA', 'SF'],
        'description': 'General Construction'
    }
}


def margin_to_markup(margin_pct: float) -> float:
    """Convert gross margin % to markup %.
    
    Formula: Markup = Margin / (1 - Margin)
    
    Example: 33% margin → 49.3% markup
    """
    if margin_pct >= 1.0:
        raise ValueError("Margin cannot be >= 100%")
    return margin_pct / (1 - margin_pct)


def markup_to_margin(markup_pct: float) -> float:
    """Convert markup % to gross margin %.
    
    Formula: Margin = Markup / (1 + Markup)
    
    Example: 49.3% markup → 33% margin
    """
    return markup_pct / (1 + markup_pct)


class PricingProcessor:
    """
    Processes vendor quotes and calculates composite rates with markup and tax.
    
    Attributes:
        tax_rate (float): Tax rate as decimal (default: 0.0825 for 8.25%)
        margin_rate (float): Margin/markup rate as decimal (default: 0.10 for 10%)
        shipping_cost (float): Pass-through shipping cost (default: 0.00)
        calculation_method (CalculationMethod): How margin and tax are calculated
        invoice_format (InvoiceFormat): How the invoice is presented
        trade_type (TradeType): Construction trade for preset suggestions
        fixed_fee (float): Fixed fee for cost-plus contracts (default: 0.0)
        is_gross_margin (bool): If True, margin_rate is gross margin %; if False, it's markup %
    """
    
    def __init__(self, 
                 tax_rate: float = 0.0825, 
                 margin_rate: float = 0.10,
                 shipping_cost: float = 0.0,
                 calculation_method: CalculationMethod = CalculationMethod.MARGIN_THEN_TAX,
                 invoice_format: InvoiceFormat = InvoiceFormat.DETAILED_AUDIT,
                 trade_type: TradeType = TradeType.TELECOM_FIBER,
                 fixed_fee: float = 0.0,
                 is_gross_margin: bool = False):
        self.tax_rate = tax_rate
        self.is_gross_margin = is_gross_margin
        
        # Convert gross margin to markup if needed
        if is_gross_margin:
            self.gross_margin_rate = margin_rate
            self.margin_rate = margin_to_markup(margin_rate)
        else:
            self.margin_rate = margin_rate
            self.gross_margin_rate = markup_to_margin(margin_rate)
        
        self.shipping_cost = shipping_cost
        self.calculation_method = calculation_method
        self.invoice_format = invoice_format
        self.trade_type = trade_type
        self.fixed_fee = fixed_fee
    
    def calculate_composite_rate(self, unit_cost: float) -> dict:
        """
        Calculate pricing using selected method and return detailed breakdown.
        
        Returns dict with:
            - base_cost: Original unit cost
            - margin_dollars: Dollar amount of margin
            - tax_dollars: Dollar amount of tax
            - composite_rate: Final unit rate
            - method: Calculation method name
            - formula_text: Human-readable formula
            - breakdown_text: Step-by-step calculation
        """
        if pd.isna(unit_cost) or unit_cost == 0:
            return self._empty_result()
        
        # Route to appropriate calculation method
        if self.calculation_method == CalculationMethod.MARGIN_THEN_TAX:
            return self._calc_margin_then_tax(unit_cost)
        elif self.calculation_method == CalculationMethod.TAX_SEPARATE:
            return self._calc_tax_separate(unit_cost)
        elif self.calculation_method == CalculationMethod.ADDITIVE:
            return self._calc_additive(unit_cost)
        elif self.calculation_method == CalculationMethod.COST_PLUS_FIXED_FEE:
            return self._calc_cost_plus(unit_cost)
        else:
            # Default to current behavior
            return self._calc_margin_then_tax(unit_cost)
    
    def _empty_result(self) -> dict:
        """Return empty result for zero/NA costs."""
        return {
            'base_cost': 0.0,
            'margin_dollars': 0.0,
            'tax_dollars': 0.0,
            'composite_rate': 0.0,
            'method': self.calculation_method.value,
            'formula_text': 'N/A',
            'breakdown_text': 'No cost'
        }
    
    def _calc_margin_then_tax(self, cost: float) -> dict:
        """Current default: Cost × (1+Margin) × (1+Tax)"""
        after_margin = cost * (1 + self.margin_rate)
        margin_dollars = cost * self.margin_rate
        tax_dollars = after_margin * self.tax_rate
        composite = after_margin + tax_dollars
        
        return {
            'base_cost': cost,
            'margin_dollars': round(margin_dollars, 2),
            'tax_dollars': round(tax_dollars, 2),
            'composite_rate': round(composite, 2),
            'method': 'Margin-Then-Tax',
            'formula_text': f'${cost:.2f} × (1+{self.margin_rate:.2%}) × (1+{self.tax_rate:.2%})',
            'breakdown_text': (
                f"Cost: ${cost:.2f} → "
                f"After Margin: ${after_margin:.2f} → "
                f"Tax on ${after_margin:.2f}: ${tax_dollars:.2f} → "
                f"Total: ${composite:.2f}"
            )
        }
    
    def _calc_tax_separate(self, cost: float) -> dict:
        """Government standard: (Cost × (1+Margin)) + (Cost × Tax)"""
        margin_dollars = cost * self.margin_rate
        tax_dollars = cost * self.tax_rate  # Tax on ORIGINAL cost
        composite = cost + margin_dollars + tax_dollars
        
        return {
            'base_cost': cost,
            'margin_dollars': round(margin_dollars, 2),
            'tax_dollars': round(tax_dollars, 2),
            'composite_rate': round(composite, 2),
            'method': 'Tax-Separate (Government Standard)',
            'formula_text': f'(${cost:.2f} × (1+{self.margin_rate:.2%})) + (${cost:.2f} × {self.tax_rate:.2%})',
            'breakdown_text': (
                f"Cost: ${cost:.2f} → "
                f"Margin: ${margin_dollars:.2f} → "
                f"Tax on original cost: ${tax_dollars:.2f} → "
                f"Total: ${composite:.2f}"
            )
        }
    
    def _calc_additive(self, cost: float) -> dict:
        """Simplest: Cost × (1 + Margin% + Tax%)"""
        margin_dollars = cost * self.margin_rate
        tax_dollars = cost * self.tax_rate
        composite = cost * (1 + self.margin_rate + self.tax_rate)
        
        return {
            'base_cost': cost,
            'margin_dollars': round(margin_dollars, 2),
            'tax_dollars': round(tax_dollars, 2),
            'composite_rate': round(composite, 2),
            'method': 'Additive',
            'formula_text': f'${cost:.2f} × (1 + {self.margin_rate:.2%} + {self.tax_rate:.2%})',
            'breakdown_text': (
                f"Cost: ${cost:.2f} × "
                f"(1 + {self.margin_rate*100:.1f}% + {self.tax_rate*100:.2f}%) = "
                f"${composite:.2f}"
            )
        }
    
    def _calc_cost_plus(self, cost: float) -> dict:
        """Cost-Plus: Cost + Tax + Fixed Fee (per item or project)"""
        tax_dollars = cost * self.tax_rate
        composite = cost + tax_dollars
        # Fixed fee usually added at project level, not per item
        
        return {
            'base_cost': cost,
            'margin_dollars': 0,  # Fee shown separately
            'tax_dollars': round(tax_dollars, 2),
            'composite_rate': round(composite, 2),
            'method': 'Cost-Plus-Fixed-Fee',
            'formula_text': f'${cost:.2f} + ${tax_dollars:.2f} + Fixed Fee',
            'breakdown_text': (
                f"Cost: ${cost:.2f} → "
                f"Tax: ${tax_dollars:.2f} → "
                f"Subtotal: ${composite:.2f} (+ ${self.fixed_fee:.2f} project fee)"
            )
        }
    
    def get_composite_rate_value(self, unit_cost: float) -> float:
        """Legacy method: returns just the composite rate as float for backward compatibility."""
        result = self.calculate_composite_rate(unit_cost)
        return result['composite_rate']
    
    # ------------------------------------------------------------------
    # Data cleaning
    # ------------------------------------------------------------------
    def clean_vendor_quote(self, df: pd.DataFrame,
                           desc_col: str, qty_col: str,
                           cost_col: str,
                           part_col: str = None,
                           uom_col: str = None,
                           total_col: str = None) -> Tuple[pd.DataFrame, float, float]:
        """
        Clean a raw parsed vendor quote DataFrame.
        
        Phase 1 — Merge multi-line descriptions: vendor PDFs often wrap a
                   single line-item description across 2-4 rows.  Continuation
                   rows (no qty, no cost) are appended to the previous real row.
        Phase 2 — Extract sales tax and freight dollar amounts.
        Phase 3 — Strip junk: vendor headers, repeated column-header rows,
                   empty rows, subtotal markers.
        
        Optional columns (part_col, uom_col, total_col) are stored for downstream use.
        
        Returns:
            (cleaned_df, sales_tax_dollars, freight_dollars)
        """
        # ── Phase 1: merge continuation rows ──────────────────────
        df = self._merge_multiline_rows(df, desc_col, qty_col, cost_col)
        
        # ── Phase 1b: strip commas from qty/cost so "25,035" → 25035 ──
        for col in [qty_col, cost_col]:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # ── Phase 2 & 3: extract tax/freight, strip junk ─────────
        sales_tax = 0.0
        freight = 0.0
        
        header_pattern = re.compile(
            r'^(item|description|u/?m|total|qty|quantity|rate|none|tbd|'
            r'net\s*\d+|a\.?b\.?|estimate|terms|rep|project|col\d+|page)$',
            re.IGNORECASE
        )
        tax_pattern = re.compile(r'sales\s*tax|^tax$', re.IGNORECASE)
        freight_pattern = re.compile(r'freight|shipping', re.IGNORECASE)
        subtotal_pattern = re.compile(r'subtotal|sub\s*total|grand\s*total', re.IGNORECASE)
        
        keep_mask = []
        
        for _, row in df.iterrows():
            desc_val = str(row.get(desc_col, '')).strip()
            qty_val = pd.to_numeric(row.get(qty_col), errors='coerce')
            cost_val = pd.to_numeric(row.get(cost_col), errors='coerce')
            # Build row_text from ALL columns for keyword searching
            row_text = ' '.join(str(v) for v in row.values if pd.notna(v))
            
            # --- Extract sales tax ---
            if tax_pattern.search(row_text):
                # Search ALL cells for the dollar amount (could be in any column)
                for v in row.values:
                    parsed = _parse_currency(v)
                    if parsed and parsed > sales_tax:
                        sales_tax = parsed
                keep_mask.append(False)
                continue
            
            # --- Extract freight ---
            if freight_pattern.search(row_text):
                # Look for a real dollar amount > 1; skip small ints (qty=1)
                row_freight = 0.0
                for v in row.values:
                    parsed = _parse_currency(v)
                    if parsed and parsed > 1.0 and parsed > row_freight:
                        row_freight = parsed
                if row_freight > freight:
                    freight = row_freight
                keep_mask.append(False)
                continue
            
            # --- Remove subtotal rows ---
            if subtotal_pattern.search(row_text):
                keep_mask.append(False)
                continue
            
            # --- Remove repeated column-header / junk rows ---
            if not desc_val or desc_val.lower() == 'none' or header_pattern.match(desc_val):
                keep_mask.append(False)
                continue
            
            # --- Remove rows where qty AND cost are both zero or NaN ---
            if (pd.isna(qty_val) or qty_val == 0) and (pd.isna(cost_val) or cost_val == 0):
                keep_mask.append(False)
                continue
            
            keep_mask.append(True)
        
        cleaned_df = df.loc[df.index[keep_mask]].copy().reset_index(drop=True)
        
        # Ensure numeric columns (already stripped commas above, but be safe)
        cleaned_df[qty_col] = pd.to_numeric(cleaned_df[qty_col], errors='coerce').fillna(0)
        cleaned_df[cost_col] = pd.to_numeric(cleaned_df[cost_col], errors='coerce').fillna(0)
        
        # Store column mappings in attrs for downstream use
        cleaned_df.attrs['desc_col'] = desc_col
        cleaned_df.attrs['qty_col'] = qty_col
        cleaned_df.attrs['cost_col'] = cost_col
        cleaned_df.attrs['part_col'] = part_col
        cleaned_df.attrs['uom_col'] = uom_col
        cleaned_df.attrs['total_col'] = total_col
        
        return cleaned_df, sales_tax, freight
    
    @staticmethod
    def _merge_multiline_rows(df: pd.DataFrame, desc_col: str,
                               qty_col: str, cost_col: str) -> pd.DataFrame:
        """
        Merge multi-line PDF rows into single line-items.
        
        Vendor PDFs typically produce this pattern for each item:
          Row A: part# + description text  (no qty, no cost)
          Row B: continuation description  (no qty, no cost)
          Row C: *** IN-STOCK note ***     (no qty, no cost)
          Row D: 150  ea  8.20  1,230.00T  (HAS qty and cost — the data row)
        
        Strategy: always buffer description-only rows.  When a data row
        arrives (has qty or cost), prepend all buffered descriptions onto
        it, clear the buffer, and emit the merged row.
        """
        # Pattern for junk lines that should never be part of a description.
        # Also matches short generic strings (<=3 words, no part-number chars)
        # that typically appear in vendor page headers.
        junk_line = re.compile(
            r'^(date|estimate|tbd|net\s*\d+|a\.?b\.?|item|description|'
            r'u/?m|total|qty|quantity|rate|terms|rep|project|page|'
            r'col\d+|none|nan)$',
            re.IGNORECASE
        )
        # Short lines (1-3 words, no digits or hyphens) are likely vendor
        # header labels like "Gotebo Resound", "A.B.", "Rep", etc.
        short_header = re.compile(r'^[A-Za-z\s.]+$')
        # Rows that Phase 2 needs to see (tax, freight, subtotal) — pass through
        passthrough = re.compile(
            r'sales\s*tax|^tax$|freight|shipping|subtotal|sub\s*total|grand\s*total',
            re.IGNORECASE
        )
        
        merged_rows: List[pd.Series] = []
        desc_buffer: List[str] = []
        
        for _, row in df.iterrows():
            qty_val = pd.to_numeric(row.get(qty_col), errors='coerce')
            cost_val = pd.to_numeric(row.get(cost_col), errors='coerce')
            desc_val = str(row.get(desc_col, '')).strip()
            
            # Check if any cell in the row contains tax/freight/subtotal keywords
            row_text = ' '.join(str(v) for v in row.values if pd.notna(v))
            if passthrough.search(row_text):
                merged_rows.append(row.copy())
                continue
            
            has_qty = pd.notna(qty_val) and qty_val != 0
            has_cost = pd.notna(cost_val) and cost_val != 0
            
            if has_qty or has_cost:
                # ── Data row ──
                data_row = row.copy()
                
                # Filter junk lines out of the buffer before prepending
                clean_buffer = [
                    ln for ln in desc_buffer
                    if not junk_line.match(ln.strip())
                    and not (short_header.match(ln.strip()) and len(ln.split()) <= 3)
                ]
                
                if clean_buffer:
                    combined_desc = ' '.join(clean_buffer)
                    existing = desc_val
                    # If the data row's desc cell is just a number (the qty
                    # that bled into the desc column), replace it entirely
                    try:
                        float(existing.replace(',', ''))
                        data_row[desc_col] = combined_desc
                    except ValueError:
                        if existing:
                            data_row[desc_col] = (combined_desc + ' ' + existing).strip()
                        else:
                            data_row[desc_col] = combined_desc
                desc_buffer = []
                
                merged_rows.append(data_row)
            else:
                # ── Description-only / note row — always buffer ──
                if desc_val and desc_val.lower() not in ('none', 'nan', ''):
                    desc_buffer.append(desc_val)
        
        if not merged_rows:
            return df
        
        return pd.DataFrame(merged_rows).reset_index(drop=True)
    
    # ------------------------------------------------------------------
    # Quote processing
    # ------------------------------------------------------------------
    def process_quote(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process a cleaned vendor quote DataFrame and add calculated columns.
        
        Reads column mappings from df.attrs (set by clean_vendor_quote).
        
        Adds:
          - Composite Unit Rate = calculated based on selected method
          - Total Price = Composite Unit Rate × Quantity
          - Calculation details (method, formula) stored in additional columns
        """
        processed_df = df.copy()
        
        # Retrieve column mappings from attrs
        desc_col = df.attrs.get('desc_col')
        qty_col = df.attrs.get('qty_col')
        cost_col = df.attrs.get('cost_col')
        part_col = df.attrs.get('part_col')
        uom_col = df.attrs.get('uom_col')
        total_col = df.attrs.get('total_col')
        
        # Ensure numeric columns
        processed_df[cost_col] = pd.to_numeric(processed_df[cost_col], errors='coerce').fillna(0)
        processed_df[qty_col] = pd.to_numeric(processed_df[qty_col], errors='coerce').fillna(0)
        
        # Calculate composite rate using selected method
        # calculate_composite_rate now returns a dict, extract the composite_rate value
        processed_df['Composite Unit Rate'] = processed_df[cost_col].apply(
            lambda cost: self.calculate_composite_rate(cost)['composite_rate']
        )
        
        processed_df['Total Price'] = (
            processed_df[qty_col] * processed_df['Composite Unit Rate']
        ).round(2)
        
        # Store calculation details for audit trail
        calc_details = processed_df[cost_col].apply(self.calculate_composite_rate)
        processed_df['_calc_method'] = calc_details.apply(lambda x: x['method'])
        processed_df['_formula_text'] = calc_details.apply(lambda x: x['formula_text'])
        
        # Preserve all attrs for downstream methods
        processed_df.attrs = df.attrs.copy()
        
        return processed_df
    
    # ------------------------------------------------------------------
    # Internal Audit Spreadsheet (full formula trail for leadership)
    # ------------------------------------------------------------------
    def generate_internal_audit_spreadsheet(self, df: pd.DataFrame, 
                                       tax_rate: float, 
                                       margin_rate: float,
                                       output_path=None,
                                       shipping_cost: float = 0.0) -> pd.DataFrame:
        """
        Full audit trail with dollar-based breakdown (not percentages).
        
        Columns: Part # | Description | UOM | Qty | Vendor Cost | Margin $ | 
                 After Margin | Tax $ | Composite Rate | Line Total | Vendor Total
        
        Example: $10 → +$1 margin → $11 → +$0.91 tax → $11.91 composite
        """
        # Retrieve column mappings from attrs
        desc_col = df.attrs.get('desc_col')
        qty_col = df.attrs.get('qty_col')
        cost_col = df.attrs.get('cost_col')
        part_col = df.attrs.get('part_col')
        uom_col = df.attrs.get('uom_col')
        total_col = df.attrs.get('total_col')
        
        audit_data = []
        for _, row in df.iterrows():
            if not (desc_col and qty_col):
                continue
            if pd.isna(row.get(desc_col)) or pd.isna(row.get(qty_col)):
                continue
            
            quantity = float(pd.to_numeric(row[qty_col], errors='coerce') or 0)
            unit_cost = float(pd.to_numeric(row.get(cost_col, 0), errors='coerce') or 0) if cost_col else 0.0
            
            # Calculate using selected method
            calc_result = self.calculate_composite_rate(unit_cost)
            margin_dollars = calc_result['margin_dollars']
            tax_dollars = calc_result['tax_dollars']
            composite_rate = calc_result['composite_rate']
            
            # For audit trail, also calculate after_margin for display
            after_margin = round(unit_cost + margin_dollars, 2)
            line_total = round(composite_rate * quantity, 2)
            
            # Build row with optional columns
            audit_row = {}
            
            if part_col and pd.notna(row.get(part_col)):
                audit_row['Part Number'] = row[part_col]
            
            audit_row['Description'] = row[desc_col]
            
            if uom_col and pd.notna(row.get(uom_col)):
                audit_row['UOM'] = row[uom_col]
            
            audit_row['Qty'] = quantity
            audit_row['Vendor Unit Cost'] = unit_cost
            
            # Vendor Total Cost = Qty × Vendor Unit Cost
            vendor_total_cost = round(quantity * unit_cost, 2)
            audit_row['Vendor Total Cost'] = vendor_total_cost
            
            audit_row['Margin $'] = margin_dollars
            audit_row['After Margin'] = after_margin
            audit_row['Tax $'] = tax_dollars
            audit_row['Composite Unit Rate'] = composite_rate
            audit_row['Line Total'] = line_total
            
            if total_col and pd.notna(row.get(total_col)):
                vendor_total = pd.to_numeric(row[total_col], errors='coerce')
                if pd.notna(vendor_total):
                    audit_row['Vendor Total (from PDF)'] = float(vendor_total)
            
            # Add calculation method and formula
            audit_row['Calculation Method'] = calc_result['method']
            audit_row['Formula'] = calc_result['breakdown_text'] + f" | Total: ${composite_rate:.2f} × {quantity} = ${line_total:.2f}"
            
            audit_data.append(audit_row)
        
        audit_df = pd.DataFrame(audit_data)
        
        if audit_df.empty:
            return audit_df
        
        # Add shipping line if applicable
        if shipping_cost > 0:
            ship_row = {col: '' for col in audit_df.columns}
            ship_row['Description'] = 'Shipping / Freight (Pass-Through)'
            ship_row['Qty'] = 1
            ship_row['Vendor Unit Cost'] = shipping_cost
            ship_row['Vendor Total Cost'] = shipping_cost
            ship_row['Margin $'] = 0
            ship_row['After Margin'] = shipping_cost
            ship_row['Tax $'] = 0
            ship_row['Composite Unit Rate'] = shipping_cost
            ship_row['Line Total'] = shipping_cost
            ship_row['Formula'] = 'Pass-through (no markup)'
            audit_df = pd.concat([audit_df, pd.DataFrame([ship_row])], ignore_index=True)
        
        # Write to Excel if output_path provided
        if output_path:
            self._write_audit_excel(audit_df, output_path)
        
        return audit_df
    
    @staticmethod
    def _excel_col_letter(col_num):
        """Convert column number to Excel column letter (0 -> A, 1 -> B, etc.)."""
        result = ""
        while col_num >= 0:
            result = chr(col_num % 26 + 65) + result
            col_num = col_num // 26 - 1
        return result
    
    def _write_audit_excel(self, audit_df, output_path):
        """Write audit DataFrame with Excel formulas in calculated cells."""
        is_buffer = hasattr(output_path, 'write')
        
        if is_buffer:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                temp_path = tmp.name
            target = temp_path
        else:
            target = output_path
        
        with pd.ExcelWriter(target, engine='xlsxwriter') as writer:
            audit_df.to_excel(writer, sheet_name='Audit_Details', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Audit_Details']
            
            header_fmt = workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top',
                'fg_color': '#D7E4BC', 'border': 1
            })
            money_fmt = workbook.add_format({'num_format': '$#,##0.00'})
            totals_fmt = workbook.add_format({
                'bold': True, 'bg_color': '#E2EFDA', 'border': 1,
                'num_format': '$#,##0.00'
            })
            
            money_cols = ['Vendor Unit Cost', 'Vendor Total Cost', 'Margin $', 'After Margin',
                          'Tax $', 'Composite Unit Rate', 'Line Total', 'Vendor Total (from PDF)']
            
            # Map column names to Excel column letters
            col_map = {}
            for col_num, column in enumerate(audit_df.columns):
                col_letter = self._excel_col_letter(col_num)
                col_map[column] = col_letter
                
                worksheet.write(0, col_num, column, header_fmt)
                if column == 'Description':
                    worksheet.set_column(col_num, col_num, 45)
                elif column == 'Part Number':
                    worksheet.set_column(col_num, col_num, 18)
                elif column == 'Formula':
                    worksheet.set_column(col_num, col_num, 80)  # Wide column for formula text
                elif column in money_cols:
                    worksheet.set_column(col_num, col_num, 14, money_fmt)
                elif column == 'UOM':
                    worksheet.set_column(col_num, col_num, 8)
                else:
                    worksheet.set_column(col_num, col_num, 10)
            
            # Write formulas for calculated columns (rows 2 to n-1, skipping totals row)
            num_data_rows = len(audit_df) - 1  # Exclude totals row
            
            for row_idx in range(num_data_rows):
                excel_row = row_idx + 2  # Excel is 1-indexed, +1 for header
                
                # Get column letters
                vendor_cost_col = col_map.get('Vendor Unit Cost')
                vendor_total_cost_col = col_map.get('Vendor Total Cost')
                margin_col = col_map.get('Margin $')
                after_margin_col = col_map.get('After Margin')
                tax_col = col_map.get('Tax $')
                composite_col = col_map.get('Composite Unit Rate')
                qty_col = col_map.get('Qty')
                line_total_col = col_map.get('Line Total')
                
                # Vendor Total Cost = Qty * Vendor Unit Cost
                if vendor_total_cost_col and qty_col and vendor_cost_col:
                    formula = f'={qty_col}{excel_row}*{vendor_cost_col}{excel_row}'
                    worksheet.write_formula(excel_row - 1, audit_df.columns.get_loc('Vendor Total Cost'), 
                                          formula, money_fmt)
                
                # Margin $ = Vendor Unit Cost * margin_rate
                if margin_col and vendor_cost_col:
                    margin_rate = self.margin_rate
                    formula = f'={vendor_cost_col}{excel_row}*{margin_rate}'
                    worksheet.write_formula(excel_row - 1, audit_df.columns.get_loc('Margin $'), 
                                          formula, money_fmt)
                
                # After Margin = Vendor Unit Cost + Margin $
                if after_margin_col and vendor_cost_col and margin_col:
                    formula = f'={vendor_cost_col}{excel_row}+{margin_col}{excel_row}'
                    worksheet.write_formula(excel_row - 1, audit_df.columns.get_loc('After Margin'), 
                                          formula, money_fmt)
                
                # Tax $ = After Margin * tax_rate
                if tax_col and after_margin_col:
                    tax_rate = self.tax_rate
                    formula = f'={after_margin_col}{excel_row}*{tax_rate}'
                    worksheet.write_formula(excel_row - 1, audit_df.columns.get_loc('Tax $'), 
                                          formula, money_fmt)
                
                # Composite Unit Rate = After Margin + Tax $
                if composite_col and after_margin_col and tax_col:
                    formula = f'={after_margin_col}{excel_row}+{tax_col}{excel_row}'
                    worksheet.write_formula(excel_row - 1, audit_df.columns.get_loc('Composite Unit Rate'), 
                                          formula, money_fmt)
                
                # Line Total = Composite Unit Rate * Qty
                if line_total_col and composite_col and qty_col:
                    formula = f'={composite_col}{excel_row}*{qty_col}{excel_row}'
                    worksheet.write_formula(excel_row - 1, audit_df.columns.get_loc('Line Total'), 
                                          formula, money_fmt)
            
            # Totals row with SUM formulas (add new row after all data)
            totals_row = len(audit_df) + 1  # Excel row number for totals (new row)
            for col_num, column in enumerate(audit_df.columns):
                if column == 'Description':
                    worksheet.write(totals_row, col_num, 'TOTALS', totals_fmt)
                elif column in ['Qty', 'Vendor Total Cost', 'Margin $', 'After Margin', 'Tax $', 'Line Total', 'Vendor Total (from PDF)']:
                    col_letter = self._excel_col_letter(col_num)
                    # SUM from row 2 to last data row
                    formula = f'=SUM({col_letter}2:{col_letter}{len(audit_df) + 1})'
                    worksheet.write_formula(totals_row, col_num, formula, totals_fmt)
                else:
                    worksheet.write(totals_row, col_num, '', totals_fmt)
        
        if is_buffer:
            with open(temp_path, 'rb') as f:
                output_path.write(f.read())
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    # ------------------------------------------------------------------
    # Client Spreadsheet (3 columns: Description | Composite Unit Rate | Total)
    # ------------------------------------------------------------------
    def generate_client_spreadsheet(self, df: pd.DataFrame, 
                                   output_path=None,
                                   shipping_cost: float = 0.0) -> pd.DataFrame:
        """
        Generate clean client-facing spreadsheet with 6 columns:
        Part # | Description | UOM | Qty | Composite Unit Rate | Total
        
        Shows client what they're ordering with part numbers for easy reference.
        """
        # Retrieve column mappings from attrs
        desc_col = df.attrs.get('desc_col')
        qty_col = df.attrs.get('qty_col')
        part_col = df.attrs.get('part_col')
        uom_col = df.attrs.get('uom_col')
        
        # Build client view with optional columns
        rows = []
        for _, row in df.iterrows():
            if desc_col and pd.notna(row.get(desc_col)):
                client_row = {}
                
                if part_col and pd.notna(row.get(part_col)):
                    client_row['Part Number'] = row[part_col]
                
                client_row['Description'] = row[desc_col]
                
                if uom_col and pd.notna(row.get(uom_col)):
                    client_row['UOM'] = row[uom_col]
                
                if qty_col and pd.notna(row.get(qty_col)):
                    client_row['Qty'] = row[qty_col]
                
                client_row['Composite Unit Rate'] = row.get('Composite Unit Rate', 0)
                client_row['Total'] = row.get('Total Price', 0)
                
                rows.append(client_row)
        
        client_df = pd.DataFrame(rows)
        
        # Add shipping line
        if shipping_cost > 0:
            ship_row = {col: '' for col in client_df.columns}
            ship_row['Description'] = 'Shipping / Freight'
            if 'Qty' in client_df.columns:
                ship_row['Qty'] = 1
            ship_row['Composite Unit Rate'] = shipping_cost
            ship_row['Total'] = shipping_cost
            client_df = pd.concat([client_df, pd.DataFrame([ship_row])], ignore_index=True)
        
        # Write to Excel if output_path provided
        if output_path:
            self._write_client_excel(client_df, output_path)
        
        return client_df
    
    def _write_client_excel(self, client_df, output_path):
        """Write the client DataFrame to a formatted Excel file or BytesIO buffer with formulas."""
        is_buffer = hasattr(output_path, 'write')
        
        if is_buffer:
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
                temp_path = tmp.name
            target = temp_path
        else:
            target = output_path
        
        with pd.ExcelWriter(target, engine='xlsxwriter') as writer:
            client_df.to_excel(writer, sheet_name='Quote', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Quote']
            
            money_fmt = workbook.add_format({'num_format': '$#,##0.00'})
            header_fmt = workbook.add_format({
                'bold': True, 'fg_color': '#4472C4', 'font_color': 'white',
                'border': 1
            })
            totals_fmt = workbook.add_format({
                'bold': True, 'bg_color': '#D0E0F0', 'border': 1,
                'num_format': '$#,##0.00'
            })
            
            # Map column names to Excel column letters
            col_map = {}
            for col_num, column in enumerate(client_df.columns):
                col_letter = self._excel_col_letter(col_num)
                col_map[column] = col_letter
                
                worksheet.write(0, col_num, column, header_fmt)
                if column == 'Description':
                    worksheet.set_column(col_num, col_num, 45)
                elif column == 'Part Number':
                    worksheet.set_column(col_num, col_num, 18)
                elif column == 'UOM':
                    worksheet.set_column(col_num, col_num, 8)
                elif column == 'Qty':
                    worksheet.set_column(col_num, col_num, 10)
                elif column in ['Composite Unit Rate', 'Total']:
                    worksheet.set_column(col_num, col_num, 16, money_fmt)
                else:
                    worksheet.set_column(col_num, col_num, 12)
            
            # Write formulas for Total column (rows 2 to n)
            num_data_rows = len(client_df)
            
            for row_idx in range(num_data_rows):
                excel_row = row_idx + 2  # Excel is 1-indexed, +1 for header
                
                # Get column letters
                rate_col = col_map.get('Composite Unit Rate')
                total_col = col_map.get('Total')
                qty_col = col_map.get('Qty')
                
                # Total = Composite Unit Rate * Qty
                if total_col and rate_col and qty_col:
                    formula = f'={rate_col}{excel_row}*{qty_col}{excel_row}'
                    worksheet.write_formula(excel_row - 1, client_df.columns.get_loc('Total'), 
                                          formula, money_fmt)
            
            # Totals row with SUM formulas (add new row after all data)
            totals_row = len(client_df) + 1  # Excel row number for totals (new row)
            for col_num, column in enumerate(client_df.columns):
                if column == 'Description':
                    worksheet.write(totals_row, col_num, 'TOTALS', totals_fmt)
                elif column in ['Qty', 'Total']:
                    col_letter = self._excel_col_letter(col_num)
                    # SUM from row 2 to last data row
                    formula = f'=SUM({col_letter}2:{col_letter}{len(client_df) + 1})'
                    worksheet.write_formula(totals_row, col_num, formula, totals_fmt)
                else:
                    worksheet.write(totals_row, col_num, '', totals_fmt)
        
        if is_buffer:
            with open(temp_path, 'rb') as f:
                output_path.write(f.read())
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    # ------------------------------------------------------------------
    # Summary Report Generator (Markdown / .docx / Excel)
    # ------------------------------------------------------------------
    def generate_summary_report(self, processed_df: pd.DataFrame,
                                fmt: str = 'md',
                                shipping_cost: float = 0.0,
                                extracted_tax: float = 0.0,
                                extracted_freight: float = 0.0) -> str:
        """
        Generate a summary report of the processed quote.
        
        Args:
            processed_df: DataFrame after process_quote()
            fmt: Output format — 'md' for Markdown, 'docx' for Word
            shipping_cost: Pass-through shipping entered by user
            extracted_tax: Sales tax dollar amount extracted from vendor quote
            extracted_freight: Freight dollar amount extracted from vendor quote
            
        Returns:
            For 'md': Markdown string
            For 'docx': bytes of the .docx file
        """
        desc_col = processed_df.attrs.get('desc_col', 'Description')
        qty_col = processed_df.attrs.get('qty_col', 'Qty')
        cost_col = processed_df.attrs.get('cost_col', 'Unit Cost')
        
        # Calculate totals
        line_items = len(processed_df)
        vendor_subtotal = round(
            (pd.to_numeric(processed_df[cost_col], errors='coerce').fillna(0) *
             pd.to_numeric(processed_df[qty_col], errors='coerce').fillna(0)).sum(), 2)
        total_composite = round(processed_df['Total Price'].sum(), 2)
        total_margin = round(total_composite - vendor_subtotal - extracted_tax, 2)
        effective_margin_pct = round((total_margin / vendor_subtotal * 100), 2) if vendor_subtotal else 0
        grand_total = round(total_composite + shipping_cost, 2)
        
        if fmt == 'md':
            return self._summary_as_markdown(
                processed_df, desc_col, qty_col, line_items,
                vendor_subtotal, total_margin, effective_margin_pct,
                extracted_tax, extracted_freight, shipping_cost,
                total_composite, grand_total)
        elif fmt == 'docx':
            return self._summary_as_docx(
                processed_df, desc_col, qty_col, line_items,
                vendor_subtotal, total_margin, effective_margin_pct,
                extracted_tax, extracted_freight, shipping_cost,
                total_composite, grand_total)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
    
    def _summary_as_markdown(self, df, desc_col, qty_col, line_items,
                              vendor_subtotal, total_margin, margin_pct,
                              extracted_tax, extracted_freight, shipping,
                              total_composite, grand_total) -> str:
        lines = [
            "# Quote Summary Report",
            "",
            f"**Line Items:** {line_items}",
            f"**Margin Rate:** {self.margin_rate*100:.1f}%",
            f"**Tax Rate:** {self.tax_rate*100:.2f}%",
            "",
            "## Line Items",
            "",
            "| Description | Composite Unit Rate | Total |",
            "|---|---|---|",
        ]
        for _, row in df.iterrows():
            desc = str(row.get(desc_col, ''))[:60]
            rate = f"${row.get('Composite Unit Rate', 0):,.2f}"
            total = f"${row.get('Total Price', 0):,.2f}"
            lines.append(f"| {desc} | {rate} | {total} |")
        
        lines.extend([
            "",
            "## Totals",
            "",
            f"| Vendor Subtotal | ${vendor_subtotal:,.2f} |",
            f"| Margin ({self.margin_rate*100:.1f}%) | ${total_margin:,.2f} ({margin_pct:.1f}% effective) |",
            f"| Extracted Sales Tax | ${extracted_tax:,.2f} |",
            f"| Extracted Freight | ${extracted_freight:,.2f} |",
            f"| Quote Total (with markup + tax) | ${total_composite:,.2f} |",
            f"| Pass-Through Shipping | ${shipping:,.2f} |",
            f"| **Grand Total** | **${grand_total:,.2f}** |",
        ])
        return "\n".join(lines)
    
    def _summary_as_docx(self, df, desc_col, qty_col, line_items,
                          vendor_subtotal, total_margin, margin_pct,
                          extracted_tax, extracted_freight, shipping,
                          total_composite, grand_total) -> bytes:
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            raise ImportError("python-docx is required for .docx export. "
                              "Install it with: pip install python-docx")
        
        doc = Document()
        doc.add_heading('Quote Summary Report', 0)
        
        doc.add_paragraph(f'Line Items: {line_items}')
        doc.add_paragraph(f'Margin Rate: {self.margin_rate*100:.1f}%')
        doc.add_paragraph(f'Tax Rate: {self.tax_rate*100:.2f}%')
        
        doc.add_heading('Line Items', level=1)
        table = doc.add_table(rows=1, cols=3)
        table.style = 'Light Grid Accent 1'
        hdr = table.rows[0].cells
        hdr[0].text = 'Description'
        hdr[1].text = 'Composite Unit Rate'
        hdr[2].text = 'Total'
        
        for _, row in df.iterrows():
            r = table.add_row().cells
            r[0].text = str(row.get(desc_col, ''))[:80]
            r[1].text = f"${row.get('Composite Unit Rate', 0):,.2f}"
            r[2].text = f"${row.get('Total Price', 0):,.2f}"
        
        doc.add_heading('Totals', level=1)
        totals_data = [
            ('Vendor Subtotal', f'${vendor_subtotal:,.2f}'),
            (f'Margin ({self.margin_rate*100:.1f}%)',
             f'${total_margin:,.2f} ({margin_pct:.1f}% effective)'),
            ('Extracted Sales Tax', f'${extracted_tax:,.2f}'),
            ('Quote Total', f'${total_composite:,.2f}'),
            ('Pass-Through Shipping', f'${shipping:,.2f}'),
            ('Grand Total', f'${grand_total:,.2f}'),
        ]
        t2 = doc.add_table(rows=len(totals_data), cols=2)
        t2.style = 'Light Grid Accent 1'
        for i, (label, val) in enumerate(totals_data):
            t2.rows[i].cells[0].text = label
            t2.rows[i].cells[1].text = val
        
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()


# ======================================================================
# Module-level helpers
# ======================================================================

def _parse_currency(value) -> Optional[float]:
    """Try to parse a value as a dollar amount. Returns float or None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = str(value).strip().replace('$', '').replace(',', '').replace('T', '')
    try:
        v = float(s)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def parse_vendor_spreadsheet(file_path: str, sheet_name: str = 'Vendor Quote Sheet') -> pd.DataFrame:
    """Parse the vendor spreadsheet format."""
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
    df = df.dropna(how='all')
    df = df[~df.iloc[:, 0].astype(str).str.contains('Subtotal|tax|Vendor Invoice|markup', na=False)]
    return df
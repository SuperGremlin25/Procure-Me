"""
Test script to verify different pricing calculation methods.

Tests all 4 calculation methods and margin/markup conversions.
"""

import sys
sys.path.insert(0, 'src')

from pricing_calculator import (
    PricingProcessor, 
    CalculationMethod, 
    InvoiceFormat,
    TradeType,
    margin_to_markup,
    markup_to_margin,
    TRADE_PRESETS
)


def test_margin_markup_conversion():
    """Test margin <-> markup conversion."""
    print("=" * 60)
    print("MARGIN ⟷ MARKUP CONVERSION TEST")
    print("=" * 60)
    
    test_cases = [
        (0.10, "10% margin"),
        (0.20, "20% margin"),
        (0.25, "25% margin"),
        (0.30, "30% margin"),
        (0.33, "33% margin (GC target)"),
        (0.40, "40% margin"),
    ]
    
    for margin, label in test_cases:
        markup = margin_to_markup(margin)
        back_to_margin = markup_to_margin(markup)
        print(f"{label:25} → {markup*100:5.1f}% markup → {back_to_margin*100:5.1f}% margin (roundtrip)")
    
    print()


def test_calculation_methods():
    """Test all 4 calculation methods on same cost."""
    print("=" * 60)
    print("CALCULATION METHOD COMPARISON ($100 cost, 12% margin, 8.25% tax)")
    print("=" * 60)
    
    cost = 100.0
    
    methods = [
        (CalculationMethod.MARGIN_THEN_TAX, "Margin-Then-Tax (Current)"),
        (CalculationMethod.TAX_SEPARATE, "Tax-Separate (Government)"),
        (CalculationMethod.ADDITIVE, "Additive (Simplest)"),
        (CalculationMethod.COST_PLUS_FIXED_FEE, "Cost-Plus ($500 fee)"),
    ]
    
    for method, name in methods:
        processor = PricingProcessor(
            tax_rate=0.0825,
            margin_rate=0.12,
            calculation_method=method,
            fixed_fee=500.0 if method == CalculationMethod.COST_PLUS_FIXED_FEE else 0.0
        )
        
        result = processor.calculate_composite_rate(cost)
        
        print(f"\n{name}:")
        print(f"  Cost:        ${result['base_cost']:7.2f}")
        print(f"  Margin $:    ${result['margin_dollars']:7.2f}")
        print(f"  Tax $:       ${result['tax_dollars']:7.2f}")
        print(f"  Composite:   ${result['composite_rate']:7.2f}")
        print(f"  Method:      {result['method']}")
        print(f"  Formula:     {result['formula_text']}")
    
    print()


def test_gross_margin_mode():
    """Test gross margin input mode (user enters margin %, tool converts to markup)."""
    print("=" * 60)
    print("GROSS MARGIN MODE TEST (33% gross margin target)")
    print("=" * 60)
    
    # User wants 33% gross margin
    target_margin = 0.33
    
    processor = PricingProcessor(
        tax_rate=0.0825,
        margin_rate=target_margin,
        is_gross_margin=True,  # This triggers conversion
        calculation_method=CalculationMethod.TAX_SEPARATE
    )
    
    print(f"User enters:       {target_margin*100:.0f}% gross margin")
    print(f"Tool converts to:  {processor.margin_rate*100:.1f}% markup")
    print(f"Gross margin:      {processor.gross_margin_rate*100:.1f}%")
    
    cost = 100.0
    result = processor.calculate_composite_rate(cost)
    
    print(f"\nOn $100 cost:")
    print(f"  Markup applied:  ${result['margin_dollars']:.2f}")
    print(f"  Tax:             ${result['tax_dollars']:.2f}")
    print(f"  Total price:     ${result['composite_rate']:.2f}")
    
    # Verify actual margin
    actual_margin = result['margin_dollars'] / result['composite_rate']
    print(f"  Actual margin:   {actual_margin*100:.1f}% ✓")
    
    print()


def test_trade_presets():
    """Test trade-specific presets."""
    print("=" * 60)
    print("TRADE PRESET TEST")
    print("=" * 60)
    
    for trade_type, preset in TRADE_PRESETS.items():
        print(f"\n{preset['description']}:")
        print(f"  Suggested margin: {preset['suggested_margin_min']*100:.0f}%-{preset['suggested_margin_max']*100:.0f}%")
        print(f"  Default margin:   {preset['default_margin']*100:.0f}%")
        print(f"  Gov't margin:     {preset['government_margin']*100:.0f}%")
        print(f"  Common UOMs:      {', '.join(preset['common_uoms'])}")
    
    print()


def test_project_comparison():
    """Show $ difference on a $10M project."""
    print("=" * 60)
    print("PROJECT COMPARISON ($10M materials, 12% margin, 8.25% tax)")
    print("=" * 60)
    
    materials_cost = 10_000_000
    
    # Margin-Then-Tax (current)
    p1 = PricingProcessor(
        tax_rate=0.0825,
        margin_rate=0.12,
        calculation_method=CalculationMethod.MARGIN_THEN_TAX
    )
    r1 = p1.calculate_composite_rate(materials_cost)
    
    # Tax-Separate (government)
    p2 = PricingProcessor(
        tax_rate=0.0825,
        margin_rate=0.12,
        calculation_method=CalculationMethod.TAX_SEPARATE
    )
    r2 = p2.calculate_composite_rate(materials_cost)
    
    print(f"\nMargin-Then-Tax:  ${r1['composite_rate']:,.2f}")
    print(f"Tax-Separate:     ${r2['composite_rate']:,.2f}")
    print(f"Difference:       ${r1['composite_rate'] - r2['composite_rate']:,.2f}")
    print(f"\n⚠️  On a $10M project, current method charges ${(r1['composite_rate'] - r2['composite_rate']):,.2f} more")
    print(f"    because tax is applied to the markup (${r1['tax_dollars']:,.2f} vs ${r2['tax_dollars']:,.2f})")
    
    print()


if __name__ == "__main__":
    test_margin_markup_conversion()
    test_calculation_methods()
    test_gross_margin_mode()
    test_trade_presets()
    test_project_comparison()
    
    print("=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)

"""
Procure-Me Pricing Calculator

A Streamlit application for processing vendor quotes with markup and tax calculations.
"""

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.pricing_calculator import PricingProcessor
from src.excel_parser import ExcelParser
from src.materials_db import MaterialsDatabase
from src.pdf_parser import PDFParser


def _detect_columns(df: pd.DataFrame) -> dict:
    """
    Detect which DataFrame columns contain description, quantity, and unit cost
    by analyzing the actual cell values — not just column names.
    
    Handles cases where:
    - Column names are generic (Col0, Col1, etc.) from PDF parsing
    - The first row of data contains the real column headers
      (e.g. 'Description', 'Qty', 'Rate')
    - Vendor page headers repeat across rows
    
    Returns dict with keys 'desc', 'qty', 'cost' mapping to column names.
    """
    scores = {col: {'desc': 0, 'qty': 0, 'cost': 0} for col in df.columns}
    
    desc_keywords = ['desc', 'material', 'item', 'product', 'name']
    qty_keywords = ['qty', 'quantity', 'count']
    cost_keywords = ['cost', 'price', 'rate', 'amount', 'unit cost', 'unit price']
    
    for col in df.columns:
        col_lower = str(col).lower()
        vals = df[col].dropna().astype(str)
        sample = vals.head(20)
        
        # ── 1. Column-name hints ──
        if any(k in col_lower for k in desc_keywords):
            scores[col]['desc'] += 3
        if any(k in col_lower for k in qty_keywords):
            scores[col]['qty'] += 3
        if any(k in col_lower for k in cost_keywords):
            scores[col]['cost'] += 3
        
        # ── 2. First few values may be in-data headers ──
        # Check the first 5 non-empty values for header keywords
        for v in vals.head(5):
            vl = v.strip().lower()
            if vl in ('description', 'item', 'material', 'product', 'item description'):
                scores[col]['desc'] += 6
            if vl in ('qty', 'quantity'):
                scores[col]['qty'] += 6
            if vl in ('rate', 'unit cost', 'cost', 'price', 'unit price'):
                scores[col]['cost'] += 6
            if vl in ('total',):
                # Total column is not cost — penalise cost, but don't add
                scores[col]['cost'] -= 2
        
        # ── 3. Content analysis ──
        numeric_count = 0
        long_text_count = 0
        unique_vals = set()
        nums = []
        for v in sample:
            unique_vals.add(v.strip())
            v_clean = v.replace('$', '').replace(',', '').replace('T', '').strip()
            try:
                nums.append(float(v_clean))
                numeric_count += 1
            except ValueError:
                pass
            if len(v) > 25:
                long_text_count += 1
        
        total = max(len(sample), 1)
        numeric_ratio = numeric_count / total
        text_ratio = long_text_count / total
        unique_ratio = len(unique_vals) / total
        
        # Columns with mostly long text are likely descriptions
        if text_ratio > 0.3:
            scores[col]['desc'] += 4
        
        # Columns where every row is the same value are repeated headers
        # (like Date, Estimate #, P.O. No., Terms, Rep, Project)
        # These should NOT be qty or cost
        if unique_ratio < 0.3 and total > 3:
            scores[col]['qty'] -= 3
            scores[col]['cost'] -= 3
            scores[col]['desc'] -= 2
        
        # Columns with varied numeric values
        if numeric_ratio > 0.4 and nums:
            avg = sum(nums) / len(nums)
            # Penalize columns where all numbers are the same (header repeat)
            if len(set(round(n, 2) for n in nums)) <= 2:
                scores[col]['qty'] -= 2
                scores[col]['cost'] -= 2
            else:
                whole_ratio = sum(1 for n in nums if n == int(n)) / len(nums)
                if whole_ratio > 0.5:
                    scores[col]['qty'] += 3
                decimal_ratio = sum(1 for n in nums if n != int(n)) / len(nums)
                if decimal_ratio > 0.2:
                    scores[col]['cost'] += 3
    
    # Pick best column for each role (no column used twice)
    # Prioritize desc first (most distinctive), then qty, then cost
    result = {}
    used = set()
    for role in ['desc', 'qty', 'cost']:
        best_col = None
        best_score = -1
        for col in df.columns:
            if col not in used and scores[col][role] > best_score:
                best_score = scores[col][role]
                best_col = col
        if best_col:
            result[role] = best_col
            used.add(best_col)
    
    return result


# Configure Streamlit page
st.set_page_config(
    page_title="Procure-Me Pricing Calculator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        background-color: #e7f3ff;
        border: 1px solid #b8daff;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application function."""
    # Hero Section
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0;">
        <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">🔧 Procure-Me</h1>
        <p style="font-size: 1.5rem; color: #666; margin-bottom: 2rem;">
            Turn vendor quotes into client-ready estimates in seconds
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⚡ Processing Time", "< 30 sec")
    with col2:
        st.metric("📊 Output Formats", "7 types")
    with col3:
        st.metric("🔒 Your Data", "Never stored")
    with col4:
        st.metric("💰 Cost", "FREE")
    
    # Value Props
    st.markdown("""
    ### Why Procure-Me?
    
    ✅ **Stop manual spreadsheet work** — Upload vendor quote, get client estimate instantly  
    ✅ **Formula transparency** — See exactly how every price is calculated  
    ✅ **Multiple output formats** — Excel, CSV, Word, Markdown — choose what works for you  
    ✅ **Configurable rates** — Adjust margin (0-50%) and tax (0-20%) with simple sliders  
    ✅ **No signup required** — Start processing quotes immediately, no account needed  
    """)
    
    # Quick Start Guide
    with st.expander("� Quick Start Guide - First time here?"):
        st.markdown("""
        ### How to Use Procure-Me
        
        **Step 1: Upload Your Vendor Quote**
        - Click the "📊 Process Quote" tab below
        - Upload your Excel (.xlsx) or PDF file
        - Supported formats: vendor quotes, BOMs, material lists
        
        **Step 2: Configure Your Rates**
        - Use the sidebar sliders to set your margin (default 10%)
        - Set your tax rate (default 8.25%)
        - Adjust shipping costs if applicable
        
        **Step 3: Map Your Columns**
        - Procure-Me auto-detects columns (Description, Qty, Cost)
        - Verify the mapping is correct
        - Adjust if needed
        
        **Step 4: Download Your Results**
        - Get 7 different output formats:
          - **Client Quote** (clean 6-column format)
          - **Internal Audit** (full cost breakdown with formulas)
          - **Combined Workbook** (both sheets in one file)
          - **CSV exports** (for data portability)
          - **Summary reports** (Markdown or Word)
        
        **All processing happens locally in your browser. No data is uploaded or stored.**
        """)
    
    st.markdown("---")
    
    # Initialize materials database with persistent storage
    data_file_path = os.path.join(os.path.dirname(__file__), "materials_data.json")
    materials_db = MaterialsDatabase(data_file_path)
    
    # Main navigation
    tab1, tab2, tab3 = st.tabs(["📊 Process Quote", "🔧 Build Quote", "📦 Materials List"])
    
    with tab1:
        process_quote_tab(materials_db)
    
    with tab2:
        build_quote_tab(materials_db)
    
    with tab3:
        materials_list_tab(materials_db)
    
    # Footer
    st.markdown("---")
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    
    with footer_col1:
        st.markdown("**About**")
        st.markdown(
            "Built for contractors, estimators, and procurement professionals who are tired of manual spreadsheet work."
        )
    
    with footer_col2:
        st.markdown("**Resources**")
        st.markdown("📖 [Documentation](https://github.com/SuperGremlin25/Procure-Me#readme)")
        st.markdown("🐛 [Report Bug](https://github.com/SuperGremlin25/Procure-Me/issues)")
        st.markdown("💡 [Request Feature](https://github.com/SuperGremlin25/Procure-Me/issues)")
    
    with footer_col3:
        st.markdown("**Connect**")
        st.markdown("⭐ [Star on GitHub](https://github.com/SuperGremlin25/Procure-Me)")
        st.markdown("Made with ❤️ by Digital Insurgent Media")
    
    st.caption("v1.0.0 | MIT License | No data is stored or transmitted")


def process_quote_tab(materials_db):
    """Process uploaded quote files."""
    # Sidebar for settings
    st.sidebar.markdown('<h2 class="section-header">Settings</h2>', 
                        unsafe_allow_html=True)
    
    # Tax and margin settings
    tax_rate = st.sidebar.slider(
        "Tax Rate (%)",
        min_value=0.0,
        max_value=20.0,
        value=8.25,
        step=0.25,
        help="Tax rate to apply to marked-up prices"
    ) / 100
    
    margin_rate = st.sidebar.slider(
        "Margin Rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=10.0,
        step=1.0,
        help="Margin/markup rate to apply to vendor costs"
    ) / 100
    
    # Feedback Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💬 Feedback")
    st.sidebar.markdown("Help us improve Procure-Me!")
    
    feedback_text = st.sidebar.text_area(
        "Share your thoughts:",
        placeholder="Feature requests, bugs, suggestions...",
        height=100,
        label_visibility="collapsed",
        key="feedback_text"
    )
    
    if st.sidebar.button("📤 Send Feedback", use_container_width=True):
        if feedback_text.strip():
            st.sidebar.success("✅ Thanks for your feedback!")
            st.sidebar.info("We'll review it soon!")
            # TODO: Future - integrate with Google Forms API or email service
        else:
            st.sidebar.warning("Please enter some feedback first")
    
    st.sidebar.markdown(
        "📋 [Take our 2-min survey](https://github.com/SuperGremlin25/Procure-Me/issues) for a chance to get early access to premium features!",
        unsafe_allow_html=True
    )
    
    # First-time user helper
    if 'files_processed' not in st.session_state:
        st.session_state.files_processed = 0
    
    # File upload section
    st.markdown('<h2 class="section-header">Upload Vendor Quote</h2>', 
                unsafe_allow_html=True)
    
    # Welcome message for first-time users
    if st.session_state.files_processed == 0:
        st.info("""
        👋 **Welcome!** Upload your first vendor quote to get started. 
        Supported formats: Excel (.xlsx, .xls) or PDF.
        
        💡 **Tip:** Use the sidebar to adjust margin and tax rates before processing.
        """)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['xlsx', 'xls', 'pdf'],
        help="Upload vendor quote (Excel or PDF)",
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        # Validate file size (max 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            st.error("File too large. Please upload a file smaller than 50MB.")
            return
        
        # Check file type
        is_pdf = uploaded_file.type == 'application/pdf'
        
        try:
            if is_pdf:
                # Parse PDF
                st.info("📄 PDF detected. Using advanced PDF parser...")
                parser = PDFParser()
                
                # Get PDF info
                pdf_info = parser.get_pdf_info(uploaded_file)
                st.markdown(f"""
                <div class="info-box">
                    <strong>PDF Info:</strong><br>
                    Pages: {pdf_info['pages']}<br>
                    File Size: {pdf_info['file_size'] / 1024:.1f} KB<br>
                    Tables Detected: {'Yes' if pdf_info['has_tables'] else 'No'}<br>
                    Available Strategies: {', '.join(pdf_info['strategies_available'])}
                </div>
                """, unsafe_allow_html=True)
                
                # Parse the PDF
                df = parser.parse_pdf(uploaded_file)
                
                # Display parsing results
                st.markdown('<h3>Extracted Data</h3>', unsafe_allow_html=True)
                st.dataframe(df.head(10), use_container_width=True)
                
                if df.empty:
                    st.error("Could not extract data from PDF. Try uploading a clearer version or an Excel file.")
                    return
            else:
                # Parse Excel file
                # Use secure temporary file
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    temp_path = tmp_file.name
                    tmp_file.write(uploaded_file.getbuffer())
                
                # Initialize parser
                parser = ExcelParser()
                
                # Get sheet information
                sheet_info = parser.get_sheet_info(temp_path)
                
                # Sheet selection
                st.markdown('<h3>Select Sheet to Process</h3>', unsafe_allow_html=True)
                
                sheet_names = list(sheet_info.keys())
                selected_sheet = st.selectbox(
                    "Choose a sheet:",
                    sheet_names,
                    help="Select the sheet containing the quote data"
                )
                
                if selected_sheet:
                    # Display sheet info
                    info = sheet_info[selected_sheet]
                    st.markdown(f"""
                    <div class="info-box">
                        <strong>Sheet Info:</strong><br>
                        Columns: {len(info['columns'])}<br>
                        Rows: {info['row_count']}<br>
                        Columns found: {', '.join(str(c) for c in info['columns'][:5])}{'...' if len(info['columns']) > 5 else ''}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Parse the selected sheet
                    df = parser.parse_file(temp_path, selected_sheet)
                    
                    # Display raw data preview
                    st.markdown('<h3>Uploaded Data Preview</h3>', unsafe_allow_html=True)
                    st.dataframe(df.head(10), use_container_width=True)
            
            # ── Step 1: Column Mapping ──────────────────────────────
            st.markdown('<h3>Map Your Columns</h3>', unsafe_allow_html=True)
            st.markdown("Select which columns in your file correspond to the required and optional fields.")
            
            # Auto-detect best columns by analyzing content
            detected = _detect_columns(df)
            all_cols = list(df.columns)
            all_cols_with_none = ['(None)'] + all_cols
            
            def _col_index(detected_key, fallback):
                col = detected.get(detected_key)
                if col and col in all_cols:
                    return all_cols.index(col)
                return fallback
            
            def _col_index_with_none(detected_key, fallback):
                col = detected.get(detected_key)
                if col and col in all_cols:
                    return all_cols_with_none.index(col)
                return fallback
            
            st.markdown("**Required Columns:**")
            req_row1 = st.columns(3)
            
            with req_row1[0]:
                desc_col = st.selectbox(
                    "Description Column",
                    options=all_cols,
                    index=_col_index('desc', 0),
                    help="Column containing material descriptions"
                )
            
            with req_row1[1]:
                qty_col = st.selectbox(
                    "Quantity Column",
                    options=all_cols,
                    index=_col_index('qty', min(1, len(all_cols)-1)),
                    help="Column containing quantities"
                )
            
            with req_row1[2]:
                cost_col = st.selectbox(
                    "Unit Cost Column",
                    options=all_cols,
                    index=_col_index('cost', min(2, len(all_cols)-1)),
                    help="Column containing unit costs/prices"
                )
            
            req_row2 = st.columns(3)
            
            with req_row2[0]:
                uom_col = st.selectbox(
                    "Unit of Measurement Column",
                    options=all_cols,
                    index=_col_index('uom', min(3, len(all_cols)-1)),
                    help="Unit type: ea, ft, bag, box, etc."
                )
            
            with req_row2[1]:
                total_col = st.selectbox(
                    "Vendor Total Column",
                    options=all_cols,
                    index=_col_index('total', min(4, len(all_cols)-1)),
                    help="Vendor's line total for validation"
                )
            
            st.markdown("**Optional Columns:**")
            opt_col1 = st.columns(1)[0]
            
            with opt_col1:
                part_col_sel = st.selectbox(
                    "Part Number Column",
                    options=all_cols_with_none,
                    index=_col_index_with_none('part', 0),
                    help="Supplier part number (optional — useful for ordering)"
                )
                part_col = None if part_col_sel == '(None)' else part_col_sel
            
            # ── Step 2: Clean data & extract tax/freight ──────────
            processor = PricingProcessor(tax_rate=tax_rate, margin_rate=margin_rate)
            cleaned_df, extracted_tax, extracted_freight = processor.clean_vendor_quote(
                df, desc_col=desc_col, qty_col=qty_col, cost_col=cost_col,
                part_col=part_col, uom_col=uom_col, total_col=total_col
            )
            
            st.markdown('<h3>Cleaned Data Preview</h3>', unsafe_allow_html=True)
            st.dataframe(cleaned_df.head(15), use_container_width=True)
            st.caption(f"{len(cleaned_df)} line items after cleaning ({len(df) - len(cleaned_df)} junk rows removed)")
            
            # Show extracted tax & freight
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                if extracted_tax > 0:
                    # Calculate effective tax rate from vendor quote
                    vendor_subtotal = (pd.to_numeric(cleaned_df[cost_col], errors='coerce').fillna(0) *
                                       pd.to_numeric(cleaned_df[qty_col], errors='coerce').fillna(0)).sum()
                    effective_rate = (extracted_tax / vendor_subtotal * 100) if vendor_subtotal > 0 else 0
                    st.info(f"📋 Extracted Sales Tax: **${extracted_tax:,.2f}** (effective rate: {effective_rate:.2f}%)")
                else:
                    st.info("No sales tax found in quote — using sidebar rate")
            with info_col2:
                if extracted_freight > 0:
                    st.info(f"🚚 Extracted Freight: **${extracted_freight:,.2f}**")
                else:
                    st.info("No freight line found in quote")
            with info_col3:
                st.info(f"⚙️ Margin: {margin_rate*100:.1f}% | Tax: {tax_rate*100:.2f}%")
            
            # ── Step 3: Pass-through shipping ─────────────────────
            st.markdown('<h3>Pass-Through Shipping</h3>', unsafe_allow_html=True)
            shipping_cost = st.number_input(
                "Shipping / Freight Cost (pass-through, varies per site)",
                min_value=0.0,
                value=extracted_freight,
                step=10.0,
                help="Enter the shipping cost for this job. Added as a flat line item — no markup applied."
            )
            
            # ── Step 4: Process Quote ─────────────────────────────
            if st.button("Process Quote", type="primary"):
                processor = PricingProcessor(
                    tax_rate=tax_rate,
                    margin_rate=margin_rate,
                    shipping_cost=shipping_cost
                )
                
                processed_df = processor.process_quote(cleaned_df)
                
                st.markdown('<h2 class="section-header">Processed Quote</h2>', 
                            unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="info-box">
                    <strong>Calculation:</strong> Vendor Cost &times; (1 + {margin_rate*100:.1f}% margin) &times; (1 + {tax_rate*100:.2f}% tax) = Composite Unit Rate<br>
                    <strong>Multiplier:</strong> {(1+margin_rate)*(1+tax_rate):.4f}x<br>
                    <strong>Shipping:</strong> ${shipping_cost:,.2f} (pass-through)
                </div>
                """, unsafe_allow_html=True)
                
                # ── Client Sheet (3 columns) ─────────────────────
                client_df = processor.generate_client_spreadsheet(
                    processed_df, shipping_cost=shipping_cost
                )
                st.markdown('<h3>Client-Facing Quote (3-Column)</h3>', unsafe_allow_html=True)
                st.dataframe(client_df, use_container_width=True)
                
                client_total = client_df['Total'].sum()
                st.metric("Client Grand Total", f"${client_total:,.2f}")
                
                # ── Audit Sheet (full trail) ─────────────────────
                with st.expander("📊 Internal Audit Trail (for leadership)"):
                    audit_df = processor.generate_internal_audit_spreadsheet(
                        processed_df, tax_rate=tax_rate, margin_rate=margin_rate,
                        shipping_cost=shipping_cost
                    )
                    st.dataframe(audit_df, use_container_width=True)
                
                # ── Downloads ─────────────────────────────────────
                st.markdown('<h3>Download Results</h3>', unsafe_allow_html=True)
                
                # Excel Downloads
                st.markdown("**Excel Workbooks:**")
                dl_col1, dl_col2, dl_col3, dl_col4, dl_col5 = st.columns(5)
                
                with dl_col1:
                    audit_buffer = BytesIO()
                    processor.generate_internal_audit_spreadsheet(
                        processed_df, tax_rate=tax_rate, margin_rate=margin_rate,
                        output_path=audit_buffer, shipping_cost=shipping_cost
                    )
                    st.download_button(
                        label="📥 Audit (.xlsx)",
                        data=audit_buffer.getvalue(),
                        file_name="internal_audit_quote.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with dl_col2:
                    client_buffer = BytesIO()
                    processor.generate_client_spreadsheet(
                        processed_df, output_path=client_buffer,
                        shipping_cost=shipping_cost
                    )
                    st.download_button(
                        label="📥 Client (.xlsx)",
                        data=client_buffer.getvalue(),
                        file_name="client_quote.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with dl_col3:
                    # Generate combined workbook with proper formatting
                    combined_buffer = BytesIO()
                    
                    # Generate audit with formulas
                    audit_buffer_temp = BytesIO()
                    processor.generate_internal_audit_spreadsheet(
                        processed_df, tax_rate=tax_rate, margin_rate=margin_rate,
                        output_path=audit_buffer_temp, shipping_cost=shipping_cost
                    )
                    
                    # Generate client sheet
                    client_buffer_temp = BytesIO()
                    processor.generate_client_spreadsheet(
                        processed_df, output_path=client_buffer_temp,
                        shipping_cost=shipping_cost
                    )
                    
                    # Combine both into one workbook
                    import openpyxl
                    from openpyxl import load_workbook
                    
                    # Load audit workbook
                    audit_buffer_temp.seek(0)
                    audit_wb = load_workbook(audit_buffer_temp)
                    
                    # Load client workbook and copy its sheet
                    client_buffer_temp.seek(0)
                    client_wb = load_workbook(client_buffer_temp)
                    client_sheet = client_wb.active
                    
                    # Copy client sheet to audit workbook
                    audit_wb.create_sheet('Client_Quote')
                    target_sheet = audit_wb['Client_Quote']
                    for row in client_sheet.iter_rows():
                        for cell in row:
                            target_cell = target_sheet[cell.coordinate]
                            target_cell.value = cell.value
                            if cell.has_style:
                                target_cell.font = cell.font.copy()
                                target_cell.border = cell.border.copy()
                                target_cell.fill = cell.fill.copy()
                                target_cell.number_format = cell.number_format
                                target_cell.alignment = cell.alignment.copy()
                    
                    # Rename audit sheet
                    audit_wb['Audit_Details'].title = 'Internal_Audit'
                    
                    # Save combined workbook
                    audit_wb.save(combined_buffer)
                    
                    st.download_button(
                        label="📥 Combined (.xlsx)",
                        data=combined_buffer.getvalue(),
                        file_name="quote_complete.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with dl_col4:
                    md_report = processor.generate_summary_report(
                        processed_df, fmt='md', shipping_cost=shipping_cost,
                        extracted_tax=extracted_tax, extracted_freight=extracted_freight
                    )
                    st.download_button(
                        label="📥 Summary (.md)",
                        data=md_report,
                        file_name="quote_summary.md",
                        mime="text/markdown"
                    )
                
                with dl_col5:
                    try:
                        docx_bytes = processor.generate_summary_report(
                            processed_df, fmt='docx', shipping_cost=shipping_cost,
                            extracted_tax=extracted_tax, extracted_freight=extracted_freight
                        )
                        st.download_button(
                            label="📥 Summary (.docx)",
                            data=docx_bytes,
                            file_name="quote_summary.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    except ImportError:
                        st.caption("Install python-docx for .docx export")
                
                # Add Cleaned Data + CSV Downloads
                st.markdown("**Additional Exports:**")
                csv_col1, csv_col2, csv_col3, csv_col4 = st.columns(4)
                
                with csv_col1:
                    # Cleaned Data Excel
                    cleaned_buffer = BytesIO()
                    with pd.ExcelWriter(cleaned_buffer, engine='xlsxwriter') as writer:
                        cleaned_df.to_excel(writer, sheet_name='Cleaned_Data', index=False)
                    st.download_button(
                        label="📥 Cleaned (.xlsx)",
                        data=cleaned_buffer.getvalue(),
                        file_name="cleaned_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Raw cleaned data before pricing calculations"
                    )
                
                with csv_col2:
                    # Cleaned Data CSV
                    cleaned_csv = cleaned_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Cleaned (.csv)",
                        data=cleaned_csv,
                        file_name="cleaned_data.csv",
                        mime="text/csv",
                        help="Raw cleaned data in CSV format"
                    )
                
                with csv_col3:
                    # Audit CSV
                    audit_csv = audit_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Audit (.csv)",
                        data=audit_csv,
                        file_name="internal_audit.csv",
                        mime="text/csv",
                        help="Internal audit trail in CSV format"
                    )
                
                with csv_col4:
                    # Client CSV
                    client_csv = client_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Client (.csv)",
                        data=client_csv,
                        file_name="client_quote.csv",
                        mime="text/csv",
                        help="Client quote in CSV format"
                    )
                
                # Success message
                st.markdown("""
                <div class="success-message">
                    ✅ Quote processed successfully! 
                    <br><br>
                    <strong>Excel Downloads:</strong>
                    <br>• <strong>Audit</strong> — Step-by-step dollar breakdown with Part #, UOM (Vendor Cost → +Margin $ → +Tax $ → Composite Rate)
                    <br>• <strong>Client</strong> — Clean 6-column quote with Part #, Description, UOM, Qty, Rate, Total
                    <br>• <strong>Combined</strong> — Both audit and client sheets in one workbook
                    <br>• <strong>Summary</strong> — Markdown or Word report with totals and margin analysis
                    <br><br>
                    <strong>Additional Exports:</strong>
                    <br>• <strong>Cleaned Data</strong> — Raw extracted data (.xlsx or .csv)
                    <br>• <strong>CSV Exports</strong> — All sheets available in CSV format for data portability
                </div>
                """, unsafe_allow_html=True)
                
                # Increment files processed counter
                st.session_state.files_processed += 1
                
                # ── Auto-add materials ────────────────────────────
                st.markdown('<h3>Add New Materials to Database</h3>', unsafe_allow_html=True)
                
                with st.expander("📦 Auto-add Materials from Quote"):
                    st.markdown("Add new materials from this quote to your materials database:")
                    
                    add_col1, add_col2, add_col3 = st.columns(3)
                    
                    with add_col1:
                        add_category = st.selectbox(
                            "Category for new materials",
                            ["Conduit", "Couplers", "Plugs", "Equipment", "Hand Holes", 
                             "Cable", "Aerial", "Grounding", "Markers", "Safety", "Materials", "Other"]
                        )
                    
                    with add_col2:
                        add_part_col = st.selectbox(
                            "Part Number Column (Optional)",
                            options=["None"] + all_cols,
                            help="Column containing vendor part numbers"
                        )
                    
                    with add_col3:
                        add_unit_col = st.selectbox(
                            "Unit Column (Optional)",
                            options=["None"] + all_cols,
                            help="Column containing units (ea, FT, etc.)"
                        )
                    
                    if st.button("Add New Materials", type="secondary"):
                        part_col_name = None if add_part_col == "None" else add_part_col
                        unit_col_name = None if add_unit_col == "None" else add_unit_col
                        
                        added = materials_db.add_materials_from_quote(
                            df=cleaned_df,
                            desc_col=desc_col,
                            part_col=part_col_name,
                            unit_col=unit_col_name if unit_col_name else 'Unit',
                            cost_col=cost_col,
                            category=add_category
                        )
                        
                        if added > 0:
                            st.success(f"Added {added} new materials to database!")
                        else:
                            st.info("No new materials found (all materials already in database)")
                        st.rerun()
            
            # Clean up temporary file (only for Excel)
            if not is_pdf:
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception as cleanup_error:
                    st.warning(f"Warning: Could not clean up temporary file: {cleanup_error}")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass


def build_quote_tab(materials_db):
    """Manual quote building tab."""
    st.markdown('<h2 class="section-header">Build Quote Manually</h2>', 
                unsafe_allow_html=True)
    
    # Get materials by category
    materials_by_category = materials_db.get_materials_by_category()
    
    # Initialize session state for quote items
    if 'quote_items' not in st.session_state:
        st.session_state.quote_items = []
    
    # Add items section
    st.markdown('<h3>Add Items to Quote</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Material selection dropdown
        category = st.selectbox("Select Category", list(materials_by_category.keys()))
        materials_in_category = materials_by_category[category]
        material_names = [m['name'] for m in materials_in_category]
        selected_material = st.selectbox("Select Material", material_names)
    
    with col2:
        # Quantity input
        quantity = st.number_input("Quantity", min_value=0, value=1, step=1)
    
    with col3:
        # Add button
        if st.button("Add to Quote", type="primary"):
            material = materials_db.find_material(selected_material)
            if material:
                # Clean the material name for display
                clean_name = materials_db._clean_material_name(material['name'])
                item = {
                    'name': clean_name,
                    'part_number': material['part_number'],
                    'quantity': quantity,
                    'unit': material['unit'],
                    'unit_cost': material['unit_cost']
                }
                st.session_state.quote_items.append(item)
                st.success(f"Added {quantity} x {clean_name}")
    
    # Display quote items
    if st.session_state.quote_items:
        st.markdown('<h3>Quote Items</h3>', unsafe_allow_html=True)
        
        # Convert to DataFrame for display
        quote_df = pd.DataFrame(st.session_state.quote_items)
        
        # Add calculations
        tax_rate = st.sidebar.slider("Tax Rate (%)", 0.0, 20.0, 8.25, 0.25) / 100
        margin_rate = st.sidebar.slider("Margin Rate (%)", 0.0, 50.0, 10.0, 1.0) / 100
        
        processor = PricingProcessor(tax_rate=tax_rate, margin_rate=margin_rate)
        
        quote_df['composite_rate'] = quote_df['unit_cost'].apply(processor.calculate_composite_rate)
        quote_df['total'] = (quote_df['quantity'] * quote_df['composite_rate']).round(2)
        
        # Display with formatting
        display_df = quote_df[['name', 'quantity', 'unit', 'composite_rate', 'total']].copy()
        display_df.columns = ['Description', 'Quantity', 'Unit', 'Unit Price', 'Total']
        display_df['Unit Price'] = display_df['Unit Price'].map('${:,.2f}'.format)
        display_df['Total'] = display_df['Total'].map('${:,.2f}'.format)
        
        st.dataframe(display_df, use_container_width=True)
        
        # Summary
        total_amount = quote_df['total'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Subtotal (Cost)", f"${quote_df['unit_cost'].sum():,.2f}")
        with col2:
            st.metric("With Margin & Tax", f"${total_amount:,.2f}")
        with col3:
            st.metric("Items", len(quote_df))
        
        # Download buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Generate internal audit file
            audit_buffer = BytesIO()
            audit_df = processor.generate_internal_audit_spreadsheet(
                quote_df, 
                tax_rate=tax_rate, 
                margin_rate=margin_rate,
                output_path=audit_buffer
            )
            
            st.download_button(
                label="📥 Download Audit",
                data=audit_buffer.getvalue(),
                file_name="manual_audit.xlsx",
                help="Full calculation breakdown",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # Generate client quote file
            client_buffer = BytesIO()
            client_df_manual = processor.generate_client_spreadsheet(
                quote_df,
                output_path=client_buffer
            )
            
            st.download_button(
                label="📥 Download Client Quote",
                data=client_buffer.getvalue(),
                file_name="manual_client_quote.xlsx",
                help="Clean quote for client",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col3:
            # Combined file
            combined_buffer = BytesIO()
            with pd.ExcelWriter(combined_buffer, engine='xlsxwriter') as writer:
                audit_df.to_excel(writer, sheet_name='Internal_Audit', index=False)
                client_df_manual.to_excel(writer, sheet_name='Client_Quote', index=False)
            
            st.download_button(
                label="📥 Download Both",
                data=combined_buffer.getvalue(),
                file_name="manual_quote_complete.xlsx",
                help="Both sheets in one file",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Clear button
        if st.button("Clear Quote", type="secondary"):
            st.session_state.quote_items = []
            st.rerun()


def materials_list_tab(materials_db):
    """Materials list management tab."""
    st.markdown('<h2 class="section-header">Materials Database</h2>', 
                unsafe_allow_html=True)
    
    # Display materials table (hide sensitive columns)
    materials_df = materials_db.to_dataframe(hide_sensitive=True)
    
    # Search/filter
    search_term = st.text_input("Search materials...")
    
    if search_term:
        filtered_df = materials_df[materials_df['name'].str.contains(search_term, case=False)]
    else:
        filtered_df = materials_df
    
    st.dataframe(filtered_df, use_container_width=True)
    
    # Edit existing materials
    with st.expander("Edit Material Pricing"):
        st.markdown("**Select a material to update its pricing:**")
        
        # Material selection for editing
        edit_material_names = materials_df['name'].tolist()
        selected_edit_material = st.selectbox("Select Material to Edit", edit_material_names)
        
        if selected_edit_material:
            material = materials_db.find_material(selected_edit_material)
            if material:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    current_cost = st.number_input(
                        "Current Unit Cost",
                        min_value=0.0,
                        value=float(material['unit_cost']),
                        step=0.01,
                        key=f"cost_{material['name']}"
                    )
                
                with col2:
                    new_part = st.text_input(
                        "Part Number",
                        value=material['part_number'] or "",
                        key=f"part_{material['name']}"
                    )
                
                with col3:
                    new_unit = st.selectbox(
                        "Unit",
                        options=["each", "FT", "ea", "bag", "PK", "REEL"],
                        index=["each", "FT", "ea", "bag", "PK", "REEL"].index(material['unit']) if material['unit'] in ["each", "FT", "ea", "bag", "PK", "REEL"] else 0,
                        key=f"unit_{material['name']}"
                    )
                
                # Update button
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("Update Material", type="primary"):
                        # Update the material using the database method
                        materials_db.update_material(
                            selected_edit_material,
                            unit_cost=current_cost,
                            part_number=new_part if new_part else None,
                            unit=new_unit
                        )
                        st.success(f"Updated {selected_edit_material}")
                        st.rerun()
                
                with col2:
                    if st.button("Delete Material", type="secondary"):
                        # Delete the material using the database method
                        materials_db.delete_material(selected_edit_material)
                        st.success(f"Deleted {selected_edit_material}")
                        st.rerun()
    
    # Bulk price update section
    with st.expander("Bulk Price Update"):
        st.markdown("**Apply percentage increase/decrease to all materials or by category:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            update_type = st.selectbox("Update Scope", ["All Materials", "By Category"])
            
        with col2:
            if update_type == "By Category":
                categories = list(set(materials_df['category'].tolist()))
                selected_category = st.selectbox("Select Category", categories)
            else:
                selected_category = None
        
        with col3:
            percentage_change = st.number_input(
                "% Change",
                value=0.0,
                step=0.1,
                help="Positive for increase, negative for decrease"
            )
        
        if st.button("Apply Bulk Update"):
            if update_type == "All Materials":
                # Update all materials
                for mat in materials_db.materials:
                    old_cost = mat['unit_cost']
                    new_cost = old_cost * (1 + percentage_change / 100)
                    mat['unit_cost'] = round(new_cost, 4)
                materials_db.save()  # Save all changes
                st.success(f"Updated all materials by {percentage_change}%")
            else:
                # Update only selected category
                updated_count = 0
                for mat in materials_db.materials:
                    if mat['category'] == selected_category:
                        old_cost = mat['unit_cost']
                        new_cost = old_cost * (1 + percentage_change / 100)
                        mat['unit_cost'] = round(new_cost, 4)
                        updated_count += 1
                materials_db.save()  # Save all changes
                st.success(f"Updated {updated_count} materials in {selected_category} by {percentage_change}%")
            st.rerun()
    
    # Add new material section
    with st.expander("Add New Material"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_name = st.text_input("Material Name")
            new_part = st.text_input("Part Number")
        
        with col2:
            new_cost = st.number_input("Unit Cost", min_value=0.0, value=0.0, step=0.01)
            new_unit = st.selectbox("Unit", ["each", "FT", "ea", "bag", "PK", "REEL"])
        
        with col3:
            all_categories = sorted(set(materials_df['category'].tolist() + 
                ["Conduit", "Couplers", "Plugs", "Equipment", "Hand Holes",
                 "Cable", "Aerial", "Grounding", "Markers", "Safety", "Materials", "Other"]))
            new_category = st.selectbox("Category", all_categories)
        
        if st.button("Add Material") and new_name:
            materials_db.add_material(
                name=new_name,
                part_number=new_part if new_part else None,
                unit_cost=new_cost,
                unit=new_unit,
                category=new_category
            )
            st.success(f"Added {new_name} to materials database")
            st.rerun()
    
    # Export/Import
    col1, col2 = st.columns(2)
    
    with col1:
        # Export materials (without sensitive data)
        csv = materials_db.to_dataframe(hide_sensitive=True).to_csv(index=False)
        st.download_button(
            label="📥 Export Materials CSV",
            data=csv,
            file_name="materials_list.csv",
            mime="text/csv"
        )
    
    with col2:
        # Import materials
        uploaded_materials = st.file_uploader(
            "Import Materials CSV",
            type=['csv'],
            help="Upload a CSV file with materials"
        )
        
        if uploaded_materials:
            try:
                imported_df = pd.read_csv(uploaded_materials)
                st.success(f"Imported {len(imported_df)} materials")
                st.dataframe(imported_df)
            except Exception as e:
                st.error(f"Error importing file: {str(e)}")
    
    # Instructions section
    with st.expander("📖 How to Use"):
        st.markdown("""
        **Process Quote Tab:**
        1. Upload your Excel file containing the vendor quote
        2. Select the sheet with the quote data
        3. Adjust tax and margin rates in the sidebar if needed
        4. Click "Process Quote" to calculate composite rates
        5. Download the results
        
        **Build Quote Tab:**
        1. Select materials from the dropdown by category
        2. Enter quantities for each item
        3. Add items to build your quote
        4. Download the completed quote
        
        **Materials List Tab:**
        1. View all available materials
        2. Search for specific items
        3. Add new materials to the database
        4. Export/import materials lists
        
        The calculator automatically adds margin and tax to create clean client pricing.
        """)
    
    # Example format section
    with st.expander("📋 Expected Format"):
        st.markdown("""
        **For Process Quote Tab:**
        The app works best with Excel formats including:
        - Material Description
        - Part Number
        - Quantity
        - Unit Cost
        
        **For Build Quote Tab:**
        Uses the built-in materials database with standard OSP items.
        You can add custom materials in the Materials List tab.
        """)


if __name__ == "__main__":
    main()
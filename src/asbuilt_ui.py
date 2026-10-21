"""Streamlit tab: scan an as-built drawing -> verified takeoff -> priced BOM."""

from __future__ import annotations

import hashlib
import io
import os
from typing import List

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from src import asbuilt_extractor as ex
from src import asbuilt_ocr as ocr
from src.pricing_calculator import PricingProcessor

_CAT_COLORS = {
    "Directional Bore": "#d62728", "Trench": "#8c564b", "Plow": "#bcbd22", "Aerial": "#1f77b4",
    "Conduit": "#ff7f0e", "Fiber Cable": "#9467bd", "Slack": "#17becf", "Station Run": "#7f7f7f",
    "Structure": "#2ca02c", "Table line": "#e377c2",
}


def _annotate(page: ocr.OcrPage, items: pd.DataFrame, show_all: bool, max_side: int = 2600) -> Image.Image:
    img = page.image.convert("RGB").copy()
    d = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", max(14, img.width // 160))
    except OSError:
        font = ImageFont.load_default()
    if show_all:
        for w in page.words:
            d.rectangle(w.box, outline=(150, 150, 150, 140), width=1)
    pitems = items[items["page"] == page.page + 1] if not items.empty else items
    for _, r in pitems.iterrows():
        col = _CAT_COLORS.get(r["category"], "#444444").lstrip("#")
        rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
        alpha = 255 if bool(r["include"]) else 90
        box = (r["x0"], r["y0"], r["x1"], r["y1"])
        if any(pd.isna(v) or v == "" for v in box):
            continue  # rows added by hand have no position on the drawing
        d.rectangle(box, outline=rgb + (alpha,), fill=rgb + (45,), width=max(2, img.width // 900))
        d.text((box[0], max(box[1] - font.size - 2, 0)), f'{r["category"]}', fill=rgb + (alpha,), font=font)
    k = max_side / max(img.size)
    return img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS) if k < 1 else img


def _excel(title: dict, items: pd.DataFrame, summary: pd.DataFrame, bom: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
        pd.DataFrame(list(title.items()), columns=["Field", "Value"]).to_excel(xw, sheet_name="Title Block", index=False)
        items.drop(columns=["x0", "y0", "x1", "y1"], errors="ignore").to_excel(xw, sheet_name="Takeoff", index=False)
        summary.to_excel(xw, sheet_name="Summary", index=False)
        bom.to_excel(xw, sheet_name="BOM", index=False)
        for ws in xw.sheets.values():
            ws.set_column(0, 12, 22)
    return buf.getvalue()


def render(materials_db) -> None:
    st.markdown('<h2 class="section-header">As-Built Scanner</h2>', unsafe_allow_html=True)
    st.caption("Scan an as-built drawing (PDF / photo / TIFF). Footage callouts, stationing, structures and the title "
               "block are read automatically - **review the highlighted overlay**, correct anything wrong, then "
               "send the bill of materials to pricing.")

    engines = ocr.available_engines()
    c1, c2, c3, c4 = st.columns([3, 1.4, 1, 1.4])
    up = c1.file_uploader("As-built drawing", type=["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp"],
                          key="ab_file")
    engine = c2.selectbox("OCR engine", ["auto"] + engines, key="ab_engine",
                          help="auto = PDF text layer first, then RapidOCR (local). Mistral needs MISTRAL_API_KEY.")
    dpi = c3.select_slider("Scan DPI", [150, 200, 250, 300], value=200, key="ab_dpi",
                           help="Higher = reads smaller text, slower")
    min_conf = c4.slider("Min confidence", 0.2, 0.9, 0.45, 0.05, key="ab_conf")
    o1, o2 = st.columns(2)
    deskew = o1.checkbox("Auto-straighten scanned pages", True, key="ab_deskew")
    force = o2.checkbox("Ignore PDF text layer (force OCR)", False, key="ab_force")

    if not engines and not up:
        st.info("Install `rapidocr-onnxruntime` for local OCR (included in requirements.txt).")
    if up is None:
        return

    data = up.getvalue()
    sig = hashlib.sha1(data + f"{engine}{dpi}{min_conf}{deskew}{force}".encode()).hexdigest()
    if st.session_state.get("ab_sig") != sig:
        if not st.button("🔍 Scan drawing", type="primary", key="ab_go"):
            return
        bar = st.progress(0.0, text="Starting...")
        try:
            pages = ocr.scan_document(data, up.name, engine=engine, dpi=dpi, deskew=deskew, min_conf=min_conf,
                                      force_ocr=force, progress=lambda f, m: bar.progress(min(f, 1.0), text=m))
            result = ex.extract_takeoff(pages)
        except Exception as exc:
            bar.empty()
            st.error(f"Scan failed: {exc}")
            return
        bar.empty()
        st.session_state.update(ab_sig=sig, ab_pages=pages, ab_result=result, ab_items=result.items.copy(),
                                ab_title=dict(result.title_block))

    pages: List[ocr.OcrPage] = st.session_state["ab_pages"]
    result: ex.AsBuiltResult = st.session_state["ab_result"]
    n_words = sum(len(p.words) for p in pages)
    st.success(f"Read {len(pages)} page(s), {n_words:,} text blocks via {', '.join(sorted({p.engine for p in pages}))}.")
    for n in result.notes:
        st.warning(n)

    # ---- title block -------------------------------------------------
    st.subheader("Title block")
    tb = st.session_state["ab_title"]
    keys = ["project", "job_no", "sheet", "date", "revision", "scale", "drawn_by", "client", "location"]
    cols = st.columns(3)
    for i, k in enumerate(keys):
        tb[k] = cols[i % 3].text_input(k.replace("_", " ").title(), tb.get(k, ""), key=f"ab_tb_{k}")
    (st.success if result.is_as_built else st.warning)(
        "AS-BUILT / record drawing stamp detected" if result.is_as_built else "No AS-BUILT stamp detected")

    # ---- overlay -----------------------------------------------------
    items: pd.DataFrame = st.session_state["ab_items"]
    st.subheader("Verify on the drawing")
    v1, v2 = st.columns([1, 1])
    pno = v1.number_input("Page", 1, len(pages), 1, key="ab_page") - 1
    show_all = v2.checkbox("Show every text box", False, key="ab_all")
    st.image(_annotate(pages[pno], items, show_all), use_container_width=True,
             caption="Colored boxes = takeoff items (faded = excluded). Zoom the image to inspect.")
    st.caption("  ".join(f"<span style='color:{c}'>■</span> {n}" for n, c in _CAT_COLORS.items()),
               unsafe_allow_html=True)

    # ---- editable takeoff ----------------------------------------------
    st.subheader("Takeoff (editable)")
    if items.empty:
        st.info("No quantities recognised. Try a higher DPI, lower the confidence, or check the raw text below.")
    else:
        view_cols = ["include", "page", "category", "description", "size", "count", "qty", "unit", "total_qty",
                     "conf", "flags", "source_text"]
        edited = st.data_editor(
            items[view_cols], use_container_width=True, height=420, num_rows="dynamic", key="ab_editor",
            column_config={"include": st.column_config.CheckboxColumn("Use"),
                           "qty": st.column_config.NumberColumn(format="%.1f"),
                           "total_qty": st.column_config.NumberColumn("Total qty", format="%.1f", disabled=True),
                           "conf": st.column_config.ProgressColumn("OCR conf", min_value=0, max_value=1)})
        # recompute total_qty after edits and keep box coordinates aligned
        edited["total_qty"] = [(q or 0) * (c or 1) if u == "LF" else (q or 0)
                               for q, c, u in zip(edited["qty"], edited["count"], edited["unit"])]
        for col in ("x0", "y0", "x1", "y1"):
            edited[col] = items[col].reindex(edited.index)
        st.session_state["ab_items"] = edited.reset_index(drop=True)
        items = st.session_state["ab_items"]

        summary = ex.summarize(items)
        st.subheader("Summary")
        m1, m2, m3 = st.columns(3)
        inc = items[items["include"].astype(bool)]
        m1.metric("Linear footage", f'{inc.loc[inc["unit"] == "LF", "total_qty"].sum():,.0f} LF')
        m2.metric("Structures / EA", f'{inc.loc[inc["unit"] == "EA", "total_qty"].sum():,.0f}')
        m3.metric("Low-confidence / flagged", int((inc["flags"].astype(str) != "").sum()))
        st.dataframe(summary, use_container_width=True)

        # ---- BOM + pricing --------------------------------------------
        st.subheader("Bill of materials & pricing")
        p1, p2 = st.columns(2)
        margin = p1.number_input("Margin %", 0.0, 100.0, 10.0, 1.0, key="ab_margin") / 100
        tax = p2.number_input("Tax %", 0.0, 25.0, 8.25, 0.25, key="ab_tax") / 100
        bom = ex.to_bom(items, materials_db.materials)
        priced = pd.DataFrame()
        if bom.empty:
            st.info("Nothing selected for the BOM.")
        else:
            unmatched = int((~bom["Matched"]).sum())
            if unmatched:
                st.warning(f"{unmatched} line(s) have no catalog match (cost $0). Add them in the Materials List tab "
                           "or edit the description above.")
            bom = st.data_editor(bom, use_container_width=True, key="ab_bom", num_rows="dynamic",
                                 column_config={"Unit Cost": st.column_config.NumberColumn(format="$%.3f"),
                                                "Matched": st.column_config.CheckboxColumn(disabled=True)})
            try:
                proc = PricingProcessor(tax_rate=tax, margin_rate=margin)
                priced = proc.process_quote(bom[["Description", "Qty", "Unit Cost"]].copy(), desc_col="Description",
                                            qty_col="Qty", cost_col="Unit Cost")
                st.metric("Estimated total (with margin & tax)", f'${priced["Total Price"].sum():,.2f}')
                st.dataframe(priced, use_container_width=True)
            except Exception as exc:
                st.error(f"Pricing failed: {exc}")

            b1, b2, b3 = st.columns(3)
            b1.download_button("📥 Takeoff workbook (.xlsx)", _excel(tb, items.drop(columns=["x0", "y0", "x1", "y1"], errors="ignore"),
                                                                  summary, bom), "as_built_takeoff.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            b2.download_button("📥 BOM (.csv)", bom.to_csv(index=False), "as_built_bom.csv", "text/csv")
            if b3.button("➕ Send to Build Quote", key="ab_send"):
                st.session_state.setdefault("quote_items", [])
                for _, r in bom.iterrows():
                    st.session_state.quote_items.append({
                        "name": r["Description"], "part_number": None, "quantity": float(r["Qty"]),
                        "unit": r["Unit"], "unit_cost": float(r["Unit Cost"])})
                st.success(f"Added {len(bom)} lines to the Build Quote tab.")
                st.rerun()

    with st.expander("Raw OCR text"):
        txt = "\n".join(f"[p{l.page + 1}] {l.text}" for l in result.lines)
        st.text_area("Recognised text", txt, height=300, key="ab_raw")
        st.download_button("⬇️ Text", txt, "as_built_ocr.txt")

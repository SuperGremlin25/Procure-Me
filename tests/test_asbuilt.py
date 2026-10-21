"""As-built scanner tests: extraction logic on positioned words + one real OCR round trip."""

import io
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.asbuilt_extractor import extract_takeoff, normalize, parse_size, fmt_size, summarize, to_bom
from src.asbuilt_ocr import OcrPage, OcrWord, dedupe, group_lines, scan_document, available_engines
from src.materials_db import MaterialsDatabase
from src.mistral_ocr_client import MistralOCRClient


def W(text, x, y, h=20, conf=0.9):
    return OcrWord(text, conf, (x, y, x + 12 * len(text), y + h), 0)


def page(words):
    return OcrPage(0, 3000, 2000, words)


def items(words):
    return extract_takeoff([page(words)])


def test_sizes():
    assert parse_size("1-1/4") == 1.25 and parse_size("3/4") == 0.75 and parse_size("2") == 2.0
    assert fmt_size(1.25) == '1-1/4"' and fmt_size(0.25) == '1/4"' and fmt_size(2) == '2"'


def test_ocr_digit_confusion_fixed():
    assert normalize("2,1OO FT") == "2,100 FT"
    assert "HDPE" in normalize("hdpe")


def test_conduit_bore_multiplies_by_count():
    r = items([W('(2) 2" HDPE BY DIRECTIONAL BORE 1,250 LF', 100, 100)])
    row = r.items.iloc[0]
    assert row["category"] == "Directional Bore" and row["qty"] == 1250 and row["count"] == 2
    assert row["total_qty"] == 2500 and row["size"] == '2"'


def test_callout_split_across_boxes_uses_neighbours():
    r = items([W('(3) 1-1/4" INNERDUCT', 100, 300), W("TRENCH", 500, 300), W("340 LF", 650, 300)])
    row = r.items.iloc[0]
    assert row["category"] == "Trench" and row["total_qty"] == 1020


def test_pole_height_is_not_footage():
    r = items([W("40' CLASS 4 POLE #123", 100, 100)])
    assert list(r.items["category"]) == ["Structure"]
    assert "40'" in r.items.iloc[0]["size"]


def test_depth_notes_ignored():
    assert items([W("DEPTH 36\" MIN COVER", 100, 100)]).items.empty


def test_structures_counted_once_per_id():
    r = items([W("HH-12 30x48", 100, 100), W("HH-12", 900, 700), W("HH-13", 200, 400)])
    assert len(r.items) == 2


def test_station_run_not_double_counted_with_callout():
    r = items([W('(2) 2" HDPE BORE 1,250 LF', 100, 100), W("STA 10+00 TO 22+50", 100, 300)])
    st = r.items[r.items["description"].str.contains("stationing")].iloc[0]
    assert st["qty"] == 1250 and not st["include"]
    assert summarize(r.items)["qty"].sum() == 2500  # only the callout, with 2 ducts


def test_title_block_reads_value_to_the_right():
    r = items([W("PROJECT", 1500, 1200), W("Columbus Fiber", 1650, 1200), W("DATE", 1500, 1300),
               W("03/14/2025", 1650, 1300), W("REV", 1500, 1350), W("B", 1650, 1350), W("AS-BUILT", 1500, 1500)])
    assert r.title_block["project"] == "Columbus Fiber"
    assert r.title_block["date"] == "03/14/2025" and r.title_block["revision"] == "B"
    assert r.is_as_built


def test_bom_maps_to_catalog():
    r = items([W('(2) 2" HDPE BORE 1,250 LF', 100, 100), W('1/4" MESSENGER STRAND 2,100 FT', 100, 300),
               W("HH-12 30x48", 100, 500)])
    bom = to_bom(r.items, MaterialsDatabase(None).materials)
    by = {row["Description"]: row for _, row in bom.iterrows()}
    assert by['2" Conduit orange']["Qty"] == 2500 and by['2" Conduit orange']["Unit Cost"] > 0
    assert by['1/4" Messenger Strand']["Qty"] == 2100
    hh = [r for d, r in by.items() if d.startswith("HH")][0]
    assert "APPROX" in hh["Match basis"]  # 30x48 is not a catalog size - flagged as approximate


def test_dedupe_stitches_tile_seam_and_drops_fragments():
    a = OcrWord("Columbus Fiber Phase", 0.86, (2621, 1725, 3038, 1758), 0)
    b = OcrWord("er Phase 2", 0.85, (2884, 1724, 3079, 1756), 0)
    out = dedupe([a, b])
    assert [w.text for w in out] == ["Columbus Fiber Phase 2"]
    full = OcrWord('(1) 4" PVC 180 LF', 0.9, (1421, 652, 1476, 1247), 0, rotated=True)
    frag = OcrWord("180 LF", 0.7, (1440, 662, 1474, 802), 0, rotated=True)
    assert len(dedupe([full, frag])) == 1


def test_group_lines_merges_same_baseline():
    lines = group_lines([W('(2) 2" HDPE', 100, 100), W("1,250 LF", 260, 101)])
    assert len(lines) == 1 and lines[0].text.endswith("1,250 LF")


def test_mistral_markdown_parser():
    md = "| Pole # | Make-ready Action | Attach Height |\n|---|---|---|\n| A-1 | Replace pole | |\n| A-2 | Lower comm | 25'-6\" |"
    rep = MistralOCRClient("k")._parse_ocr_response({"pages": [{"markdown": md}]}, "AEP")
    assert [(a.pole_id, a.action_type) for a in rep.actions] == [("A-1", "POLE_REPLACE"), ("A-2", "COMM_MOVE")]
    assert rep.actions[1].attachment_height == 25.5


@pytest.mark.skipif("rapidocr" not in available_engines(), reason="rapidocr not installed")
def test_real_ocr_roundtrip():
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    img = Image.new("RGB", (1500, 500), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 60), '(2) 2" HDPE BY DIRECTIONAL BORE 1,250 LF', fill="black", font=font)
    d.text((40, 200), "HH-12 30x48", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    r = extract_takeoff(scan_document(buf.getvalue(), "t.png", thorough=False))
    assert 2500 in list(r.items["total_qty"]) and any("Handhole" in x for x in r.items["description"])

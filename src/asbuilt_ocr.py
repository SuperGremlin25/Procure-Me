"""As-built drawing OCR.

Turns a scanned or plotted as-built (PDF, PNG, JPG, TIFF) into positioned text
that the takeoff extractor can read.

Engines (auto-selected, in this order):
  * PDF text layer   - vector CAD plots already contain exact text; used when present
  * RapidOCR         - local, pip-installable, no system binary (default for scans)
  * Tesseract        - if the binary and pytesseract are installed
  * Mistral OCR      - cloud, needs MISTRAL_API_KEY (markdown only, no positions)

Large sheets (ARCH D / E sized) are OCR'd in overlapping tiles so small callout
text isn't lost to downscaling.  Vertical text (routes, property lines) is read
natively by the engine and flagged ``rotated`` from the box shape.
"""

from __future__ import annotations

import base64
import io
import math
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageOps

Image.MAX_IMAGE_PIXELS = 400_000_000  # large-format scans are legitimately huge

Box = Tuple[float, float, float, float]  # x0, y0, x1, y1 (page pixels)


@dataclass
class OcrWord:
    text: str
    conf: float
    box: Box
    page: int = 0
    rotated: bool = False  # True when the text runs vertically on the sheet
    source: str = ""

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1] if not self.rotated else self.box[2] - self.box[0]

    @property
    def cx(self) -> float:
        return (self.box[0] + self.box[2]) / 2

    @property
    def cy(self) -> float:
        return (self.box[1] + self.box[3]) / 2


@dataclass
class OcrPage:
    page: int
    width: int
    height: int
    words: List[OcrWord] = field(default_factory=list)
    engine: str = ""
    image: Optional[Image.Image] = None
    markdown: str = ""  # only set by engines without positions (Mistral)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def render_pages(data: bytes, filename: str, dpi: int = 200, max_side: int = 7000,
                 max_pages: int = 30) -> List[Tuple[Image.Image, List[OcrWord]]]:
    """Return [(page image, native text words)] for a PDF or image upload."""
    name = filename.lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return _render_pdf(data, dpi, max_side, max_pages)
    img = Image.open(io.BytesIO(data))
    pages = []
    n = getattr(img, "n_frames", 1)
    for i in range(min(n, max_pages)):
        img.seek(i)
        pages.append((ImageOps.exif_transpose(img.convert("RGB")), []))
    return pages


def _render_pdf(data: bytes, dpi: int, max_side: int, max_pages: int):
    import pypdfium2 as pdfium

    out = []
    pdf = pdfium.PdfDocument(data)
    try:
        native = _native_words(data, dpi, max_pages)
        for i in range(min(len(pdf), max_pages)):
            page = pdf[i]
            w_pt, h_pt = page.get_size()
            scale = dpi / 72.0
            if max(w_pt, h_pt) * scale > max_side:
                scale = max_side / max(w_pt, h_pt)
            img = page.render(scale=scale).to_pil().convert("RGB")
            words = native.get(i, [])
            # native coordinates were computed at dpi/72; rescale if we capped resolution
            k = scale / (dpi / 72.0)
            if abs(k - 1.0) > 1e-6:
                for w in words:
                    w.box = tuple(v * k for v in w.box)  # type: ignore[assignment]
            out.append((img, words))
    finally:
        pdf.close()
    return out


def _native_words(data: bytes, dpi: int, max_pages: int) -> dict:
    """Words from the PDF text layer (empty for pure scans)."""
    result: dict = {}
    try:
        import pdfplumber
    except ImportError:
        return result
    k = dpi / 72.0
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                ws = []
                for w in page.extract_words(keep_blank_chars=False, use_text_flow=False, extra_attrs=["upright"]):
                    t = w["text"].strip()
                    if not t:
                        continue
                    ws.append(OcrWord(t, 1.0, (w["x0"] * k, w["top"] * k, w["x1"] * k, w["bottom"] * k), i,
                                      rotated=not w.get("upright", True), source="pdf-text"))
                result[i] = ws
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def deskew_angle(img: Image.Image, search: float = 4.0, step: float = 0.5) -> float:
    """Estimate scan skew (degrees) by maximizing row-sum variance on a small binary copy."""
    small = ImageOps.autocontrast(img.convert("L"))
    scale = 900 / max(small.size)
    if scale < 1:
        small = small.resize((int(small.width * scale), int(small.height * scale)))
    arr = (np.asarray(small) < 140).astype(np.uint8) * 255
    if arr.sum() == 0:
        return 0.0
    bin_img = Image.fromarray(arr)
    best, best_score = 0.0, -1.0
    a = -search
    while a <= search + 1e-9:
        rows = np.asarray(bin_img.rotate(a, resample=Image.NEAREST, fillcolor=0)).sum(axis=1).astype(float)
        score = float(np.var(rows))
        if score > best_score:
            best, best_score = a, score
        a += step
    return best


def preprocess(img: Image.Image, deskew: bool = True, sharpen: bool = False) -> Tuple[Image.Image, float]:
    """Grayscale -> autocontrast -> (deskew) -> mild sharpen.  Returns (image, angle applied)."""
    g = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    angle = 0.0
    if deskew:
        angle = deskew_angle(g)
        if abs(angle) >= 0.4:
            g = g.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=255)
        else:
            angle = 0.0
    if sharpen:
        g = g.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=3))
    return g.convert("RGB"), angle


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

_RAPID = None


def _rapid():
    global _RAPID
    if _RAPID is None:
        from rapidocr_onnxruntime import RapidOCR
        _RAPID = RapidOCR()
    return _RAPID


def available_engines() -> List[str]:
    engines = []
    try:
        import rapidocr_onnxruntime  # noqa: F401
        engines.append("rapidocr")
    except Exception:
        pass
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        engines.append("tesseract")
    except Exception:
        pass
    if os.getenv("MISTRAL_API_KEY"):
        engines.append("mistral")
    return engines


def _iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua


def _area(b: Box) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _overlap_min(a: Box, b: Box) -> float:
    """Intersection area as a fraction of the smaller box."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    small = min(_area(a), _area(b))
    return (ix * iy) / small if small > 0 else 0.0


def _union(a: Box, b: Box) -> Box:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _stitch(a: OcrWord, b: OcrWord) -> Optional[OcrWord]:
    """Join two reads of the same line split by a tile seam: the end of one repeats the start of the other
    ('Columbus Fiber Phase' + 'er Phase 2' -> 'Columbus Fiber Phase 2')."""
    from difflib import SequenceMatcher

    for first, second in ((a, b), (b, a)):
        m = SequenceMatcher(None, first.text, second.text, autojunk=False).find_longest_match(
            0, len(first.text), 0, len(second.text))
        if m.size >= 4 and m.a + m.size == len(first.text) and m.b + m.size < len(second.text) \
                and m.b <= max(3, len(second.text) // 3):
            text = first.text + second.text[m.b + m.size:]
            return OcrWord(text, min(a.conf, b.conf), _union(a.box, b.box), a.page, a.rotated or b.rotated, a.source)
    return None


def dedupe(words: List[OcrWord], thresh: float = 0.5) -> List[OcrWord]:
    """Resolve overlapping reads from tile overlaps: stitch seam splits, drop fragments contained in a longer
    read, and keep the higher-confidence copy of true duplicates."""
    kept: List[OcrWord] = []
    for w in sorted(words, key=lambda w: (-len(w.text) * w.conf)):
        # 1) seam split: partially overlapping reads on one row that repeat each other's tail/head
        merged = False
        for k in kept:
            if _overlap_min(w.box, k.box) > 0.05 and abs(w.cy - k.cy) < 0.5 * max(w.height, k.height):
                st = _stitch(w, k)
                if st:
                    kept.remove(k)
                    kept.append(st)
                    merged = True
                    break
        if merged:
            continue
        # 2) duplicates / fragments contained in a longer read are discarded
        if any(_iou(w.box, k.box) >= thresh or _overlap_min(w.box, k.box) > 0.6 for k in kept):
            continue
        kept.append(w)
    return sorted(kept, key=lambda w: (round(w.cy / max(w.height, 1)), w.cx))


def _tiles(w: int, h: int, tile: int, overlap: int):
    xs = list(range(0, max(w - overlap, 1), tile - overlap)) or [0]
    ys = list(range(0, max(h - overlap, 1), tile - overlap)) or [0]
    for y in ys:
        for x in xs:
            yield x, y, min(x + tile, w), min(y + tile, h)


def _rapid_words(img: Image.Image, page: int, min_conf: float, tile: int = 1600, overlap: int = 160,
                 progress: Optional[Callable[[float], None]] = None) -> List[OcrWord]:
    eng = _rapid()
    out: List[OcrWord] = []
    tiles = list(_tiles(img.width, img.height, tile, overlap))
    for n, (x0, y0, x1, y1) in enumerate(tiles):
        crop = img.crop((x0, y0, x1, y1))
        res, _ = eng(np.asarray(crop)[:, :, ::-1])  # RapidOCR expects BGR
        for pts, text, score in (res or []):
            conf = float(score)
            text = str(text).strip()
            if not text or conf < min_conf:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bw, bh = max(xs) - min(xs), max(ys) - min(ys)
            out.append(OcrWord(text, conf, (x0 + min(xs), y0 + min(ys), x0 + max(xs), y0 + max(ys)), page,
                               rotated=len(text) > 2 and bh > 1.5 * bw, source="rapidocr"))
        if progress:
            progress((n + 1) / len(tiles))
    return out


def _tesseract_words(img: Image.Image, page: int, min_conf: float) -> List[OcrWord]:
    import pytesseract

    d = pytesseract.image_to_data(img, config="--psm 11", output_type=pytesseract.Output.DICT)
    out = []
    for i, t in enumerate(d["text"]):
        t = t.strip()
        c = float(d["conf"][i]) / 100.0
        if t and c >= min_conf:
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            out.append(OcrWord(t, c, (x, y, x + w, y + h), page, source="tesseract"))
    return out


def mistral_markdown(data: bytes, filename: str, timeout: float = 180.0) -> List[str]:
    """Mistral OCR: returns one markdown string per page (no coordinates)."""
    import httpx

    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY is not set")
    b64 = base64.b64encode(data).decode()
    if filename.lower().endswith(".pdf") or data[:4] == b"%PDF":
        doc = {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"}
    else:
        mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
        doc = {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"}
    r = httpx.post("https://api.mistral.ai/v1/ocr", timeout=timeout,
                   headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                   json={"model": "mistral-ocr-latest", "document": doc, "include_image_base64": False})
    r.raise_for_status()
    return [p.get("markdown", "") for p in r.json().get("pages", [])]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scan_document(data: bytes, filename: str, engine: str = "auto", dpi: int = 200,
                  deskew: bool = True, min_conf: float = 0.45, force_ocr: bool = False, thorough: bool = True,
                  progress: Optional[Callable[[float, str], None]] = None) -> List[OcrPage]:
    """OCR every page.  ``engine``: auto | rapidocr | tesseract | mistral."""
    pages_in = render_pages(data, filename, dpi=dpi)
    avail = available_engines()
    if engine == "auto":
        engine = "rapidocr" if "rapidocr" in avail else ("tesseract" if "tesseract" in avail else "")
    results: List[OcrPage] = []
    mistral_pages: List[str] = []
    if engine == "mistral":
        mistral_pages = mistral_markdown(data, filename)

    for i, (img, native) in enumerate(pages_in):
        def prog(frac: float, msg: str = "") -> None:
            if progress:
                progress((i + frac) / len(pages_in), msg or f"Page {i + 1}/{len(pages_in)}")

        page = OcrPage(i, img.width, img.height, image=img)
        if len(native) >= 25 and not force_ocr:
            page.words, page.engine = native, "pdf-text"
            prog(1.0, f"Page {i + 1}: text layer")
        elif engine == "mistral":
            page.markdown = mistral_pages[i] if i < len(mistral_pages) else ""
            page.engine = "mistral"
            prog(1.0)
        elif engine in ("rapidocr", "tesseract"):
            proc, angle = preprocess(img, deskew=deskew)
            if engine == "rapidocr":
                # Detector recall depends on where tile seams fall, so "thorough" reads the page with two
                # different tilings and merges the results.
                tilings = [(1600, 160), (1200, 200)] if thorough else [(1600, 160)]
                words = []
                for n, (tile, ov) in enumerate(tilings):
                    words += _rapid_words(proc, i, min_conf, tile=tile, overlap=ov,
                                          progress=lambda f, n=n: prog((n + f) / len(tilings), f"Page {i + 1}: reading text"))
            else:
                words = _tesseract_words(proc, i, min_conf)
            page.words = dedupe(words)
            # keep native text layer words too (sparse text layer on top of a raster)
            if native:
                page.words = dedupe(page.words + native)
            page.engine = engine + (f" (deskew {angle:+.1f}°)" if angle else "")
        else:
            page.words = native
            page.engine = "pdf-text" if native else "none (install rapidocr-onnxruntime)"
        results.append(page)
    return results


# ---------------------------------------------------------------------------
# Line assembly
# ---------------------------------------------------------------------------

@dataclass
class TextLine:
    text: str
    box: Box
    conf: float
    page: int
    rotated: bool
    words: List[OcrWord] = field(default_factory=list)


def group_lines(words: List[OcrWord], gap_factor: float = 2.2) -> List[TextLine]:
    """Merge neighbouring OCR boxes that share a baseline into lines ("1,250 LF" + "(2) 2\" HDPE")."""
    lines: List[TextLine] = []
    for rotated in (False, True):
        ws = [w for w in words if w.rotated == rotated]
        if not ws:
            continue
        # horizontal text: primary axis x, secondary y.  vertical text: primary y, secondary x.
        def prim(w: OcrWord): return (w.box[0], w.box[2]) if not rotated else (w.box[1], w.box[3])
        def sec_c(w: OcrWord): return w.cy if not rotated else w.cx

        ws.sort(key=lambda w: (round(sec_c(w) / max(w.height, 1.0)), prim(w)[0]))
        used = [False] * len(ws)
        for i, w in enumerate(ws):
            if used[i]:
                continue
            used[i] = True
            group = [w]
            end = prim(w)[1]
            for j in range(i + 1, len(ws)):
                if used[j]:
                    continue
                v = ws[j]
                if abs(sec_c(v) - sec_c(w)) <= 0.6 * max(w.height, v.height) and \
                        0 <= prim(v)[0] - end <= gap_factor * max(w.height, v.height) * 1.5:
                    group.append(v)
                    used[j] = True
                    end = max(end, prim(v)[1])
            group.sort(key=lambda g: prim(g)[0])
            x0 = min(g.box[0] for g in group); y0 = min(g.box[1] for g in group)
            x1 = max(g.box[2] for g in group); y1 = max(g.box[3] for g in group)
            lines.append(TextLine(" ".join(g.text for g in group), (x0, y0, x1, y1),
                                  sum(g.conf for g in group) / len(group), w.page, rotated, group))
    lines.sort(key=lambda l: (l.page, round(l.box[1] / 20), l.box[0]))
    return lines

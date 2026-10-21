"""Turn as-built OCR text into a construction takeoff.

Reads: title block (project / sheet / date / revision ...), footage callouts
("(2) 2\" HDPE 1,250 LF"), stationing runs ("STA 10+00 TO 15+50"), structures
(HH-12, poles, cabinets, splice cases), and quantity tables ("4 EA ...").
Every item keeps its source text, page, confidence and position so a reviewer
can verify it on the drawing before it becomes a bill of materials.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.asbuilt_ocr import OcrPage, TextLine, group_lines

# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize(text: str, upper: bool = True) -> str:
    t = (text.replace("”", '"').replace("“", '"').replace("″", '"').replace("''", '"')
         .replace("’", "'").replace("‘", "'").replace("′", "'").replace("–", "-")
         .replace("—", "-").replace("×", "x"))
    t = re.sub(r"\s+", " ", t).strip()
    if not upper:
        return t
    t = t.upper()
    t = re.sub(r"\bL\.?\s?F\.?\b", "LF", t)
    # OCR digit confusions (O/I/L read for 0/1) inside numeric tokens that carry a footage unit
    def _fix(m: "re.Match[str]") -> str:
        token = m.group(1)
        if not any(char.isdigit() for char in token):
            return m.group(0)
        return token.replace("O", "0").replace("I", "1").replace("L", "1") + m.group(2)
    t = re.sub(r"(?<![A-Z0-9])([\dOIL]{1,12}(?:,[\dOIL]{3}){0,3})(\s*(?:LF|FT\b|'))", _fix, t)
    return t


def parse_size(s: str) -> Optional[float]:
    """'1-1/4' -> 1.25, '3/4' -> 0.75, '2' -> 2.0."""
    s = s.strip().replace(" ", "-")
    try:
        if "-" in s and "/" in s:
            whole, frac = s.split("-", 1)
            return float(whole) + float(Fraction(frac))
        if "/" in s:
            return float(Fraction(s))
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


def fmt_size(v: float) -> str:
    """1.25 -> 1-1/4", 0.25 -> 1/4", 2 -> 2"."""
    whole = int(v)
    frac = Fraction(v - whole).limit_denominator(16)
    if frac == 0:
        return f'{whole}"'
    if frac == 1:
        return f'{whole + 1}"'
    return f'{whole}-{frac}"' if whole else f'{frac}"'


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
LENGTH_RE = re.compile(rf"(?<![\d.+/])(?P<qty>{_NUM})\s*(?P<unit>LF|LIN\.? ?FT|FEET|FT\.?|')(?![A-Z0-9])")
STATION_RE = re.compile(
    r"STA\.?\s*(?P<a1>\d+)\+(?P<a2>\d{2}(?:\.\d+)?)\s*(?:TO|-|THRU|THROUGH)\s*(?:STA\.?\s*)?(?P<b1>\d+)\+(?P<b2>\d{2}(?:\.\d+)?)")
SIZE_RE = re.compile(
    r'(?P<size>\d{1,6}\s*-\s*\d{1,6}/\d{1,6}|\d{1,6}/\d{1,6}|\d{1,6}(?:\.\d{1,6})?)'
    r'\s*(?:"|IN\b|INCH(?:ES)?\b)')
COUNT_RE = re.compile(r"\((?P<n1>\d+)\)\s*(?=\d)|(?<![\d.])(?P<n2>\d+)\s*(?:-WAY|\s*WAY)")
FIBER_CT_RE = re.compile(r"\b(?P<ct>\d{1,3})\s*(?:CT|COUNT|FIBER|F)\b(?!\w)")
QTY_RE = re.compile(r"\b(?:QTY|QUANTITY|COUNT)\s*[:=]?\s*(?P<q>\d+)\b")
TABLE_RE = re.compile(r"^\s*(?P<q>\d+)\s*(?P<u>EA|EACH|LF|FT|PCS|ROLL|SET|LOT|CT)\b\.?\s*[-:]?\s*(?P<d>.{4,})$")

CATEGORY_RULES: List[Tuple[str, re.Pattern]] = [
    ("Directional Bore", re.compile(r"\b(BORE|BORING|HDD|DIRECTIONAL)\b")),
    ("Trench", re.compile(r"\b(TRENCH|OPEN[ -]?CUT)\b")),
    ("Plow", re.compile(r"\b(PLOW|PLOWED|VIBRATORY)\b")),
    ("Aerial", re.compile(r"\b(AERIAL|STRAND|MESSENGER|OVERLASH|ADSS|FIG(?:URE)?[ -]?8)\b")),
    ("Conduit", re.compile(r"\b(CONDUIT|DUCT|INNERDUCT|HDPE|PVC|SCH ?40|SDR)\b")),
    ("Fiber Cable", re.compile(r"\b(FIBER|CABLE|FO)\b")),
    ("Slack", re.compile(r"\b(SLACK|LOOP)\b")),
    ("Pole", re.compile(r"\bPOLE\b")),
]

STRUCT_WORDS = {
    "Handhole": r"HANDHOLE|HAND HOLE|HH",
    "Pull Box": r"PULL ?BOX|PB|PH",
    "Manhole": r"MANHOLE|MH",
    "Vault": r"VAULT",
    "Cabinet": r"CABINET|CAB",
    "Pedestal": r"PEDESTAL|PED|FLOWER ?POT",
    "Splice Case": r"SPLICE CASE|SPLICE CLOSURE|SPLICE|SC",
    "Pole": r"POLE|PL",
    "Anchor": r"ANCHOR|GUY",
    "Riser": r"RISER",
    "Marker": r"MARKER",
}
_ID_REQUIRED = {"HH", "PB", "PH", "MH", "CAB", "PED", "SC", "PL"}  # short abbreviations need an ID
STRUCT_RE = re.compile(
    r"\b(?P<word>" + "|".join(f"(?:{v})" for v in STRUCT_WORDS.values()) + r")\b[\s\-#.]*(?P<id>[A-Z]?\d{1,4}[A-Z]?)?(?![\d])")
DIM_RE = re.compile(r"(\d{1,3})\s*(?:\"|IN)?\s*X\s*(\d{1,3})\s*(?:\"|IN)?(?:\s*X\s*(\d{1,3}))?")


def _struct_type(word: str) -> str:
    for name, alt in STRUCT_WORDS.items():
        if re.fullmatch(alt, word):
            return name
    return word.title()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class AsBuiltResult:
    items: pd.DataFrame
    title_block: Dict[str, str]
    lines: List[TextLine]
    is_as_built: bool = False
    notes: List[str] = field(default_factory=list)


ITEM_COLS = ["include", "page", "category", "description", "size", "count", "qty", "unit", "total_qty",
             "source_text", "conf", "flags", "x0", "y0", "x1", "y1"]


def _classify(text: str) -> str:
    for name, rx in CATEGORY_RULES:
        if rx.search(text):
            return name
    return ""


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


# ---------------------------------------------------------------------------
# Title block
# ---------------------------------------------------------------------------

TITLE_KEYS = {
    "project": r"PROJECT(?: NAME| TITLE)?|JOB NAME|PROJ\.?",
    "job_no": r"JOB (?:NO|NUMBER|#)\.?|PROJECT (?:NO|NUMBER|#)\.?|WO|WORK ORDER(?: NO)?",
    "sheet": r"SHEET(?: NO| NUMBER| #)?\.?|DWG\.? NO|DRAWING (?:NO|NUMBER)",
    "date": r"DATE|DATED",
    "revision": r"REV(?:ISION)?\.?",
    "scale": r"SCALE",
    "drawn_by": r"DRAWN(?: BY)?|DRN\.?|DESIGNED BY|ENGINEER|ENGR\.?",
    "client": r"CLIENT|CUSTOMER|OWNER",
    "location": r"LOCATION|CITY|COUNTY|ADDRESS",
}
DATE_RE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\.? \d{1,2},? \d{4})\b")


_LABEL_RE = re.compile(r"^(?:" + "|".join(TITLE_KEYS.values()) + r")\s*[:#=.\-]?\s*$")


def _near_value(label: TextLine, lines: List[TextLine]) -> str:
    h = max(label.box[3] - label.box[1], 1)
    best, best_d = "", 1e9
    for ln in lines:
        if ln is label or ln.page != label.page or ln.rotated != label.rotated or _LABEL_RE.match(normalize(ln.text)):
            continue
        same_row = abs((ln.box[1] + ln.box[3]) / 2 - (label.box[1] + label.box[3]) / 2) < h * 0.8
        right = ln.box[0] >= label.box[2] - h * 0.5 and ln.box[0] - label.box[2] < h * 14
        below = 0 <= ln.box[1] - label.box[3] < h * 3 and ln.box[0] < label.box[2] and ln.box[2] > label.box[0]
        if (same_row and right) or below:
            d = abs(ln.box[0] - label.box[2]) + abs(ln.box[1] - label.box[1]) * (1 if same_row else 3) + (0 if same_row else h * 2)
            if d < best_d:
                best, best_d = ln.text.strip(), d
    return best


def extract_title_block(lines: List[TextLine], full_text: str) -> Dict[str, str]:
    tb: Dict[str, str] = {}
    for key, alt in TITLE_KEYS.items():
        rx = re.compile(rf"^(?:{alt})\s*[:#=.\-]?\s*(?P<v>.*)$", re.I)
        for ln in lines:
            m = rx.match(normalize(ln.text, upper=False))
            if not m:
                continue
            val = m.group("v").strip(" :#=.-")
            if not val:
                val = _near_value(ln, lines)
            if val and len(val) < 80:
                tb[key] = val.strip()
                break
    if "date" not in tb:
        m = DATE_RE.search(full_text)
        if m:
            tb["date"] = m.group(1)
    return tb


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_takeoff(pages: List[OcrPage], min_conf: float = 0.0) -> AsBuiltResult:
    lines: List[TextLine] = []
    notes: List[str] = []
    for p in pages:
        if p.markdown and not p.words:
            notes.append(f"Page {p.page + 1}: Mistral OCR returned text without positions.")
            lines.extend(_markdown_lines(p))
        else:
            lines.extend(group_lines(p.words))

    full_text = "\n".join(normalize(l.text) for l in lines)
    rows: List[dict] = []
    seen_struct: set = set()

    for idx, ln in enumerate(lines):
        t = normalize(ln.text)
        if not t:
            continue
        # neighbouring lines on the same page help classify short callouts ("1,250 LF" next to "2\" HDPE")
        near = _neighbours(lines, idx)
        rows.extend(_station_items(ln, t, near))
        lengths = _length_items(ln, t, near)
        rows.extend(lengths)
        structs = _struct_items(ln, t, seen_struct)
        rows.extend(structs)
        if not structs and not lengths:
            rows.extend(_table_items(ln, t))

    df = pd.DataFrame(rows, columns=ITEM_COLS) if rows else pd.DataFrame(columns=ITEM_COLS)
    df = _flag_duplicates(df)
    df = _crosscheck_stations(df)
    tb = extract_title_block(lines, full_text)
    is_ab = bool(re.search(r"AS[- ]?BUILT|RECORD (?:DRAWING|DOCUMENT)|CONFORMED", full_text))
    if not is_ab:
        notes.append("No 'AS-BUILT' / 'RECORD DRAWING' stamp was read - confirm this is the as-built set.")
    return AsBuiltResult(df, tb, lines, is_ab, notes)


def _markdown_lines(p: OcrPage) -> List[TextLine]:
    out = []
    for i, raw in enumerate(p.markdown.splitlines()):
        raw = re.sub(r"[|#*`]+", " ", raw).strip()
        if raw:
            out.append(TextLine(raw, (0, i * 10, 1, i * 10 + 8), 0.9, p.page, False))
    return out


def _neighbours(lines: List[TextLine], idx: int, radius: float = 3.0) -> List[str]:
    """Nearby lines with the same text orientation, nearest first.  Callout pieces ("1,250 LF" next to
    "(2) 2\" HDPE") borrow context from these, but never from lines at a different angle."""
    ln = lines[idx]
    h = max(ln.box[3] - ln.box[1], 1) if not ln.rotated else max(ln.box[2] - ln.box[0], 1)
    found = []
    for j in range(max(0, idx - 6), min(len(lines), idx + 7)):
        o = lines[j]
        if j == idx or o.page != ln.page or o.rotated != ln.rotated:
            continue
        dx = max(o.box[0] - ln.box[2], ln.box[0] - o.box[2], 0)
        dy = max(o.box[1] - ln.box[3], ln.box[1] - o.box[3], 0)
        if dx < h * 20 and dy < h * radius:
            found.append((dx + dy, normalize(o.text)))
    return [t for _, t in sorted(found)]


def _context(t: str, near: List[str]) -> Tuple[str, str, int, bool]:
    """(category, size, count, borrowed) for a line, using its own text first and then the nearest
    neighbour that supplies each piece."""
    cat = _classify(t)
    borrowed = False
    if not cat:
        for n in near:
            cat = _classify(n)
            if cat:
                borrowed = True
                break
    size, count = _spec(t)
    if not size:
        for n in near:
            size, c2 = _spec(n)
            if size:
                count = count if count > 1 else c2
                borrowed = True
                break
    return cat, size, count, borrowed


def _row(ln: TextLine, **kw) -> dict:
    d = {c: "" for c in ITEM_COLS}
    d.update(include=True, page=ln.page + 1, conf=round(ln.conf, 2), source_text=ln.text,
             x0=ln.box[0], y0=ln.box[1], x1=ln.box[2], y1=ln.box[3], flags="", count=1, size="")
    d.update(kw)
    if ln.conf < 0.6:
        d["flags"] = (d["flags"] + " low-confidence").strip()
    qty, cnt = d.get("qty") or 0, d.get("count") or 1
    d["total_qty"] = qty * cnt if d.get("unit") == "LF" else qty
    return d


def _spec(t: str) -> Tuple[str, int]:
    """(size text, parallel count) from a conduit/cable callout like '(2) 2" HDPE'."""
    m = SIZE_RE.search(t)
    size = fmt_size(parse_size(m.group("size"))) if m and parse_size(m.group("size")) else ""
    c = COUNT_RE.search(t)
    count = int(c.group("n1") or c.group("n2")) if c else 1
    return size, max(count, 1)


def _length_items(ln: TextLine, t: str, near: List[str]) -> List[dict]:
    out = []
    matches = list(LENGTH_RE.finditer(t))
    for segment in re.split(
            r'\bAND\b|[;\n]|,\s*(?=(?:\(\d+\)\s*)?\d+(?:\s*-\s*\d+/\d+|\s*/\s*\d+)?\s*(?:"|IN\b))', t):
        segment_matches = list(LENGTH_RE.finditer(segment))
        for m in segment_matches:
            qty = _to_float(m.group("qty"))
            unit = m.group("unit")
            if unit == "'" and not re.search(r"\d\s*'\s*(?:OF|[A-Z])", segment[m.start():m.end() + 3]) and qty < 20:
                continue
            if "POLE" in segment and not any(rx.search(segment) for name, rx in CATEGORY_RULES if name != "Pole"):
                continue  # "40' CLASS 4 POLE": a pole height, not footage
            context_text = segment if len(matches) > 1 else t
            if len(segment_matches) > 1:
                cat, size, count, borrowed = "", "", 1, False
            else:
                cat, size, count, borrowed = _context(context_text, [] if len(matches) > 1 else near)
            if cat == "Pole":
                continue
            if re.search(r"\bDEPTH|COVER|MIN\b|\bAT\b \d+'?\s*DEEP", segment) and qty < 20:
                continue  # cover/depth notes
            ambiguous = len(matches) > 1 and (not cat or not size or len(segment_matches) > 1)
            cat = cat or "Unclassified"
            desc = cat
            if size:
                desc += f' {size}'
            fiber_ct = FIBER_CT_RE.search(segment)
            if fiber_ct:
                desc += f' {fiber_ct.group("ct")}ct'
            if count > 1:
                desc += f" x{count}"
            if cat == "Directional Bore" and re.search(r"\b(HDPE|CONDUIT|DUCT)\b", segment):
                desc += " conduit"
            flags = "ambiguous callout segment - verify" if ambiguous else (
                "type/size from nearby text - verify" if borrowed else "")
            out.append(_row(ln, category=cat, description=desc, size=size, count=count, qty=qty, unit="LF",
                            flags=flags))
    return out


def _station_items(ln: TextLine, t: str, near: List[str]) -> List[dict]:
    out = []
    for m in STATION_RE.finditer(t):
        a = int(m.group("a1")) * 100 + float(m.group("a2"))
        b = int(m.group("b1")) * 100 + float(m.group("b2"))
        qty = round(abs(b - a), 2)
        if qty <= 0:
            continue
        cat, size, count, _ = _context(t, near)
        cat = cat or "Station Run"
        out.append(_row(ln, category=cat, description=f"{cat} (stationing {m.group(0)})", size=size, count=count,
                        qty=qty, unit="LF", flags="stationing - cross-check vs callout"
                        if LENGTH_RE.search(t) else "from stationing"))
    return out


def _struct_items(ln: TextLine, t: str, seen: set) -> List[dict]:
    out = []
    if STATION_RE.search(t) and not re.search(r"\b(HH|MH|PB|CAB|POLE)\b", t):
        return out
    qm = QTY_RE.search(t)
    tm = TABLE_RE.match(t)
    lead_qty = float(tm.group("q")) if tm else None
    for m in STRUCT_RE.finditer(t):
        word, sid = m.group("word"), m.group("id")
        if sid and re.match(r"\s*[xX]\s*\d", t[m.end():]):
            sid = None
        if word in _ID_REQUIRED and not sid:
            continue
        stype = _struct_type(word)
        if stype == "Pole" and word == "POLE" and not sid and LENGTH_RE.search(t):
            continue
        key = (ln.page, stype, sid or f"{ln.box[0]:.0f},{ln.box[1]:.0f}")
        if sid and key in seen:
            continue
        seen.add(key)
        dm = DIM_RE.search(t)
        size = f'{dm.group(1)}x{dm.group(2)}' + (f'x{dm.group(3)}' if dm.group(3) else "") if dm and stype in (
            "Handhole", "Pull Box", "Vault", "Manhole", "Cabinet") else ""
        qty = float(qm.group("q")) if qm else (lead_qty or 1.0)
        if stype == "Pole":
            pm = re.search(r"(\d{2})'\s*(?:CL(?:ASS)?\.?\s*(\d+|H\d))?", t)
            if pm:
                size = f"{pm.group(1)}'" + (f" CL{pm.group(2)}" if pm.group(2) else "")
        label = f"{stype} {sid or ''}".strip()
        out.append(_row(ln, category="Structure", description=label + (f" {size}" if size else ""), size=size,
                        qty=qty, unit="EA", flags="" if sid or qm or lead_qty else "no ID read"))
    return out


def _table_items(ln: TextLine, t: str) -> List[dict]:
    m = TABLE_RE.match(t)
    if not m or STRUCT_RE.search(m.group("d")) and False:
        return []
    desc = m.group("d").strip()
    if not re.search(r"[A-Z]{3}", desc) or STATION_RE.search(t):
        return []
    unit = {"EACH": "EA", "FT": "LF"}.get(m.group("u"), m.group("u"))
    return [_row(ln, category="Table line", description=desc.title(), qty=float(m.group("q")), unit=unit,
                 flags="from quantity table")]


def _crosscheck_stations(df: pd.DataFrame) -> pd.DataFrame:
    """Exclude stationing only when a nearby callout has matching material specifications."""
    if df.empty:
        return df
    st = df["flags"].astype(str).str.contains("from stationing|stationing - cross-check", regex=True)
    callouts = df[(df["unit"] == "LF") & ~st & df["include"].astype(bool)]
    for i in df[st].index:
        same = callouts[(callouts["page"] == df.at[i, "page"]) &
                        ((callouts["qty"] - df.at[i, "qty"]).abs() <= 1.5)]
        if same.empty:
            continue
        height = max(float(df.at[i, "y1"]) - float(df.at[i, "y0"]), 1)
        compatible = same[
            (same["category"] == df.at[i, "category"]) &
            (same["size"].fillna("") == df.at[i, "size"]) &
            (same["count"].fillna(1) == df.at[i, "count"])
        ]
        def associated(row: pd.Series) -> bool:
            if row["source_text"] == df.at[i, "source_text"]:
                return True
            dx = max(float(row["x0"]) - float(df.at[i, "x1"]),
                     float(df.at[i, "x0"]) - float(row["x1"]), 0)
            dy = max(float(row["y0"]) - float(df.at[i, "y1"]),
                     float(df.at[i, "y0"]) - float(row["y1"]), 0)
            return dx <= height * 4 and dy <= height * 4

        nearby = compatible[compatible.apply(associated, axis=1)]
        if not nearby.empty:
            df.at[i, "include"] = False
            df.at[i, "flags"] = "matches nearby compatible callout - not double counted"
        else:
            df.at[i, "flags"] = "matching footage length - verify route/specifications"
    return df


def _flag_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    key = df[["category", "description", "qty", "unit"]].astype(str).agg("|".join, axis=1)
    dup = key.duplicated(keep="first") & df["category"].isin(["Directional Bore", "Trench", "Plow", "Aerial", "Conduit",
                                                              "Fiber Cable", "Slack"])
    df.loc[dup, "flags"] = (df.loc[dup, "flags"] + " possible duplicate callout").str.strip()
    return df


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------

def summarize(items: pd.DataFrame) -> pd.DataFrame:
    """Totals of the included items by category / description."""
    if items.empty:
        return items
    inc = items[items["include"].astype(bool)]
    g = (inc.groupby(["category", "description", "unit"], dropna=False)
         .agg(lines=("qty", "size"), qty=("total_qty", "sum")).reset_index())
    g["qty"] = g["qty"].round(1)
    return g.sort_values(["category", "description"])


# ---------------------------------------------------------------------------
# Map takeoff -> Procure-Me materials catalog
# ---------------------------------------------------------------------------

def _material_size(name: str) -> Optional[float]:
    m = SIZE_RE.search(normalize(name))
    return parse_size(m.group("size")) if m else None


def _hh_dims(name: str) -> Optional[Tuple[int, int]]:
    n = normalize(name)
    m = re.search(r"(\d{1,3})\s{0,3}(\"|')?\s{0,3}X\s{0,3}(\d{1,3})", n)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(3))
    if "'" in n[m.start():m.end() + 2]:  # feet -> inches
        a, b = a * 12, b * 12
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def _is_handhole(description: str) -> bool:
    return bool(re.search(r"\b(?:HAND\s?HOLE|HH(?:[- #]?\w+)?)\b", description, re.I))


def _normalized_unit(unit: str) -> str:
    normalized = re.sub(r"[^A-Z]", "", str(unit).upper())
    if normalized in {"LF", "FT", "FOOT", "FEET", "LINEARFT"}:
        return "LF"
    if normalized in {"EA", "EACH", "PC", "PCS", "UNIT"}:
        return "EA"
    return normalized


def match_material(row: pd.Series, materials: List[dict]) -> Tuple[Optional[dict], str]:
    """Best catalog match for a takeoff row, with a short reason."""
    cat = row["category"]
    size = parse_size(str(row["size"]).replace('"', "")) if row["size"] else None
    desc = str(row["description"])

    def pick(pred) -> Optional[dict]:
        return next((m for m in materials if pred(m)), None)

    if cat in ("Directional Bore", "Trench", "Plow", "Conduit") and size is not None:
        m = pick(lambda m: m.get("category") == "Conduit" and _normalized_unit(m.get("unit", "")) == "LF" and
                 _material_size(m["name"]) == size)
        if m:
            return m, f'conduit size {fmt_size(size)}'
    if cat == "Aerial" and size is not None:
        m = pick(lambda m: m.get("category") == "Aerial" and _normalized_unit(m.get("unit", "")) == "LF" and
                 "messenger" in m["name"].lower() and _material_size(m["name"]) == size) or \
            pick(lambda m: m.get("category") == "Aerial" and _normalized_unit(m.get("unit", "")) == "LF" and
                 "strand" in m["name"].lower() and _material_size(m["name"]) == size)
        if m:
            return m, "strand size"
    handhole = cat == "Structure" and _is_handhole(desc)
    if handhole and row["size"]:
        want = tuple(sorted(int(x) for x in re.findall(r"\d+", str(row["size"]))[:2]))
        if len(want) == 2:
            m = pick(lambda m: m.get("category") == "Hand Holes" and _hh_dims(m["name"]) == want)
            if m:
                return m, "handhole size"
    if cat == "Structure" and re.search(r"FLOWER|PEDESTAL|PED", desc.upper()):
        m = pick(lambda m: "flowerpot" in m["name"].lower())
        if m:
            return m, "flowerpot"
    if handhole and row["size"] and re.match(r"^\d+x\d+", str(row["size"])):
        want = tuple(sorted(int(x) for x in re.findall(r"\d+", str(row["size"]))[:2]))
        cands = [(m, _hh_dims(m["name"])) for m in materials if m.get("category") == "Hand Holes"]
        cands = [(m, d) for m, d in cands if d]
        if len(want) == 2 and cands:
            import math
            m, d = min(cands, key=lambda md: abs(math.log((md[1][0] * md[1][1]) / (want[0] * want[1]))))
            return m, f"APPROX nearest HH size ({want[0]}x{want[1]} -> {d[0]}x{d[1]})"
    # Fuzzy matching is limited to materials with compatible types, dimensions, and units.
    type_categories = {
        "Directional Bore": {"Conduit"}, "Trench": {"Conduit"}, "Plow": {"Conduit"}, "Conduit": {"Conduit"},
        "Aerial": {"Aerial"}, "Fiber Cable": {"Cable"},
    }
    eligible = []
    for material in materials:
        if material.get("category") not in type_categories.get(cat, set()):
            continue
        if _normalized_unit(material.get("unit", "")) != _normalized_unit(row["unit"]):
            continue
        material_size = _material_size(material["name"])
        if size is not None and material_size != size:
            continue
        if cat == "Aerial":
            desc_lower, name_lower = desc.lower(), material["name"].lower()
            if any(token in desc_lower for token in ("strand", "messenger")) and not any(
                    token in name_lower for token in ("strand", "messenger")):
                continue
            if any(token in desc_lower for token in ("fiber", "cable")) and not any(
                    token in name_lower for token in ("fiber", "cable")):
                continue
        if cat == "Fiber Cable":
            fiber_ct = FIBER_CT_RE.search(desc.upper())
            material_ct = FIBER_CT_RE.search(material["name"].upper())
            if not re.search(r"\b(?:FIBER|CABLE)\b", material["name"], re.I) or \
                    (fiber_ct and (not material_ct or fiber_ct.group("ct") != material_ct.group("ct"))):
                continue
        eligible.append(material)
    names = {m["name"].lower(): m for m in eligible}
    hit = difflib.get_close_matches(desc.lower(), list(names), n=1, cutoff=0.72)
    if hit:
        return names[hit[0]], "name similarity"
    toks = [w for w in re.findall(r"[a-z0-9]+", desc.lower()) if len(w) > 2]
    best, score = None, 0
    for m in eligible:
        mt = set(re.findall(r"[a-z0-9]+", m["name"].lower()))
        s = sum(1 for w in toks if w in mt)
        if s > score:
            best, score = m, s
    if best and score >= 2:
        return best, "keyword overlap"
    return None, ""


def to_bom(items: pd.DataFrame, materials: List[dict]) -> pd.DataFrame:
    """Included items -> priced-ready BOM lines (Description / Qty / Unit / Unit Cost)."""
    rows = []
    inc = items[items["include"].astype(bool)] if not items.empty else items
    for _, r in inc.iterrows():
        mat, why = match_material(r, materials)
        rows.append({
            "Description": mat["name"] if mat else r["description"],
            "Qty": float(r["total_qty"] or 0),
            "Unit": (mat or {}).get("unit", r["unit"]),
            "Unit Cost": float(mat["unit_cost"]) if mat and mat.get("unit_cost") is not None else 0.0,
            "Matched": bool(mat), "Match basis": why,
            "From takeoff": r["description"], "Page": r["page"], "Flags": r["flags"],
        })
    bom = pd.DataFrame(rows)
    if bom.empty:
        return bom
    agg = bom.groupby(["Description", "Unit", "Unit Cost", "Matched", "Match basis"], as_index=False).agg(
        Qty=("Qty", "sum"), **{"From takeoff": ("From takeoff", lambda s: "; ".join(sorted(set(s))[:4]))})
    return agg[["Description", "Qty", "Unit", "Unit Cost", "Matched", "Match basis", "From takeoff"]]

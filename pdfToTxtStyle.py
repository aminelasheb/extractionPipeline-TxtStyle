# pip install pymupdf
import fitz
import csv
import re
import sys
import glob
from pathlib import Path
from typing import Iterable, Tuple


def to_hex_color(c):
    if isinstance(c, int):
        return f"#{c:06x}"
    if isinstance(c, (tuple, list)) and len(c) >= 3:
        vals = []
        for x in c[:3]:
            vals.append(int(round(x * 255 if x <= 1 else x)))
        return "#{:02x}{:02x}{:02x}".format(*vals)
    return "#000000"


STYLE_PATTERNS = [
    ("black",   ["black", "extrablack", "condblack", "ultrablack"]),
    ("bold",    ["bold", "heavy", "strong"]),
    ("semibold",["semibold", "demibold", "demi"]),
    ("medium",  ["medium"]),
    ("regular", ["regular", "book", "roman"]),
    ("light",   ["light", "thin", "extralight", "ultralight"]),
]
ITALIC_PATTERNS = ["italic", "oblique"]


def normalize_style(fontname: str) -> Tuple[str, str]:
    base = re.sub(r"^[A-Z]{6}\+", "", fontname or "")
    parts = base.split("-")
    family = parts[0].strip() if parts else base.strip()
    variant = "-".join(parts[1:]).lower() if len(parts) > 1 else base[len(family):].lower()
    weight = "regular"
    if variant:
        for tag, keys in STYLE_PATTERNS:
            if any(k in variant for k in keys):
                weight = tag
                break
    italic = any(k in variant for k in ITALIC_PATTERNS)
    return family, (weight + ("/italic" if italic else ""))


def rect_intersection_area(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    x0 = max(ax0, bx0); y0 = max(ay0, by0)
    x1 = min(ax1, bx1); y1 = min(ay1, by1)
    return max(0, x1 - x0) * max(0, y1 - y0)


def style_for_word_from_spans(word_bbox, spans):
    best = None
    best_area = 0.0
    for s in spans:
        area = rect_intersection_area(word_bbox, s["bbox"])
        if area > best_area:
            best_area = area
            fam, style = normalize_style(s.get("font", ""))
            size = float(s.get("size", 0.0))
            color_hex = to_hex_color(s.get("color", 0))
            best = (fam, style, size, color_hex)
    return best or ("", "regular", 0.0, "#000000")


def weighted_dominant_style(spans):
    weights = {}
    for s in spans:
        fam, tag = normalize_style(s.get("font", ""))
        size = float(s.get("size", 0.0))
        col = to_hex_color(s.get("color", 0))
        key = (fam, tag, size, col)
        weights[key] = weights.get(key, 0) + max(1, len(s.get("text", "")))
    return max(weights.items(), key=lambda kv: kv[1])[0]


def export_phrase_compact_from_doc(doc: fitz.Document, out_csv: str, pages: Iterable[int]):
    page_indexes = pages
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["phrase", "font_family", "size", "color_hex", "style_tag", "overrides"])

        for p in page_indexes:
            page = doc[p]
            d = page.get_text("dict")

            for b in d.get("blocks", []):
                if b.get("type", 0) != 0:
                    continue

                for l in b.get("lines", []):
                    spans, texts = [], []

                    for s in l.get("spans", []):
                        t = s.get("text", "")
                        if t == "":
                            continue  
                        spans.append({
                            "bbox": tuple(s["bbox"]),
                            "font": s.get("font", ""),
                            "size": float(s.get("size", 0.0)),
                            "color": s.get("color", 0),
                            "text": t
                        })
                        texts.append(t)

                    if not spans:
                        continue

                    raw_phrase = "".join(texts)
                    phrase = raw_phrase
                    fam_d, tag_d, size_d, col_d = weighted_dominant_style(spans)

                    overrides = []
                    words = page.get_text("words")

                    x0 = min(s["bbox"][0] for s in spans)
                    y0 = min(s["bbox"][1] for s in spans)
                    x1 = max(s["bbox"][2] for s in spans)
                    y1 = max(s["bbox"][3] for s in spans)
                    lbbox = (x0, y0, x1, y1)

                    for (wx0, wy0, wx1, wy1, word, *_rest) in words:
                        wbbox = (wx0, wy0, wx1, wy1)
                        if rect_intersection_area(lbbox, wbbox) <= 0:
                            continue

                        fam_w, tag_w, size_w, col_w = style_for_word_from_spans(wbbox, spans)

                        if (fam_w != fam_d) or (tag_w != tag_d) or abs(size_w - size_d) > 1e-6 or (col_w.lower() != col_d.lower()):
                            if word.strip():
                                overrides.append(f"{word}|{fam_w}|{size_w:g}|{col_w}|{tag_w}")

                    w.writerow([
                        phrase,
                        fam_d,
                        f"{size_d:g}",
                        col_d,
                        tag_d,
                        "||".join(overrides) if overrides else ""
                    ])

    print(f"[OK] Export: {out_csv}")


def main():
    # Usage: python pdfToTxtStyle.py <pdf_path> <output_folder> <all(true|false)> [first_page] [last_page]
    if len(sys.argv) < 4:
        print("Usage: python pdfToTxtStyle.py <pdf_path> <output_folder> <all(true|false)> [first_page] [last_page]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = Path(sys.argv[2])
    all_flag = sys.argv[3].lower().strip()

    with fitz.open(pdf_path) as doc:
        total = len(doc)
        print(f"PDF : {pdf_path}")
        print(f"Nombre de pages detectees : {total}")

        if all_flag == "true" or all_flag == "":
            first_page = 1
            last_page = total
        else:
            if len(sys.argv) < 6:
                print("Error: need first_page and last_page when all_flag is false")
                sys.exit(1)
            first_page = int(sys.argv[4])
            last_page = int(sys.argv[5])

            if first_page < 1:
                first_page = 1
            if last_page > total:
                last_page = total

        print(f"Pages traitees : {first_page} > {last_page}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # pages 1-based -> index 0-based
        for page_num in range(first_page, last_page + 1):
            page_idx = page_num - 1
            out_csv = output_dir / f"page_{page_num}.csv"
            print(f"->  Export page {page_num} vers {out_csv}")
            export_phrase_compact_from_doc(doc, str(out_csv), pages=[page_idx])


if __name__ == "__main__":
    main()

"""Reproducible reference/ParkFlow design measurements, normalized to 1600 x 900.

PDFs stay outside the repository. Text coordinates come from PDF extraction or
Tesseract OCR. Pixel metrics describe visual occupancy, not factual quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import os
from pathlib import Path
import re

import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw
import pytesseract
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "deck-design-analysis"
CANVAS = (1600, 900)
REFERENCES = [Path(r"C:\Downloads\FINAL_BDR_PITCHDECK.pdf"),
              Path(r"C:\Downloads\BDR_17_AC2026.pdf")]
os.environ.setdefault("OMP_THREAD_LIMIT", "1")


def area_union(boxes):
    mask = np.zeros((900, 1600), dtype=np.uint8)
    for box in boxes:
        x0, y0, x1, y1 = [round(v) for v in box]
        mask[max(0, y0):min(900, y1), max(0, x0):min(1600, x1)] = 1
    return round(100 * float(mask.mean()), 2)


def bounds(boxes):
    if not boxes:
        return None
    return [round(min(b[0] for b in boxes), 1), round(min(b[1] for b in boxes), 1),
            round(max(b[2] for b in boxes), 1), round(max(b[3] for b in boxes), 1)]


def pixels(im):
    im = im.convert("RGB").resize(CANVAS)
    arr = np.array(im)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    edges = cv2.Canny(cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY), 70, 160)
    palette = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
    colours = palette.getpalette()
    top = []
    for count, index in sorted(palette.getcolors(), reverse=True)[:10]:
        colour = colours[index * 3:index * 3 + 3]
        top.append({"hex": "#" + "".join(f"{v:02x}" for v in colour),
                    "area_pct": round(100 * count / (1600 * 900), 2)})
    bg = np.array([int(top[0]["hex"][i:i + 2], 16) for i in (1, 3, 5)])
    # Background-relative colour distance includes photography and solid panels.
    foreground = np.max(np.abs(arr.astype(float) - bg), axis=2) > 35
    tiles = edges.reshape(9, 100, 16, 100).mean(axis=(1, 3)) / 255
    return {"palette_quantized": top,
            "light_neutral_pct": round(float(((hsv[:, :, 1] < 20) & (hsv[:, :, 2] > 225)).mean() * 100), 2),
            "saturated_surface_pct": round(float(((hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 65)).mean() * 100), 2),
            "background_relative_foreground_pct": round(float(foreground.mean() * 100), 2),
            "edge_ink_pct": round(float((edges > 0).mean() * 100), 2),
            "edge_active_grid_pct": round(float((tiles > .015).mean() * 100), 2)}


def ocr_words(im):
    result = pytesseract.image_to_data(im, config="--psm 11", output_type=pytesseract.Output.DICT)
    words = []
    for i, text in enumerate(result["text"]):
        text = text.strip()
        if not text or float(result["conf"][i]) < 40:
            continue
        x, y, w, h = [result[key][i] for key in ("left", "top", "width", "height")]
        words.append({"text": text, "box": [x, y, x + w, y + h],
                      "confidence": round(float(result["conf"][i]), 1)})
    return words


def text_metrics(words):
    boxes = [w["box"] for w in words]
    content = " ".join(w["text"] for w in words)
    b = bounds(boxes)
    return {"word_count": len(words), "numeric_token_count": sum(bool(re.search(r"\d", w["text"])) for w in words),
            "text_box_union_pct": area_union(boxes), "text_bounds_px": b,
            "text_margins_pct": {"left": round(b[0] / 16, 2), "top": round(b[1] / 9, 2),
                                  "right": round((1600 - b[2]) / 16, 2),
                                  "bottom": round((900 - b[3]) / 9, 2)} if b else None,
            "text_preview": content[:260]}


def reference_page(task):
    path, page_no = task
    with fitz.open(path) as doc:
        page = doc[page_no]
        sx, sy = 1600 / page.rect.width, 900 / page.rect.height
        pix = page.get_pixmap(matrix=fitz.Matrix(sx, sy), alpha=False)
        im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        target = OUT / "renders" / path.stem / f"{page_no + 1:02d}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        im.save(target)
        words = [{"text": w[4], "box": [round(w[0] * sx, 2), round(w[1] * sy, 2),
                                                  round(w[2] * sx, 2), round(w[3] * sy, 2)]}
                 for w in page.get_text("words")]
        method = "native-pdf"
        if not words:
            words = ocr_words(im)
            method = "tesseract-psm11-confidence40"
        spans = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].strip():
                        spans.append({"text": span["text"], "font": span["font"],
                                      "size_native_pt": round(span["size"], 2),
                                      "size_at_1600_px": round(span["size"] * sx, 2),
                                      "colour": f"#{span['color']:06x}",
                                      "box": [round(v * (sx if i % 2 == 0 else sy), 2)
                                              for i, v in enumerate(span["bbox"])]})
        return {"document": path.name, "page": page_no + 1, "native_size_pt": list(page.rect)[2:],
                "text_method": method, **text_metrics(words), **pixels(im),
                "words": words, "spans": spans,
                "images": [{"box": [round(v * (sx if i % 2 == 0 else sy), 2) for i, v in enumerate(info["bbox"])],
                            "width": info["width"], "height": info["height"]}
                           for info in page.get_image_info()],
                "render": str(target.relative_to(ROOT)).replace("\\", "/")}


def measure_html():
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 900}, reduced_motion="reduce")
        page.goto((ROOT / "site-vnext" / "index.html").as_uri())
        page.wait_for_function("window.__pfReady === true")
        page.evaluate("document.fonts.ready")
        page.evaluate("""() => {
          document.querySelectorAll('.slide').forEach(s => s.classList.add('shown'));
          document.querySelectorAll('img').forEach(i => i.loading = 'eager');
        }""")
        page.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)")
        ids = page.locator('.slide:not([data-skip="true"])').evaluate_all("ss => ss.map(s => s.id)")
        for index, slide_id in enumerate(ids, 1):
            slide = page.locator("#" + slide_id)
            slide.evaluate("s => window.scrollTo(0, s.offsetTop)")
            page.wait_for_timeout(60)
            data = slide.evaluate("""s => {
              const sr=s.getBoundingClientRect();
              const box=r => [r.left-sr.left,r.top-sr.top,r.right-sr.left,r.bottom-sr.top].map(x=>Math.round(x*100)/100);
              const words=[], spans=[];
              const walk=document.createTreeWalker(s,NodeFilter.SHOW_TEXT);
              let n;
              while(n=walk.nextNode()) {
                const el=n.parentElement, cs=getComputedStyle(el);
                if(el.closest('script,style,svg,canvas,[hidden]') || cs.display==='none' || cs.visibility==='hidden') continue;
                const matches=[...n.textContent.matchAll(/\\S+/g)];
                for(const m of matches) {
                  const r=document.createRange();r.setStart(n,m.index);r.setEnd(n,m.index+m[0].length);
                  for(const rect of r.getClientRects()) if(rect.width && rect.height) words.push({text:m[0],box:box(rect)});
                }
                if(matches.length) spans.push({text:n.textContent.trim(),font:cs.fontFamily,size_at_1600_px:parseFloat(cs.fontSize),colour:cs.color,line_height:cs.lineHeight});
              }
              const h=s.querySelector('h1,h2'), hs=getComputedStyle(h), wr=s.querySelector('.wrap').getBoundingClientRect();
              return {id:s.id,title:s.dataset.title,appendix:s.hasAttribute('data-appendix'),words,spans,
                heading:{box:box(h.getBoundingClientRect()),font:hs.fontFamily,size_px:parseFloat(hs.fontSize),line_height:hs.lineHeight},
                wrap:box(wr),background:getComputedStyle(s).backgroundColor,
                images:[...s.querySelectorAll('img')].map(i=>({src:i.getAttribute('src'),box:box(i.getBoundingClientRect())}))};
            }""")
            image_bytes = page.screenshot(type="png")
            im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            target = OUT / "renders" / "parkflow" / f"{index:02d}-{slide_id}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            im.save(target)
            rows.append({"document": "ParkFlow HTML", "page": index, "text_method": "browser-dom-text-ranges",
                         **data, **text_metrics(data["words"]), **pixels(im),
                         "render": str(target.relative_to(ROOT)).replace("\\", "/")})
        browser.close()
    return rows


def contact_sheet(rows, target):
    cell_w, cell_h, columns = 400, 250, 4
    sheet = Image.new("RGB", (columns * cell_w, ((len(rows) + columns - 1) // columns) * cell_h), "#e5e7eb")
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(rows):
        x, y = i % columns * cell_w, i // columns * cell_h
        with Image.open(ROOT / row["render"]) as im:
            im.thumbnail((400, 225))
            sheet.paste(im, (x, y))
        draw.text((x + 8, y + 230), f"{row['page']:02d} | {row['word_count']} words | text {row['text_box_union_pct']}%", fill="#111827")
    sheet.save(target, quality=90)


def summary(rows):
    fonts, colours, sizes = Counter(), Counter(), Counter()
    for row in rows:
        for span in row.get("spans", []):
            weight = len(span["text"])
            fonts[span["font"]] += weight
            colours[span["colour"]] += weight
            sizes[round(span["size_at_1600_px"], 1)] += weight
    ocr_rows = [r for r in rows if "visible_ocr_word_count" in r]
    return {"pages": len(rows),
            "word_count_median": round(float(np.median([r["word_count"] for r in rows]))),
            "text_coverage_median_pct": round(float(np.median([r["text_box_union_pct"] for r in rows])), 2),
            "edge_active_grid_median_pct": round(float(np.median([r["edge_active_grid_pct"] for r in rows])), 2),
            "light_neutral_median_pct": round(float(np.median([r["light_neutral_pct"] for r in rows])), 2),
            "fonts_by_character": fonts.most_common(8), "text_colours_by_character": colours.most_common(10),
            "font_sizes_1600_px_by_character": sizes.most_common(12),
            "visible_ocr_word_count_median": round(float(np.median([r["visible_ocr_word_count"] for r in ocr_rows]))) if ocr_rows else None,
            "visible_ocr_text_coverage_median_pct": round(float(np.median([r["visible_ocr_text_box_union_pct"] for r in ocr_rows])), 2) if ocr_rows else None}


def enrich_ocr(row):
    if row["text_method"].startswith("tesseract"):
        words = row["words"]
    else:
        with Image.open(ROOT / row["render"]) as im:
            words = ocr_words(im)
    metrics = text_metrics(words)
    row.update({"visible_ocr_" + key: value for key, value in metrics.items()})
    # Word boxes are retained for native extraction; OCR glyph dimensions are a
    # separate measurement, not an estimate of a native font's point size.
    row["visible_ocr_glyph_height_median_px"] = round(float(np.median([w["box"][3] - w["box"][1] for w in words])), 1) if words else 0
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-only", action="store_true")
    parser.add_argument("--enrich-ocr", action="store_true", help="Use existing renders to compare all sources with the same OCR method")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    refs_file = OUT / "reference-measurements.json"
    if args.html_only or args.enrich_ocr:
        references = json.loads(refs_file.read_text(encoding="utf-8"))
    else:
        tasks = []
        for path in REFERENCES:
            with fitz.open(path) as doc:
                tasks.extend((path, i) for i in range(len(doc)))
        with ThreadPoolExecutor(max_workers=3) as pool:
            references = list(pool.map(reference_page, tasks))
        refs_file.write_text(json.dumps(references, indent=2), encoding="utf-8")
    current = json.loads((OUT / "parkflow-measurements.json").read_text(encoding="utf-8")) if args.enrich_ocr else measure_html()
    if args.enrich_ocr:
        with ThreadPoolExecutor(max_workers=3) as pool:
            references = list(pool.map(enrich_ocr, references))
            current = list(pool.map(enrich_ocr, current))
        refs_file.write_text(json.dumps(references, indent=2), encoding="utf-8")
    (OUT / "parkflow-measurements.json").write_text(json.dumps(current, indent=2), encoding="utf-8")
    groups = {path.stem: [r for r in references if r["document"] == path.name] for path in REFERENCES}
    groups["parkflow"] = current
    stats = {}
    for name, rows in groups.items():
        contact_sheet(rows, OUT / f"{name}-contact.jpg")
        stats[name + "-all"] = summary(rows)
    stats["BDR_17-main-content-p2-15"] = summary(groups["BDR_17_AC2026"][1:15])
    stats["FINAL_BDR-main-content-p2-12"] = summary(groups["FINAL_BDR_PITCHDECK"][1:12])
    stats["parkflow-opening-p3-12"] = summary(current[2:12])
    stats["parkflow-business-p13-22"] = summary(current[12:22])
    (OUT / "summary.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    fields = ["document", "page", "text_method", "word_count", "numeric_token_count", "text_box_union_pct",
              "light_neutral_pct", "saturated_surface_pct", "edge_ink_pct", "edge_active_grid_pct",
              "visible_ocr_word_count", "visible_ocr_text_box_union_pct", "visible_ocr_glyph_height_median_px"]
    with (OUT / "slide-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(references + current)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

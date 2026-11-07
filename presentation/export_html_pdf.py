"""Export the current HTML presentation as a vector PDF with one slide per page."""
import argparse
from pathlib import Path
from urllib.parse import unquote, urlsplit

import fitz
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def export(appendix=False):
    label = "Appendix" if appendix else "19-Slide-Deck"
    target = ROOT / "submission" / f"ParkFlow-{label}.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1600, "height": 900},
            reduced_motion="reduce",
            device_scale_factor=2,
        )
        url = (ROOT / "site-vnext" / "index.html").as_uri()
        page.goto(url + ("?appendix=1" if appendix else ""))
        page.wait_for_function("window.__pfReady === true")
        page.evaluate("document.fonts.ready")
        page.evaluate("""() => {
            document.querySelectorAll('.slide').forEach(s => s.classList.add('shown'));
            document.querySelectorAll('img').forEach(i => i.loading = 'eager');
        }""")
        page.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)")
        titles = page.locator('.slide:not([data-skip="true"])').evaluate_all(
            "ss => ss.map(s => s.querySelector('h1,h2').textContent.trim().replace(/\\s+/g, ' '))"
        )
        slide_ids = page.locator('.slide:not([data-skip="true"])').evaluate_all(
            "ss => ss.map(s => s.id)"
        )
        page.emulate_media(media="screen")
        page.add_style_tag(content="""
            @page { size: 1600px 900px; margin: 0; }
            html, body { width: 1600px !important; margin: 0 !important;
                padding: 0 !important; scroll-snap-type: none !important; }
            main { display: block !important; width: 1600px !important; margin: 0 !important; }
            *, *::before, *::after { animation: none !important; transition: none !important;
                print-color-adjust: exact !important; -webkit-print-color-adjust: exact !important; }
            .nav, .lift, .foot, .deck-ui, .deck-progress, #streak, .sr,
                .appendix-back { display: none !important; }
            .slide { width: 1600px !important; height: 900px !important;
                min-height: 900px !important; max-height: 900px !important;
                margin: 0 !important; overflow: hidden !important;
                break-inside: avoid !important; break-after: page !important; }
            .slide:last-of-type { break-after: auto !important; }
            .slide[data-skip="true"] { display: none !important; }
            .slide > .wrap { zoom: 1 !important; transform: none !important; opacity: 1 !important; }
            [data-a], .w, .w > span { opacity: 1 !important; transform: none !important;
                filter: none !important; }
        """)
        # Avoid a trailing page break when hidden appendix sections follow the last main slide.
        page.locator('.slide:not([data-skip="true"])').last.evaluate(
            "s => s.style.setProperty('break-after', 'auto', 'important')"
        )
        page.pdf(
            path=str(target),
            width="1600px",
            height="900px",
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
            tagged=True,
        )
        cover_image = None
        if not appendix:
            page.evaluate("window.scrollTo(0, 0)")
            cover_image = page.screenshot(type="png")
        browser.close()

    doc = fitz.open(target)
    assert len(doc) == len(titles), (len(doc), len(titles))
    for number, (pdf_page, title) in enumerate(zip(doc, titles), 1):
        assert abs(pdf_page.rect.width - 1200) < 1 and abs(pdf_page.rect.height - 675) < 1
        assert len(pdf_page.get_text().strip()) > 50, (number, title, "Unexpectedly empty page")
    print(f"Saved {target}")
    print(f"Verified {len(doc)} pages, 16:9 landscape, selectable text.")
    if cover_image:
        # Chromium's PDF compositing darkens the hero's CSS 3D/gradient layers.
        # Preserve the browser-rendered colours with a 2x cover image. Original
        # text, tags and link annotations remain underneath for search/navigation.
        doc[0].insert_image(doc[0].rect, stream=cover_image, overlay=True)
    doc.set_toc([[1, title, number] for number, title in enumerate(titles, 1)])
    doc.saveIncr()
    doc.close()
    return target, titles, slide_ids


def export_combined():
    main_path, main_titles, main_ids = export(False)
    appendix_path, appendix_titles, appendix_ids = export(True)
    target = ROOT / "submission" / "ParkFlow-Deck-With-Appendix.pdf"
    combined = fitz.open()
    source_links = []
    for source in [main_path, appendix_path]:
        with fitz.open(source) as part:
            start = len(combined)
            for index, source_page in enumerate(part):
                source_links.append((start + index, start, source_page.get_links()))
            combined.insert_pdf(part)
    offset = len(main_titles)
    combined.set_toc(
        [[1, "Main presentation", 1]]
        + [[2, title, number] for number, title in enumerate(main_titles, 1)]
        + [[1, "Appendix", offset + 1]]
        + [[2, title, offset + number] for number, title in enumerate(appendix_titles, 1)]
    )
    destinations = {slide_id: i for i, slide_id in enumerate(main_ids + appendix_ids)}
    # Rebuild links from the originals: merging can drop named destinations or
    # encode local HTML fragments as external file links.
    for page_index, start, links in source_links:
        pdf_page = combined[page_index]
        for existing in pdf_page.get_links():
            pdf_page.delete_link(existing)
        for link in links:
            uri = link.get("uri", link.get("file", ""))
            for _ in range(3):
                uri = unquote(uri)
            destination = link.get("nameddest") or urlsplit(uri).fragment
            if destination in destinations:
                pdf_page.insert_link({"kind": fitz.LINK_GOTO, "from": link["from"],
                                      "page": destinations[destination], "to": fitz.Point(0, 0)})
            elif link["kind"] == fitz.LINK_GOTO and link.get("page", -1) >= 0:
                pdf_page.insert_link({"kind": fitz.LINK_GOTO, "from": link["from"],
                                      "page": start + link["page"], "to": fitz.Point(0, 0)})
            elif uri.startswith(("https://", "http://", "mailto:")):
                pdf_page.insert_link({"kind": fitz.LINK_URI, "from": link["from"], "uri": uri})
    combined.set_metadata({
        "title": "ParkFlow | Pitch Deck and Appendix",
        "subject": "19 main slides followed by the complete supporting appendix",
    })
    combined.save(target, garbage=3, deflate=True)
    assert len(combined) == len(main_titles) + len(appendix_titles)
    print(f"Saved {target}")
    print(f"Verified {len(combined)} pages: {offset} main + {len(appendix_titles)} appendix.")
    combined.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--appendix", action="store_true")
    parser.add_argument("--with-appendix", action="store_true")
    args = parser.parse_args()
    if args.with_appendix:
        export_combined()
    else:
        export(args.appendix)

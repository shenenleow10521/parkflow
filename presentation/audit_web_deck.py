"""Render the continuous HTML presentation and check its main/appendix sequence."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / ".codex-preview" / "deck-continuous"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 900}, reduced_motion="reduce")
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    url = (ROOT / "site-vnext" / "index.html").as_uri()
    page.goto(url)
    page.wait_for_function("window.__pfReady === true")
    page.evaluate("document.fonts.ready")
    page.evaluate("""() => {
        document.querySelectorAll('.slide').forEach(s => s.classList.add('shown'));
        document.querySelectorAll('img').forEach(i => i.loading = 'eager');
    }""")
    page.wait_for_timeout(400)
    ids = page.locator('.slide:not([data-skip="true"])').evaluate_all("(ss) => ss.map(s => s.id)")
    assert len(ids) == 32, ids
    assert ids[1] == "team"
    assert "books" in ids and "driver" in ids and "ml-stack" in ids
    assert ids.index("ml-stack") + 1 == ids.index("accuracy")
    assert ids.index("prototype") < ids.index("ml-stack")
    assert ids.index("accuracy") + 1 == ids.index("result")
    assert ids.index("result") + 1 == ids.index("market")
    assert ids.index("market") + 1 == ids.index("costs")
    assert ids.index("money") + 1 == ids.index("investment-conditions")
    assert ids.index("appendix-retention") + 1 == ids.index("next-up")
    assert ids.index("next-up") + 1 == ids.index("pilot-plan")
    assert ids.index("close") + 1 == ids.index("thanks")
    assert ids.index("thanks") + 1 == ids.index("business")
    assert ids.index("business") + 1 == ids.index("appendix-partner-sensitivity")
    assert "stress-slide" in ids and "appendix-access-rules" in ids
    shots = []
    for number, slide_id in enumerate(ids, 1):
        slide = page.locator("#" + slide_id)
        slide.scroll_into_view_if_needed()
        page.evaluate("(id) => window.scrollTo(0, document.getElementById(id).offsetTop)", slide_id)
        page.wait_for_timeout(70)
        target = OUT / f"{number:02d}-{slide_id}.png"
        page.screenshot(path=str(target))
        shots.append(target)
    layout = page.evaluate("""() => [...document.querySelectorAll('.slide:not([data-skip="true"])')].map(s => {
        const r = s.getBoundingClientRect(), w = s.querySelector('.wrap').getBoundingClientRect();
        return {id:s.id, content:Math.round(w.height), available:Math.round(r.height -
          parseFloat(getComputedStyle(s).paddingTop) - parseFloat(getComputedStyle(s).paddingBottom)),
          horizontal:s.scrollWidth > s.clientWidth};
    })""")
    assert all(row["content"] <= row["available"] + 1 for row in layout), layout
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.evaluate("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)")
    for width, height in [(1280, 720), (1366, 768)]:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(100)
        failures = page.evaluate("""() => [...document.querySelectorAll('.slide:not([data-skip="true"])')].filter(s => {
            const r = s.getBoundingClientRect(), w = s.querySelector('.wrap').getBoundingClientRect();
            return w.height > r.height - parseFloat(getComputedStyle(s).paddingTop) -
                parseFloat(getComputedStyle(s).paddingBottom) + 1;
        }).map(s => s.id)""")
        assert not failures, (width, height, failures)
    thanks_index = ids.index("thanks")
    main = ids[:thanks_index + 1]
    appendix = ids[thanks_index + 1:]
    assert len(main) == 23, main
    assert len(appendix) == 9, appendix
    assert appendix[0] == "business"
    assert page.locator("#d-tot").inner_text() == "32"
    assert page.locator("#close-h").inner_text() == "Pilot Decision"
    assert page.locator("#thanks-h").inner_text() == "Thank You"
    assert "appendix=1" not in page.content()
    assert not errors, errors
    report = {"main": main, "appendix": appendix, "layout": layout, "errors": errors}
    print(json.dumps(report, indent=2))
    browser.close()

thumb_w, thumb_h = 400, 250
sheet = Image.new("RGB", (thumb_w * 4, thumb_h * math.ceil(len(shots) / 4)), "#dce1e8")
draw = ImageDraw.Draw(sheet)
for i, shot in enumerate(shots):
    x, y = i % 4 * thumb_w, i // 4 * thumb_h
    with Image.open(shot) as source:
        source.thumbnail((thumb_w, 225))
        sheet.paste(source, (x, y))
    draw.text((x + 8, y + 230), shot.stem, fill="#111827")
sheet.save(OUT / "contact.jpg", quality=92)

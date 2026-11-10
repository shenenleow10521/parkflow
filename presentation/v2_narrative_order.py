"""Apply the approved V2 narrative trim and business-slide order.

Run this as the final deck pass, after ``v2_redesign_slides.py``. The pass is
idempotent and preserves the generated HTML formatting.
"""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "site-consulting" / "index-v2.html"
REMOVE = ("context", "booking-sensitivity", "retention")
BUSINESS_ORDER = ("must-be-true", "capex-opex", "booking-return", "investment")


def section_pattern(slide_id):
    return re.compile(r'<section\b[^>]*\bid="' + re.escape(slide_id) + r'"[^>]*>.*?</section>', re.S)


def take(h, slide_id):
    match = section_pattern(slide_id).search(h)
    assert match, f"#{slide_id} not found"
    return h[:match.start()] + h[match.end():], match.group(0)


def main():
    h = HTML.read_text(encoding="utf-8")

    for slide_id in REMOVE:
        h = section_pattern(slide_id).sub("", h)

    business = []
    for slide_id in BUSINESS_ORDER:
        h, slide = take(h, slide_id)
        business.append(slide)
    pilot = section_pattern("pilot-design").search(h)
    assert pilot, "#pilot-design not found"
    h = h[:pilot.start()] + "".join(business) + h[pilot.start():]

    h, risk = take(h, "risk")
    risk = risk.replace('data-section="Implementation"', 'data-section="Appendix"', 1)
    risk = risk.replace('data-appendix="false"', 'data-appendix="true"', 1)
    thanks = section_pattern("thanks").search(h)
    assert thanks, "#thanks not found"
    h = h[:thanks.end()] + risk + h[thanks.end():]

    sections = re.findall(r'<section\b[^>]*\bclass="[^"]*\bslide\b[^"]*"[^>]*\bid="([^"]+)"|'
                          r'<section\b[^>]*\bid="([^"]+)"[^>]*\bclass="[^"]*\bslide\b[^"]*"', h)
    ids = [a or b for a, b in sections]
    total = len(ids)
    pages = iter(range(1, total + 1))
    h = re.sub(r'<span class="page">V2 · \d+ / \d+</span>',
               lambda _: f'<span class="page">V2 · {next(pages):02d} / {total}</span>', h)

    assert len(ids) == len(set(ids)) == 34
    assert ids[:4] == ["cover", "team", "executive", "problem"]
    assert ids[14:18] == list(BUSINESS_ORDER)
    assert ids[19:22] == ["roadmap", "horizons", "decision"]
    assert ids[22:24] == ["thanks", "risk"]
    assert not set(REMOVE) & set(ids)

    HTML.write_text(h, encoding="utf-8", newline="")
    print(f"ok  slides={total} main=23 appendix=11")


if __name__ == "__main__":
    main()

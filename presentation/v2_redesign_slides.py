"""Apply the 10 Nov 2026 V2 redesign and the KLGCC pilot switch to index-v2.html.

What it does (idempotent; reruns give the same file):
  * Slide 1  (#cover)        red cover: slanted KLGCC photo, red kicker, steps <- v2_redesign/cover.html + .css
  * Slide 2  (#team)         red team layout: five member cards     <- v2_redesign/team.html + .css
  * Slide 3  (#executive)    red executive-recommendation layout   <- v2_redesign/executive.html + .css
  * Slide 4  (#problem)      NEW problem-statement slide, inserted after #executive
                             <- v2_redesign/problem.html + .css; pages are renumbered
  * Slide 6  (#alternatives) red market-context comparison table   <- v2_redesign/alternatives.html + .css
  * Slide 7  (#service)      red "Introducing ParkFlow" Priority Zone layout <- v2_redesign/service.html + .css
  * Slide 10 (#admission)    red forecasting & admission control: timeline + capacity guard <- v2_redesign/admission.html + .css
  * Slide 25 (#horizons)     three-horizon area-curve roadmap      <- v2_redesign/horizons.html + .css
  * KL East exterior photo -> KLGCC Mall photo (assets/klgcc-mall-exterior.webp) on every slide
  * Pilot site KL East -> KLGCC in the deck text; KLGCC official parking page as site source
    (KL East + Elmina annual-report occupancy facts are kept: they describe those malls, not the pilot).

Run after build_consulting_v2.py and the other v2_*_slide.py patches, last of all:
    python presentation/v2_redesign_slides.py [path/to/index-v2.html]
Shared V1 files (deck.css, premium.css, index.html) are not touched.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTS = HERE / 'v2_redesign'
HTML = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[0] / 'site-consulting' / 'index-v2.html'
ASSET = HERE.parents[0] / 'site-consulting' / 'assets' / 'klgcc-mall-exterior.webp'

KLE = 'https://www.simedarbyproperty.com/malls/kleast-mall/'
KLG = 'https://www.simedarbyproperty.com/malls/klgcc-mall/'

# (old, new): applied only where `old` is still present, so reruns are no-ops.
TEXT = [
    # Cover
    ('KL East Mall is a proposed first pilot.', 'KLGCC Mall is a proposed first pilot.'),
    ('Property image: official KL East Mall website.',
     'Property image: KLGCC Mall exterior, supplied by Team Hexa; original source to be confirmed.'),
    # Slide 3 (#executive) source line
    ('KL East remains a pilot candidate.', 'KLGCC remains a pilot candidate.'),
    # Slide 4 (#context)
    ('<section aria-label="KL East Mall parking"', '<section aria-label="KLGCC Mall parking"'),
    ('<h2 class="slide-title">KL East Mall parking</h2>', '<h2 class="slide-title">KLGCC Mall parking</h2>'),
    ('<figcaption>KL East Mall · proposed lighthouse site</figcaption>',
     '<figcaption>KLGCC Mall · proposed lighthouse site</figcaption>'),
    ('<figcaption>KLGCC Mall · SDP mall, potential H2 site</figcaption>',
     '<figcaption>KLGCC Mall · proposed lighthouse site</figcaption>'),
    ('Cashless parking, LPR and online payment.', 'About 1,000 bays on LG and B1–B3; Touch ’n Go card payment.'),
    ('Existing mall LPR does not replace the two new zone cameras.',
     'Mall-wide LPR is not published; the zone still needs two new zone cameras.'),
    # Other slides that name the pilot site
    ('Not a surveyed or approved KL East floor plan.', 'Not a surveyed or approved KLGCC floor plan.'),
    ('does not validate KL East booking demand.', 'does not validate KLGCC booking demand.'),
    ('Nominate KL East sponsor and operator counterpart', 'Nominate KLGCC sponsor and operator counterpart'),
    ('Nominate a KL East sponsor and operator counterpart.', 'Nominate a KLGCC sponsor and operator counterpart.'),
    ('not KL East or booking requests', 'not KLGCC or booking requests'),
    # Appendix source entry for the site
    ('Current tariffs, valet comparator and mall LPR. New zone needs two additional cameras.',
     'Current tariffs, ~1,000 bays and Touch ’n Go card payment; mall LPR not published. New zone needs two additional cameras.'),
]

REGEX = [
    # Any remaining KL East exterior photo becomes the KLGCC photo.
    (r'<img alt="[^"]*" src="assets/kl-east-exterior\.jpg"/>',
     '<img alt="KLGCC Mall exterior" src="assets/klgcc-mall-exterior.webp"/>'),
    # Site-source links (cover/context S1, integration slide, appendix).
    (r'<a href="' + re.escape(KLE) + r'"([^>]*)>S1: KL East Mall official parking information</a>',
     '<a href="' + KLG + r'"\1>S1: KLGCC Mall official parking information</a>'),
    (r'<a href="' + re.escape(KLE) + r'"([^>]*)>KL East: existing LPR and payment</a>',
     '<a href="' + KLG + r'"\1>KLGCC Mall: official parking information</a>'),
]

STYLES = [  # (style id, css file) in insertion order
    ('horizons-v3-style', 'horizons.css'),
    ('executive-v3-style', 'executive.css'),
    ('alternatives-v3-style', 'alternatives.css'),
    ('problem-v3-style', 'problem.css'),
    ('team-v3-style', 'team.css'),
    ('service-v3-style', 'service.css'),
    ('cover-v3-style', 'cover.css'),
    ('admission-v3-style', 'admission.css'),
]
# V2-only crop so the KLGCC sign is not cut off on the Thank-you slide (premium.css is shared with V1).
PHOTO_CSS = '<style id="v2-photo-style">#thanks .thank-composition img { object-position:51% center; }</style>'


def part(name):
    return (PARTS / name).read_text(encoding='utf-8')


def section_span(h, sid):
    m = re.search(r'<section[^>]*id="' + sid + r'".*?</section>', h, re.S)
    assert m, f'#{sid} not found'
    return m.start(), m.end()


def splice(h, sid, start_marker, end_marker, new, include_end_div=False):
    """Replace the part of section #sid from start_marker up to (or through) end_marker."""
    s, e = section_span(h, sid)
    sec = h[s:e]
    i = sec.index(start_marker)
    j = sec.index(end_marker, i)
    if include_end_div:
        j = sec.index('</div>', j) + len('</div>')
    return h[:s] + sec[:i] + new + sec[j:] + h[e:]


def main():
    assert ASSET.exists(), f'missing {ASSET}'
    h = HTML.read_text(encoding='utf-8')

    h = splice(h, 'cover', '<div class="content">', '<div class="source">', part('cover.html'))
    h = splice(h, 'team', '<div class="frame">', '<div class="source">', part('team.html'))
    h = splice(h, 'executive', '<div class="frame">', '<div class="source">', part('executive.html'))
    h = splice(h, 'alternatives', '<div class="frame">', '<div class="source">', part('alternatives.html'), include_end_div=True)
    h = splice(h, 'service', '<div class="frame">', '<div class="source">', part('service.html'), include_end_div=True)
    h = splice(h, 'admission', '<div class="frame">', '<div class="source">', part('admission.html'))
    h = splice(h, 'horizons', '<div class="content">', '<div class="source">', part('horizons.html'))

    # New problem-statement slide right after #executive (Overview section, same footer pattern).
    h = re.sub(r'<section[^>]*id="problem".*?</section>', '', h, flags=re.S)
    s, e = section_span(h, 'executive')
    footer = re.search(r'<footer class="footer">.*?</footer>', h[s:e], re.S).group(0)
    h = h[:e] + part('problem.html').replace('{footer}', footer) + h[e:]
    pages = re.findall(r'<span class="page">V2 · \d+ / \d+</span>', h)
    counter = iter(range(1, len(pages) + 1))
    h = re.sub(r'<span class="page">V2 · \d+ / \d+</span>',
               lambda m: f'<span class="page">V2 · {next(counter):02d} / {len(pages)}</span>', h)

    for old, new in TEXT:
        h = h.replace(old, new)
    for pattern, repl in REGEX:
        h = re.sub(pattern, repl, h)

    for sid, _ in STYLES:
        h = re.sub(r'<style id="' + sid + r'">.*?</style>', '', h, flags=re.S)
    h = h.replace(PHOTO_CSS, '')
    blocks = ''.join(f'<style id="{sid}">{part(css)}</style>' for sid, css in STYLES) + PHOTO_CSS
    assert h.count('</head>') == 1
    h = h.replace('</head>', blocks + '</head>', 1)

    # End-state checks.
    assert 'kl-east-exterior' not in h
    assert KLE not in h, 'a KL East site-source link remains'
    for must in ['KLGCC Mall is a proposed first pilot.', 'KLGCC Mall parking', 'class="ex-steps"', 'class="mc-table"',
                 'class="hz-lead"', 'Potential sites: Elmina + KL East', 'id="problem"', 'class="ps-stats"', 'class="tm-grid"', 'class="sv-main"', 'class="cv-copy"', 'class="ad-guard"']:
        assert must in h, must

    HTML.write_text(h, encoding='utf-8', newline='')
    print(f'ok  {HTML}')


if __name__ == '__main__':
    main()

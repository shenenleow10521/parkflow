"""Phase 2: red theme + consulting header for every slide of site-consulting/index.html.

Run after redesign_red.py (the 4 hand-built sample slides). Idempotent: reruns rebuild the
inlined stylesheet and skip slides that already carry the redx class.
"""
import re, sys, os

PATH = sys.argv[1]
DIR = os.path.dirname(os.path.abspath(PATH))
h = open(PATH, encoding="utf-8").read()

# ---------- 1. Recoloured copy of premium.css, inlined (premium.css itself stays untouched) ----------
NAVY_BG = "#7F1D1D"
COLOURS = {
    "#102a43": "#1F2937", "#245bd8": "#B91C1C", "#53647a": "#6B7280", "#5f748d": "#4B5563",
    "#8795a7": "#9CA3AF", "#f2f5f9": "#F3F4F6", "#e1e6eb": "#E5E7EB", "#e6eaf0": "#E5E7EB",
    "#d5dde7": "#E5E7EB", "#dbe4ef": "#E5E7EB", "#c5ced9": "#D1D5DB", "#bbc7d6": "#D1D5DB",
    "#b9c9dc": "#D1D5DB", "#b6c5d8": "#D1D5DB", "#afc0d8": "#D1D5DB",
    # blue tints -> red tints
    "#edf3fc": "#FEF2F2", "#eef3fa": "#FEF2F2", "#f1f5fa": "#FEF2F2", "#f0f5fc": "#FEF2F2",
    "#eaf0fc": "#FEF2F2", "#eaf0fa": "#FEF2F2", "#eaf0f7": "#FEF2F2", "#dfe9f7": "#FEE2E2",
    "#d2deee": "#FEE2E2", "#c4d4e8": "#FECACA", "#b2c8e6": "#FCA5A5", "#afc5e2": "#FCA5A5",
    "#9bb5de": "#F87171", "#a8bddb": "#FCA5A5",
    # remaining blue-greys -> neutral greys
    "#1f4fa3": "#1F2937", "#5b6c80": "#4B5563", "#8196af": "#9CA3AF", "#a9b7ca": "#D1D5DB",
}


def recolour(css):
    css = re.sub(r"(background(?:-color)?:\s*)(#102a43|var\(--navy\))", r"\g<1>" + NAVY_BG, css, flags=re.I)
    for old, new in COLOURS.items():
        css = re.sub(re.escape(old), new, css, flags=re.I)
    return css


premium = recolour(open(os.path.join(DIR, "premium.css"), encoding="utf-8").read())
premium += """
:root { --navy:#1F2937; --blue:#B91C1C; --red:#B91C1C; --ink:#1F2937; --muted:#6B7280; --rule:#E5E7EB; --panel:#F3F4F6; }
.frame [style*="background:var(--navy)"], .decision-strip { border-color:#B91C1C; }
/* Keep the ParkFlow wordmark in its own brand colours */
.wordmark { color:#102a43; } .wordmark>span, .wordmark svg { color:#245bd8; }
.controls button, #reading, #previous, #next { color:#B91C1C; border-color:#E5E7EB; }
"""
premium += """
.decision-strip { border-top:0; border-left:4px solid #B91C1C; background:#FEF2F2; }
.decision-strip strong { color:#B91C1C; }
#forecast .legend i:not(.grey) { background:#B91C1C; }
"""
# deck.css also hardcodes navy; inline a recoloured copy ahead of the premium block
COLOURS.update({"#17365d": "#1F2937", "#e6ebf2": "#FEF2F2", "#c00024": "#B91C1C"})
deck = recolour(open(os.path.join(DIR, "deck.css"), encoding="utf-8").read())
COLOURS.pop("#17365d"); COLOURS.pop("#e6ebf2"); COLOURS.pop("#c00024")
block = '<style id="deck-red">\n' + deck + '\n</style><style id="premium-red">\n' + premium + "\n</style>"
if 'id="premium-red"' in h:
    h = re.sub(r'(<style id="deck-red">.*?</style>)?<style id="premium-red">.*?</style>', lambda m: block, h, count=1, flags=re.S)
else:
    h = h.replace('<link rel="stylesheet" href="deck.css">', "", 1)
    h = h.replace('<link rel="stylesheet" href="premium.css">', block, 1)

# Inline SVG chart colours
for old, new in {"#245bd8": "#B91C1C", "#102a43": "#1F2937", "#8795a7": "#9CA3AF", "#53647a": "#6B7280"}.items():
    h = re.sub(r'(fill|stroke)="%s"' % old, r'\1="%s"' % new, h, flags=re.I)


def edit_section(sid, fn):
    global h
    m = re.search(r'<section class="slide[^"]*" id="%s"[^>]*>.*?</section>' % sid, h, re.S)
    h = h.replace(m.group(0), fn(m.group(0)), 1)


# Forecast chart: the ensemble is the bar that proves the point, so it goes red
edit_section("forecast", lambda s: s.replace('fill="#1F2937"', 'fill="#B91C1C"'))
# Heat-map legend wording follows the new colours
h = h.replace("blue-grey = 12 or fewer", "light red = 12 or fewer")
# Admission: the strip heading repeats the new action title
h = re.sub(r'<h3[^>]*>Eight verified free bays, accounted for</h3>', "", h)

# ---------- 2. Consulting header on every content slide ----------
TITLES = {
    "team": "Five complementary roles built the prototype and the investment case",
    "context": "KL East already has LPR, so ParkFlow starts by integrating and reusing it",
    "alternatives": "Member parking already exists; ParkFlow must win on its fulfilment promise",
    "service": "One shared zone by the lifts: members reserve access, not a specific bay",
    "member": "Members book, arrive and get help within one journey",
    "operator": "Operators get one record of entry, occupancy, commitments and exceptions",
    "admission": "With 8 verified free bays, the gate can safely accept only 2 more bookings",
    "integration": "KL East’s LPR is in place; three integration gaps need a site audit first",
    "forecast": "The forecast ensemble cuts 60-minute error by 61% versus last week’s pattern",
    "member-value": "Frequent visitors report 68% bigger baskets; the pilot must prove parking causes extra visits",
    "investment": "RM92k is a planning subtotal; installed scope and support must be priced before funding",
    "booking-return": "Booking fees leave RM7.8k a year before central support, tax and capital recovery",
    "booking-sensitivity": "RM12k of annual support turns the RM7.8k base contribution negative",
    "recovery": "Recovering RM81.5k capital in five years needs RM8.5k more net benefit a year",
    "retention": "Closing the RM8.5k gap needs 7–29 extra weekly visits, 13 in the base case",
    "commercial": "One SDP sponsor owns the pilot, with three partners accountable for decision evidence",
    "pilot-design": "An eight-week trial, with the baseline set before the first paid booking",
    "scorecard": "Five metrics, each with an agreed rule and owner, decide whether to scale, adapt or stop",
    "risk": "When the system state is uncertain, pause new bookings and recover through a logged process",
    "horizons": "Scale in three gated horizons: KL East, then SDP’s malls, then external contracts",
}

total = len(re.findall(r'<section class="slide', h))


def tracker(num, label):
    return (f'<div class="rx-tracker"><span class="sec">{num:02d} | {label}</span>'
            f'<span class="proj">ParkFlow · KL East Mall</span></div>')


sections = list(re.finditer(r'<section class="slide[^"]*"[^>]*>.*?</section>', h, re.S))
out, last = [], 0
for idx, m in enumerate(sections, 1):
    sec = m.group(0)
    open_tag = sec.split(">", 1)[0] + ">"
    sid = re.search(r'id="([^"]+)"', open_tag).group(1)
    section = re.search(r'data-section="([^"]+)"', open_tag).group(1)
    cls = re.search(r'class="([^"]+)"', open_tag).group(1)
    new = sec
    if "redx" not in cls.split() and "premium-cover" not in cls and "premium-thank" not in cls:
        title_m = re.search(r'<h2 class="slide-title">(.*?)</h2>', sec, re.S)
        take_m = re.search(r'<p class="takeaway">(.*?)</p>', sec, re.S)
        old_title = re.sub("<[^>]+>", "", title_m.group(1)).strip()
        if sid.startswith("a-"):
            topic = old_title.split("/", 1)[1].strip()
            label = "Appendix · " + topic[0].upper() + topic[1:]
            title = re.sub("<[^>]+>", "", take_m.group(1)).strip().rstrip(".")
        else:
            label = section
            title = TITLES[sid]
        head = tracker(idx, label) + f'<h2 class="slide-title">{title}</h2><div class="rx-rule"></div>'
        new = sec.replace(title_m.group(0), head, 1)
        if take_m:
            new = new.replace(take_m.group(0), "", 1)
        new_open = open_tag.replace('class="slide ', 'class="slide redx ', 1)
        new_open = re.sub(r'aria-label="[^"]*"', 'aria-label="%s"' % title.replace('"', "&quot;"), new_open)
        new = new.replace(open_tag, new_open, 1)
    out.append(h[last:m.start()])
    out.append(new)
    last = m.end()
out.append(h[last:])
h = "".join(out)

open(PATH, "w", encoding="utf-8", newline="").write(h)
print("ok", total, "slides")

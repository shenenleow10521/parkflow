"""Insert a CAPEX | total-cost pie | OPEX infographic slide after V2 slide 16 (#investment).

Every figure comes from consulting_v2_finance.py. Idempotent: reruns replace the slide and renumber footers.
Run after v2_cost_breakeven_slide.py:  python presentation/v2_capex_opex_slide.py
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consulting_v2_finance as fm  # noqa: E402

HTML = Path(__file__).resolve().parents[1] / 'site-consulting' / 'index-v2.html'
ref = fm.economics()

CAPEX, FIXED, FIRST_YEAR = fm.UPFRONT, fm.ANNUAL_RUNNING, fm.FIRST_YEAR
OPERATOR, CARD = ref['operator'], ref['processing']
OPEX_YEAR = FIXED + OPERATOR + CARD
assert (CAPEX, FIRST_YEAR) == (79_985, 90_485)

NAVY, RED = '#102a43', '#e3261c'
CAPEX_PARTS = [  # name, value, colour (navy family, darkest = largest)
    ('Software integration', fm.INTEGRATION_ALLOWANCE, '#102a43'),
    ('Power, network &amp; works', fm.CABLING_ALLOWANCE, '#245bd8'),
    ('2 new zone LPR cameras', fm.LPR, '#5f8de0'),
    ('Coverage cameras', fm.CAMERA_ALLOWANCE, '#9bb5de'),
    ('Compact LED sign', fm.LED, '#c9d7ee'),
]
OPEX_PARTS = [
    ('Zone running allowance<small>fixed · hosting, messaging, upkeep</small>', FIXED, '#b91c1c'),
    (f'Operator share<small>variable · {fm.OPERATOR_SHARE:.0%} of booking fees</small>', OPERATOR, '#ef6b5f'),
    ('Card processing<small>variable · 1.8% + SST on the fee</small>', CARD, '#f8b4b0'),
]


def rm(v):
    return f'RM{v / 1000:.1f}k'


def donut(parts, total, size, width, centre, label_min=4.5, text_fill=('#fff', '#1a1a1a')):
    """SVG donut: one stroked circle per slice, % label at each slice's mid-angle."""
    c = size / 2
    r = c - width / 2 - 2
    circ = 2 * math.pi * r
    out, start = [], 0.0
    for _, v, colour in parts:
        frac = v / total
        out.append(f'<circle cx="{c}" cy="{c}" r="{r:.1f}" fill="none" stroke="{colour}" stroke-width="{width}" '
                   f'stroke-dasharray="{frac * circ:.2f} {circ:.2f}" stroke-dashoffset="{-start * circ:.2f}" '
                   f'transform="rotate(-90 {c} {c})"/>')
        if frac * 100 >= label_min:
            a = math.radians(-90 + 360 * (start + frac / 2))
            dark = colour in ('#9bb5de', '#c9d7ee', '#f8b4b0')
            out.append(f'<text x="{c + r * math.cos(a):.1f}" y="{c + r * math.sin(a) + 5:.1f}" font-size="{size * .068:.0f}" '
                       f'font-weight="800" fill="{text_fill[1] if dark else text_fill[0]}" text-anchor="middle">{frac * 100:.0f}%</text>')
        start += frac
    return (f'<svg viewBox="0 0 {size} {size}" role="img"><g font-family="Public Sans,Arial,sans-serif">'
            + ''.join(out) + f'<circle cx="{c}" cy="{c}" r="{r - width / 2 - 1:.1f}" fill="#fff"/>' + centre + '</g></svg>')


def legend(parts, total):
    return '<div class="co-legend">' + ''.join(
        f'<div><i style="background:{col}"></i><span class="n">{name}</span>'
        f'<span class="v">{rm(v)}<small>{v / total * 100:.0f}%</small></span></div>'
        for name, v, col in parts) + '</div>'


def centre_text(top, bottom, c):
    return (f'<text x="{c}" y="{c + 2}" font-size="19" font-weight="800" fill="#1a1a1a" text-anchor="middle">{top}</text>'
            f'<text x="{c}" y="{c + 24}" font-size="14" font-weight="700" fill="#4b4f56" text-anchor="middle">{bottom}</text>')


ICON_CAPEX = ('<svg viewBox="0 0 64 64" aria-hidden="true" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round">'
              '<path d="M10 58V10l8-6 8 6v48M6 14h40l-6 8M18 4v54M30 14v12"/><rect x="34" y="34" width="22" height="24"/>'
              '<path d="M40 40h4M48 40h2M40 47h4M48 47h2M40 54h4M48 54h2M4 58h56"/></svg>')
ICON_OPEX = ('<svg viewBox="0 0 64 64" aria-hidden="true" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round">'
             '<path d="M27 4h10l2 8 6 3 7-4 7 7-4 7 3 6 8 2v10l-8 2-3 6 4 7-7 7-7-4-6 3-2 8H27l-2-8-6-3-7 4-7-7 4-7-3-6-8-2V27l8-2 3-6-4-7 7-7 7 4 6-3z" transform="translate(0 0) scale(.94) translate(2 2)"/>'
             '<circle cx="32" cy="32" r="10"/></svg>')
COINS = ('<g fill="#fff" stroke="#102a43" stroke-width="2.4">'
         '<ellipse cx="{x0}" cy="{y3}" rx="15" ry="5"/><path d="M{l0} {y3}v-7a15 5 0 0 1 30 0v7"/><ellipse cx="{x0}" cy="{y2}" rx="15" ry="5"/>'
         '<path d="M{l0} {y2}v-7a15 5 0 0 1 30 0v7"/><ellipse cx="{x0}" cy="{y1}" rx="15" ry="5"/>'
         '<ellipse cx="{x1}" cy="{y3}" rx="15" ry="5"/><path d="M{l1} {y3}v-7a15 5 0 0 1 30 0v7"/><ellipse cx="{x1}" cy="{y2}" rx="15" ry="5"/>'
         '<path d="M{l1} {y2}v-7a15 5 0 0 1 30 0v7"/><ellipse cx="{x1}" cy="{y1}" rx="15" ry="5"/>'
         '<path d="M{l1} {y1}v-7a15 5 0 0 1 30 0v7"/><ellipse cx="{x1}" cy="{y0}" rx="15" ry="5"/></g>')

# ---------- Centre pie ----------
P = 300
pc = P / 2
pr = pc - 4
capex_frac = CAPEX / FIRST_YEAR
ang = 2 * math.pi * (1 - capex_frac)  # OPEX wedge drawn clockwise from the top
ex, ey = pc + pr * math.sin(ang), pc - pr * math.cos(ang)
pie = (f'<svg viewBox="0 0 {P} {P}" role="img" aria-label="First-year cost RM{FIRST_YEAR:,}: CAPEX {capex_frac:.0%}, fixed OPEX {1 - capex_frac:.0%}">'
       '<g font-family="Public Sans,Arial,sans-serif" text-anchor="middle">'
       f'<circle cx="{pc}" cy="{pc}" r="{pr}" fill="{NAVY}"/>'
       f'<path d="M{pc} {pc}L{pc} {pc - pr}A{pr} {pr} 0 0 1 {ex:.1f} {ey:.1f}Z" fill="{RED}"/>'
       f'<circle cx="{pc}" cy="{pc}" r="{pr}" fill="none" stroke="#fff" stroke-width="4"/>'
       f'<line x1="{pc}" y1="{pc}" x2="{pc}" y2="{pc - pr}" stroke="#fff" stroke-width="3"/>'
       f'<line x1="{pc}" y1="{pc}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#fff" stroke-width="3"/>'
       f'<circle cx="{pc}" cy="{pc}" r="46" fill="#fff"/>'
       + COINS.format(x0=pc - 12, x1=pc + 12, l0=pc - 27, l1=pc - 3, y0=pc - 18, y1=pc - 6, y2=pc + 6, y3=pc + 18)
       + f'<text x="{pc - 78}" y="{pc + 60}" font-size="34" font-weight="800" fill="#fff">{capex_frac * 100:.0f}%</text>'
       f'<text x="{pc - 78}" y="{pc + 84}" font-size="16" font-weight="700" fill="#fff">CAPEX</text>'
       f'<text x="{pc + 34}" y="{pc - 94}" font-size="22" font-weight="800" fill="#fff">{(1 - capex_frac) * 100:.0f}%</text>'
       '</g></svg>')

capex_donut = donut(CAPEX_PARTS, CAPEX, 210, 46, centre_text(rm(CAPEX), 'CAPEX', 105))
opex_donut = donut(OPEX_PARTS, OPEX_YEAR, 210, 46, centre_text(rm(OPEX_YEAR), 'OPEX / yr', 105))

content = f'''<div class="co-grid">
<div class="co-panel capex">
 <header>{ICON_CAPEX}<div><h3>CAPEX</h3><p>Capital expenditure</p><small>One-time, upfront investment</small></div></header>
 <div class="co-total"><span>Total CAPEX</span><b>RM{CAPEX:,}</b></div>
 <div class="co-body">{capex_donut}{legend(CAPEX_PARTS, CAPEX)}</div>
 <div class="co-note"><b>Quote needed:</b> gates/arms, safety loops, intercom, edge controller</div>
</div>
<div class="co-hub">
 <h3>Total cost · first year</h3><div class="co-pill">RM{FIRST_YEAR:,}<span>+</span></div>
 {pie}
 <div class="co-key"><div><i style="background:{NAVY}"></i><b>CAPEX</b><span>{capex_frac * 100:.0f}%</span><span>{rm(CAPEX)}</span></div>
 <div><i style="background:{RED}"></i><b>Fixed OPEX</b><span>{(1 - capex_frac) * 100:.0f}%</span><span>{rm(FIXED)}</span></div></div>
</div>
<div class="co-panel opex">
 <header>{ICON_OPEX}<div><h3>OPEX</h3><p>Operating expenditure</p><small>Recurring, every year</small></div></header>
 <div class="co-total"><span>Total OPEX (annual, reference volume)</span><b>RM{OPEX_YEAR:,.0f}</b></div>
 <div class="co-body">{opex_donut}{legend(OPEX_PARTS, OPEX_YEAR)}</div>
 <div class="co-note"><b>Not yet priced:</b> central support, refunds &amp; incidents, equipment servicing</div>
</div>
</div>
<div class="co-sowhat"><span>So what</span><p>Software integration is <b>{fm.INTEGRATION_ALLOWANCE / CAPEX * 100:.0f}% of CAPEX</b>: its quote is the biggest cost risk. Only the <b>{rm(FIXED)}</b> running allowance is fixed; the other {rm(OPERATOR + CARD)} of OPEX moves with bookings.</p></div>'''

CSS = '''<style id="capex-opex-style">
#capex-opex .content { display:flex; flex-direction:column; gap:16px; }
#capex-opex .co-grid { flex:1; min-height:0; display:grid; grid-template-columns:1fr 360px 1fr; gap:26px; }
#capex-opex .co-panel { display:flex; flex-direction:column; border:2px solid #102a43; border-radius:14px; overflow:hidden; background:#fff; }
#capex-opex .co-panel.opex { border-color:#b91c1c; }
#capex-opex .co-panel header { display:flex; align-items:center; gap:18px; padding:14px 22px; background:#102a43; color:#fff; }
#capex-opex .co-panel.opex header { background:#b91c1c; }
#capex-opex .co-panel header svg { width:56px; height:56px; flex:none; padding-right:16px; border-right:2px solid rgba(255,255,255,.5); box-sizing:content-box; }
#capex-opex .co-panel header h3 { font-size:36px; font-weight:800; line-height:1; letter-spacing:-.01em; margin:0; }
#capex-opex .co-panel header p { font-size:17px; margin:4px 0 0; }
#capex-opex .co-panel header small { font-size:14px; opacity:.85; }
#capex-opex .co-total { margin:14px 22px 6px; padding:8px 0; border-radius:10px; background:#e8eef8; text-align:center; }
#capex-opex .opex .co-total { background:#fde8e6; }
#capex-opex .co-total span { display:block; font-size:15px; font-weight:700; color:#102a43; }
#capex-opex .opex .co-total span { color:#7f1d1d; }
#capex-opex .co-total b { display:block; font-size:36px; font-weight:800; line-height:1.1; letter-spacing:-.02em; color:#102a43; }
#capex-opex .opex .co-total b { color:#7f1d1d; }
#capex-opex .co-body { flex:1; display:grid; grid-template-columns:184px 1fr; gap:14px; align-items:center; padding:0 22px; }
#capex-opex .co-body > svg { width:184px; height:184px; }
#capex-opex .co-legend > div { display:grid; grid-template-columns:14px 1fr auto; gap:9px; align-items:center; padding:6px 0; border-bottom:1px solid #e5e7eb; font-size:14px; }
#capex-opex .co-legend i { width:14px; height:14px; border-radius:2px; }
#capex-opex .co-legend .n { font-weight:600; line-height:1.15; color:#1a1a1a; }
#capex-opex .co-legend .n small { display:block; font-size:11px; font-weight:400; color:#6b7280; }
#capex-opex .co-legend .v { text-align:right; font-weight:800; font-variant-numeric:tabular-nums; white-space:nowrap; }
#capex-opex .co-legend .v small { margin-left:6px; font-size:12px; font-weight:600; color:#6b7280; }
#capex-opex .co-note { margin:8px 22px 14px; padding:7px 10px; border:1.5px dashed #9a9ea5; font-size:12.5px; color:#4b4f56; }
#capex-opex .co-note b { color:#1a1a1a; }
#capex-opex .co-hub { display:flex; flex-direction:column; align-items:center; text-align:center; }
#capex-opex .co-hub h3 { font-size:28px; font-weight:800; color:#102a43; margin:0; letter-spacing:-.01em; }
#capex-opex .co-pill { margin-top:8px; padding:6px 28px; border-radius:999px; background:#102a43; color:#fff; font-size:38px; font-weight:800; letter-spacing:-.02em; line-height:1.15; }
#capex-opex .co-pill span { font-size:24px; margin-left:4px; color:#fca5a5; }
#capex-opex .co-hub > svg { width:290px; height:290px; margin:12px 0 10px; }
#capex-opex .co-key { width:100%; border:1.5px solid #d5dde7; border-radius:12px; padding:4px 16px; }
#capex-opex .co-key div { display:grid; grid-template-columns:16px 1fr 46px 70px; gap:10px; align-items:center; padding:7px 0; font-size:16px; text-align:left; }
#capex-opex .co-key div + div { border-top:1px solid #e5e7eb; }
#capex-opex .co-key i { width:16px; height:16px; border-radius:3px; }
#capex-opex .co-key span { text-align:right; font-weight:700; font-variant-numeric:tabular-nums; }
#capex-opex .co-sowhat { flex:none; display:flex; align-items:stretch; background:#1a1a1a; color:#fff; min-height:52px; }
#capex-opex .co-sowhat span { display:flex; align-items:center; padding:0 22px; background:#e3261c; font-size:13px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
#capex-opex .co-sowhat p { display:block; align-self:center; padding:0 22px; font-size:16.5px; line-height:1.35; margin:0; }
#capex-opex .co-sowhat b { color:#fca5a5; }
</style>'''

SRC = ('Sources: <a href="../presentation/consulting_v2_finance.py">V2 calculation</a>; '
       '<a href="financial-sources.md">Sources, scope and unresolved costs</a>. One reference zone. First-year cost = CAPEX '
       f'RM{CAPEX:,} + fixed running RM{FIXED:,}. Variable OPEX at reference volume (30 peak / 7.5 weekday bookings a day) is deducted '
       'from booking fees and is not in the total-cost pie. Allowances are unquoted; listed prices exclude tax. Excludes gates/controller, '
       'central support, project taxes and contingency.')

h = HTML.read_text(encoding='utf-8')
h = re.sub(r'<style id="capex-opex-style">.*?</style>', '', h, flags=re.S)
h = h.replace('</head>', CSS + '</head>', 1)
h = re.sub(r'<section[^>]*id="capex-opex".*?</section>', '', h, flags=re.S)

inv = re.search(r'<section[^>]*id="investment".*?</section>', h, re.S).group(0)
footer = re.search(r'<footer class="footer">.*?</footer>', inv, re.S).group(0)
new = ('<section aria-label="CAPEX and OPEX per reference zone" class="slide" data-appendix="false" '
       'data-financial-model="v2-2026-11-09" data-section="Business" id="capex-opex"><div class="frame">'
       '<h2 class="slide-title">CAPEX and OPEX per reference zone</h2>'
       f'<div class="content">{content}</div><div class="source">{SRC}</div>{footer}</div></section>')
h = h.replace(inv, inv + new, 1)

# Renumber every footer page label for the new slide count
pages = re.findall(r'<span class="page">V2 · \d+ / \d+</span>', h)
total = len(pages)
counter = iter(range(1, total + 1))
h = re.sub(r'<span class="page">V2 · \d+ / \d+</span>',
           lambda m: f'<span class="page">V2 · {next(counter):02d} / {total}</span>', h)

HTML.write_text(h, encoding='utf-8', newline='')
print(f'ok  capex={CAPEX:,} fixed={FIXED:,} first_year={FIRST_YEAR:,} operator={OPERATOR:,.2f} card={CARD:,.2f} '
      f'opex_year={OPEX_YEAR:,.2f} capex_share={capex_frac:.1%} slides={total}')

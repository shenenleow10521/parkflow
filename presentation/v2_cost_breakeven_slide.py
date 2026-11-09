"""Replace V2 slide 16 (#investment) with a cost waterfall, cost sheet and break-even scale.

All figures come from consulting_v2_finance.py, so the slide reconciles with the V2 model.
Run after build_consulting_v2.py:  python presentation/v2_cost_breakeven_slide.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consulting_v2_finance as fm  # noqa: E402

HTML = Path(__file__).resolve().parents[1] / 'site-consulting' / 'index-v2.html'

ref = fm.economics()
net_per_booking = ref['net'] / ref['bookings']
per_day = lambda yearly: yearly / 365
be_running = per_day(fm.required_bookings())
be_5y = per_day(fm.required_bookings(5))
be_3y = per_day(fm.required_bookings(3))
ref_day = per_day(ref['bookings'])
assert round(fm.UPFRONT) == 79_985 and round(fm.FIRST_YEAR) == 90_485

# ---------- Waterfall (style: grey steps, one red driver, red share circles) ----------
STEPS = [  # label lines, value, colour, show share of upfront
    (('2 new LPR', 'cameras'), fm.LPR, '#4b4f56', True),
    (('LED', 'sign'), fm.LED, '#4b4f56', True),
    (('Coverage', 'cameras'), fm.CAMERA_ALLOWANCE, '#4b4f56', True),
    (('Power, network', '& works'), fm.CABLING_ALLOWANCE, '#4b4f56', True),
    (('Software', 'integration'), fm.INTEGRATION_ALLOWANCE, '#e3261c', True),
]
W, H, BASE, TOP_VAL_Y = 1440, 476, 414, 92
scale = (BASE - TOP_VAL_Y) / fm.FIRST_YEAR
slot, bar_w, x0 = 172, 104, 60


def k(v):
    return f'{v / 1000:.1f}'


def text(x, y, s, size=17, weight=400, fill='#1a1a1a', anchor='middle'):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}">{s}</text>')


parts, running, prev_top = [], 0, None


def bar(i, lo, hi, colour, label, circle=None):
    global prev_top
    x = x0 + i * slot
    y_top, y_bot = BASE - hi * scale, BASE - lo * scale
    out = [f'<rect x="{x}" y="{y_top:.1f}" width="{bar_w}" height="{max(y_bot - y_top, 2):.1f}" fill="{colour}"/>']
    if prev_top is not None:  # dashed connector from the previous bar's running level
        out.append(f'<line x1="{x - slot + bar_w}" y1="{prev_top:.1f}" x2="{x}" y2="{prev_top:.1f}" '
                   'stroke="#9a9ea5" stroke-width="1.5" stroke-dasharray="5 4"/>')
    cx = x + bar_w / 2
    out.append(text(cx, y_top - 11, k(hi - lo), 24, 700))
    if circle is not None:
        out.append(f'<circle cx="{cx}" cy="{y_top - 64}" r="30" fill="#e3261c"/>')
        out.append(text(cx, y_top - 57, f'{circle}%', 19, 800, '#fff'))
    for j, line in enumerate(label):
        out.append(text(cx, BASE + 28 + j * 22, line, 18, 400, '#3b3f45'))
    prev_top = y_top
    return out


shares = [round(v / fm.UPFRONT * 100) for _, v, _, _ in STEPS]
assert sum(shares) == 100
for i, (label, v, colour, show) in enumerate(STEPS):
    parts += bar(i, running, running + v, colour, label, shares[i])
    running += v
parts += bar(5, 0, fm.UPFRONT, '#9a9ea5', ('Upfront', 'capital'))
parts += bar(6, fm.UPFRONT, fm.FIRST_YEAR, '#7b8088', ('Year 1', 'running'))
parts += bar(7, 0, fm.FIRST_YEAR, '#c9ccd1', ('First-year', 'priced total'))
waterfall = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Waterfall of reference zone cost: '
             f'upfront capital RM{fm.UPFRONT:,} plus Year 1 running RM{fm.ANNUAL_RUNNING:,} gives RM{fm.FIRST_YEAR:,}.">'
             '<g font-family="Public Sans,Arial,sans-serif">'
             f'<line x1="20" y1="{BASE}" x2="{W - 10}" y2="{BASE}" stroke="#1a1a1a" stroke-width="2"/>'
             + ''.join(parts) + '</g></svg>')

# ---------- Break-even scale (paid bookings per day) ----------
MAX_DAY = 30
pos = lambda d: f'{d / MAX_DAY * 100:.2f}%'
markers = [
    (be_running, 'Operating break-even', f'covers RM{fm.ANNUAL_RUNNING / 1000:.1f}k running a year', 'be'),
    (ref_day, 'Reference volume', f'RM{ref["contribution"] / 1000:.1f}k a year · {ref["payback"]:.1f}-year payback', 'ref'),
    (be_5y, '5-year payback', 'upfront capital back', ''),
    (be_3y, '3-year payback', 'upfront capital back', 'end'),
]
marker_html = ''.join(
    f'<div class="cb-mark {cls}" style="left:{pos(d)}"><b>{d:.1f}</b><span>{t}</span><small>{s}</small></div>'
    for d, t, s, cls in markers)
ticks = ''.join(f'<span style="left:{pos(t)}">{t}</span>' for t in range(0, MAX_DAY + 1, 5))

content = f'''<div class="cb-grid">
<div class="cb-chart"><div class="cb-label">Upfront capital build-up <em>RM thousands · circles = share of upfront capital</em></div>{waterfall}</div>
</div>
<div class="cb-be">
<div class="cb-be-kpi"><span class="cb-label">Break-even</span><strong>{be_running:.1f}</strong><p>paid bookings a day cover the running cost, at ≈RM{net_per_booking:.2f} net per booking</p></div>
<div class="cb-be-scale"><div class="cb-track"><div class="cb-loss" style="width:{pos(be_running)}"></div>{marker_html}</div><div class="cb-ticks">{ticks}</div><div class="cb-axis">Paid bookings per day · fixed RM4 weekday / RM5 peak mix · annual average</div></div>
</div>'''

CSS = '''<style id="cost-breakeven-style">
#investment .content { display:flex; flex-direction:column; gap:22px; }
#investment .cb-label { font-size:13px; font-weight:750; letter-spacing:.08em; text-transform:uppercase; color:#1a1a1a; }
#investment .cb-label em { font-style:normal; font-weight:500; letter-spacing:0; text-transform:none; color:#6b7280; margin-left:10px; font-size:14px; }
#investment .cb-grid { display:grid; grid-template-columns:1fr; flex:1; min-height:0; }
#investment .cb-chart { display:flex; flex-direction:column; min-height:0; }
#investment .cb-chart svg { display:block; width:100%; flex:1; min-height:0; margin-top:4px; }
#investment .cb-be { flex:none; display:grid; grid-template-columns:300px 1fr; gap:40px; align-items:end; padding-top:10px; border-top:1px solid #e5e7eb; }
#investment .cb-be-kpi strong { display:block; font-size:48px; line-height:1; font-weight:800; letter-spacing:-.03em; color:#e3261c; margin-top:8px; }
#investment .cb-be-kpi p { font-size:15px; line-height:1.35; color:#3b3f45; margin-top:6px; }
#investment .cb-be-scale { position:relative; padding-top:66px; }
#investment .cb-track { position:relative; height:14px; background:#e5e7eb; }
#investment .cb-loss { position:absolute; left:0; top:0; bottom:0; background:repeating-linear-gradient(135deg,#fecaca 0 6px,#fee2e2 6px 12px); }
#investment .cb-mark { position:absolute; bottom:-6px; width:0; }
#investment .cb-mark::before { content:""; position:absolute; left:-1.5px; bottom:0; width:3px; height:26px; background:#4b4f56; }
#investment .cb-mark.be::before { background:#e3261c; }
#investment .cb-mark.ref::before { background:#1a1a1a; width:4px; left:-2px; height:30px; }
#investment .cb-mark b, #investment .cb-mark span, #investment .cb-mark small { position:absolute; left:-2px; white-space:nowrap; }
#investment .cb-mark b { bottom:66px; font-size:20px; font-weight:800; }
#investment .cb-mark span { bottom:48px; font-size:13px; font-weight:700; }
#investment .cb-mark small { bottom:32px; font-size:12px; color:#6b7280; }
#investment .cb-mark.be b, #investment .cb-mark.be span { color:#e3261c; }
#investment .cb-mark.end b, #investment .cb-mark.end span, #investment .cb-mark.end small { left:auto; right:-2px; text-align:right; }
#investment .cb-ticks { position:relative; height:20px; margin-top:6px; font-size:12px; color:#6b7280; }
#investment .cb-ticks span { position:absolute; transform:translateX(-50%); }
#investment .cb-axis { font-size:12px; color:#6b7280; margin-top:2px; }
</style>'''

h = HTML.read_text(encoding='utf-8')
h = re.sub(r'<style id="cost-breakeven-style">.*?</style>', '', h, flags=re.S)
h = h.replace('</head>', CSS + '</head>', 1)

sec = re.search(r'<section[^>]*id="investment".*?</section>', h, re.S).group(0)
new = re.sub(r'<div class="content">.*?(?=<div class="source">)', lambda m: f'<div class="content">{content}</div>', sec, count=1, flags=re.S)
new = re.sub(r'<h2 class="slide-title">.*?</h2>', '<h2 class="slide-title">Zone cost and break-even</h2>', new, count=1, flags=re.S)
new = re.sub(r'aria-label="[^"]*"', 'aria-label="Zone cost and break-even"', new, count=1)
SRC = ('Sources: <a href="../presentation/consulting_v2_finance.py">V2 calculation</a>; '
       '<a href="https://viskou.my/products/4mpintelligententranceanprcamerads-tcg406-e">Viskou: DS-TCG406-E ANPR camera</a>; '
       '<a href="https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows">Viskou: DS-TVL224 display</a>; '
       '<a href="financial-sources.md">Sources, scope and unresolved costs</a>. One reference zone with two new LPR cameras. '
       'Listed prices exclude tax and show zero stock; allowances are unquoted. Excludes gates/controller, central support, project taxes and contingency. '
       'Break-even uses the 20% operator share and MYR-card fees; thresholds are annual averages, not demand forecasts.')
new = re.sub(r'<div class="source">.*?</div>', SRC.join(['<div class="source">', '</div>']), new, count=1, flags=re.S)
h = h.replace(sec, new, 1)
HTML.write_text(h, encoding='utf-8', newline='')
print(f'ok  upfront={fm.UPFRONT} first_year={fm.FIRST_YEAR} shares={shares} '
      f'be={be_running:.2f} ref={ref_day:.2f} 5y={be_5y:.2f} 3y={be_3y:.2f} net/booking={net_per_booking:.3f} payback={ref["payback"]:.2f}')

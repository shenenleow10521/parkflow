"""Insert a six-month implementation roadmap slide before the V2 three-horizon slide (#horizons).

Phases, owners and gates come from the existing V2 pilot schedule and decision slides; months are
indicative and sit inside H1 (0-6 months). Costs come from consulting_v2_finance.py.
Idempotent: reruns replace the slide and renumber footers.  python presentation/v2_roadmap_slide.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consulting_v2_finance as fm  # noqa: E402

HTML = Path(__file__).resolve().parents[1] / 'site-consulting' / 'index-v2.html'
rm = lambda v: f'RM{v / 1000:.1f}k'

# name, months label, first column, span, owner, activities, highlight
PHASES = [
    ('Mobilise &amp; survey', 'M1', 1, 1, 'SDP sponsor + operator', [
        'Nominate KL East sponsor and operator counterpart',
        'Site survey and zone boundary',
        'Controller, LPR and payment integration talks',
        'Baseline counts and member data']),
    ('Build &amp; install', 'M2', 2, 1, 'IT + integrator', [
        '2 new zone LPR cameras, LED sign, works',
        'Identity, bookings, payments, zone control',
        'Data access and count reconciliation']),
    ('Shadow &amp; readiness', 'M3', 3, 1, 'Team + operator', [
        'Commissioning and acceptance',
        'Optimizer shadow replay',
        'Guard readiness check',
        'Signed recovery SOP and fault drills']),
    ('Eight-week live pilot', 'M4–M5', 4, 2, 'Operator + loyalty', [
        'Controlled reservations at RM4 / RM5',
        'Assisted service and incident log',
        'Member visits compared against a control group',
        'Weekly operating and demand review']),
    ('Review &amp; decide', 'M6', 6, 1, 'Finance + sponsor', [
        'Installed scope and net capture',
        'Cost and investment review',
        'Scale, extend or stop']),
]
GATES = [  # position in months (0-6), code, label
    (0, 'G0', 'Approve scope discovery'),
    (1, 'G1', 'Installed quote → investment approval'),
    (3, 'G2', 'Readiness check → go live'),
    (6, 'G3', 'Scale / extend / stop → H2'),
]

months = ''.join(f'<div class="rm-month">Month {m}</div>' for m in range(1, 7))
chevrons = ''.join(
    f'<div class="rm-chev{" hl" if i == 3 else ""}{" first" if i == 0 else ""}" style="grid-column:{c + 1} / span {s}">'
    f'<b>{name}</b><span>{label}</span></div>'
    for i, (name, label, c, s, _, _) in enumerate(PHASES))
acts = ''.join(
    f'<div class="rm-cell{" hl" if i == 3 else ""}" style="grid-column:{c + 1} / span {s}"><ul>'
    + ''.join(f'<li>{a}</li>' for a in act) + '</ul></div>'
    for i, (_, _, c, s, _, act) in enumerate(PHASES))
owners = ''.join(f'<div class="rm-owner" style="grid-column:{c + 1} / span {s}">{o}</div>'
                 for _, _, c, s, o, _ in PHASES)
hardware = fm.UPFRONT - fm.INTEGRATION_ALLOWANCE
spend = ('<div class="rm-spend none" style="grid-column:2"><b>No CAPEX yet</b><span>survey team time only</span></div>'
         f'<div class="rm-spend capex" style="grid-column:3 / span 2"><b>CAPEX {rm(fm.UPFRONT)}</b>'
         f'<span>hardware &amp; works {rm(hardware)} + integration {rm(fm.INTEGRATION_ALLOWANCE)}</span></div>'
         f'<div class="rm-spend opex" style="grid-column:5 / span 3"><b>Running {rm(fm.ANNUAL_RUNNING)} a year</b>'
         '<span>from go-live; operator share and card fees scale with bookings</span></div>')
gates = ''.join(
    f'<div class="rm-gate{" end" if pos == 6 else ""}{" start" if pos == 0 else ""}" style="left:{pos / 6 * 100:.4f}%">'
    f'<i></i><b>{code}</b><span>{label}</span></div>' for pos, code, label in GATES)

content = f'''<div class="rm-grid">
<div class="rm-lab"></div>{months}
<div class="rm-lab">Phase</div>{chevrons}
<div class="rm-lab">Key activities</div>{acts}
<div class="rm-lab">Owner</div>{owners}
<div class="rm-lab">Spend</div>{spend}
<div class="rm-lab">Decision gates</div><div class="rm-gates" style="grid-column:2 / span 6"><div class="rm-line"></div>{gates}</div>
</div>
<div class="rm-sowhat"><span>So what</span><p>Four gates tie spending to evidence: no CAPEX before the installed quote, no paid bookings before readiness, no scale-up before the month-6 review.</p></div>'''

CSS = '''<style id="roadmap-style">
#roadmap .content { display:flex; flex-direction:column; gap:16px; }
#roadmap .rm-grid { flex:1; min-height:0; display:grid; grid-template-columns:150px repeat(6, 1fr); grid-template-rows:auto 74px 1fr auto auto 92px; column-gap:6px; row-gap:10px; }
#roadmap .rm-lab { display:flex; align-items:center; font-size:12.5px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:#53647a; border-right:2px solid #102a43; padding-right:10px; }
#roadmap .rm-month { text-align:center; font-size:14px; font-weight:700; color:#53647a; padding-bottom:6px; border-bottom:2px solid #d5dde7; }
#roadmap .rm-chev { display:flex; flex-direction:column; justify-content:center; padding:0 26px 0 34px; background:#102a43; color:#fff;
  clip-path:polygon(0 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 0 100%, 22px 50%); }
#roadmap .rm-chev.first { padding-left:18px; clip-path:polygon(0 0, calc(100% - 22px) 0, 100% 50%, calc(100% - 22px) 100%, 0 100%); }
#roadmap .rm-chev.hl { background:#e3261c; }
#roadmap .rm-chev b { font-size:18px; line-height:1.15; }
#roadmap .rm-chev span { font-size:13px; font-weight:700; opacity:.8; margin-top:2px; }
#roadmap .rm-cell { background:#f2f5f9; padding:12px 14px; border-top:3px solid #102a43; }
#roadmap .rm-cell.hl { background:#fdf0ef; border-top-color:#e3261c; }
#roadmap .rm-cell ul { margin:0; padding-left:16px; }
#roadmap .rm-cell li { font-size:14.5px; line-height:1.3; color:#102a43; margin:0 0 7px; }
#roadmap .rm-owner { display:flex; align-items:center; gap:8px; font-size:14px; font-weight:700; color:#102a43; padding:6px 10px; border:1.5px solid #d5dde7; border-radius:999px; justify-content:center; }
#roadmap .rm-owner::before { content:""; width:9px; height:9px; border-radius:50%; background:#102a43; }
#roadmap .rm-spend { display:flex; flex-direction:column; justify-content:center; padding:8px 14px; color:#fff; min-height:52px; }
#roadmap .rm-spend.capex { background:#102a43; }
#roadmap .rm-spend.none { color:#53647a; border:1.5px dashed #b6c5d8; background:#fff; }
#roadmap .rm-spend.opex { background:repeating-linear-gradient(135deg,#e3261c 0 10px,#ea4b42 10px 20px); }
#roadmap .rm-spend b { font-size:16px; }
#roadmap .rm-spend span { font-size:12.5px; opacity:.9; }
#roadmap .rm-gates { position:relative; }
#roadmap .rm-line { position:absolute; left:0; right:0; top:18px; height:3px; background:#102a43; }
#roadmap .rm-gate { position:absolute; top:0; width:0; }
#roadmap .rm-gate i { position:absolute; left:-15px; top:4px; width:30px; height:30px; background:#e3261c; transform:rotate(45deg); border:3px solid #fff; box-shadow:0 0 0 2px #e3261c; }
#roadmap .rm-gate b { position:absolute; left:-15px; width:30px; top:10px; text-align:center; font-size:12px; color:#fff; z-index:1; }
#roadmap .rm-gate span { position:absolute; top:46px; left:0; transform:translateX(-50%); width:190px; text-align:center; font-size:13.5px; font-weight:700; line-height:1.25; color:#102a43; }
#roadmap .rm-gate.start span { transform:none; left:2px; width:120px; text-align:left; }
#roadmap .rm-gate.end span { transform:none; left:auto; right:-15px; text-align:right; }
#roadmap .rm-sowhat { flex:none; display:flex; align-items:stretch; background:#102a43; color:#fff; min-height:50px; }
#roadmap .rm-sowhat span { display:flex; align-items:center; padding:0 22px; background:#e3261c; font-size:13px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
#roadmap .rm-sowhat p { align-self:center; padding:0 22px; font-size:16.5px; margin:0; }
</style>'''

SRC = ('Sources: <a href="../presentation/consulting_v2_finance.py">V2 calculation</a>; '
       '<a href="financial-sources.md">Sources, scope and unresolved costs</a>. Proposed sequence; months are indicative and sit inside '
       'H1 (0–6 months). Phases, owners and gates follow the eight-week pilot schedule and the next-steps slide. Costs are one reference '
       'zone before unpriced equipment, central support, project taxes and contingency. Not an agreed project plan or committed budget.')

h = HTML.read_text(encoding='utf-8')
h = re.sub(r'<style id="roadmap-style">.*?</style>', '', h, flags=re.S)
h = h.replace('</head>', CSS + '</head>', 1)
h = re.sub(r'<section[^>]*id="roadmap".*?</section>', '', h, flags=re.S)

hz = re.search(r'<section[^>]*id="horizons".*?</section>', h, re.S).group(0)
footer = re.search(r'<footer class="footer">.*?</footer>', hz, re.S).group(0)
new = ('<section aria-label="Implementation roadmap" class="slide" data-appendix="false" data-section="Implementation" id="roadmap">'
       '<div class="frame"><h2 class="slide-title">Implementation roadmap · first six months</h2>'
       f'<div class="content">{content}</div><div class="source">{SRC}</div>{footer}</div></section>')
h = h.replace(hz, new + hz, 1)

pages = re.findall(r'<span class="page">V2 · \d+ / \d+</span>', h)
total = len(pages)
counter = iter(range(1, total + 1))
h = re.sub(r'<span class="page">V2 · \d+ / \d+</span>',
           lambda m: f'<span class="page">V2 · {next(counter):02d} / {total}</span>', h)

HTML.write_text(h, encoding='utf-8', newline='')
print(f'ok  slides={total} capex={fm.UPFRONT:,} running={fm.ANNUAL_RUNNING:,}')

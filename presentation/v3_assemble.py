"""Run: python -B presentation/v3_assemble.py (after analysis/v3_zone200.py; commitment slides read analysis/benchmarks/commitment/results_v5.json and results_v6.json). One-off assembler: site-consulting/index-v2.html -> index-v3.html (V2 left untouched).
Keeps V2 design/CSS; reorders, edits, drops and adds slides. Numbers come from
analysis/benchmarks/v3/results.json so the text cannot drift from the simulation."""
import json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site-consulting'
src = (SITE / 'index-v2.html').read_text(encoding='utf-8')
R = json.loads((ROOT / 'analysis/benchmarks/v3/results.json').read_text())

# ---------------------------------------------------------------- model numbers
sys.path.insert(0, str(ROOT / 'analysis'))
from v3_costs import *   # NET, RUN, CAPEX, INTEGRATION, WBS, DAY_RATE, CAM, ... (sourced / derived / assumed, itemised there)
sweep = R['volume_sweep_200bays']
acc = [r['fulfilled'] + r['noshow'] + r['expired'] for r in sweep]
G = {s: sum(r[f'gross_per_day_s{s}'] / a for r, a in zip(sweep, acc)) / len(sweep) for s in (30, 50, 70)}  # gross RM per accepted booking
def contrib(n, s): return n * G[s] * 365 * NET - RUN
def need(n_years, s): return (RUN + (CAPEX / n_years if n_years else 0)) / (G[s] * 365 * NET)
THR = {sh: (need(0, sh), need(5, sh), need(3, sh)) for sh in (30, 50, 70)}
rows_n = acc[:4]
be_op, be_5, be_3 = need(0, 50), need(5, 50), need(3, 50)
low = contrib(rows_n[0], 50); gap = max(0, CAPEX / 5 - low)
gto_hi, gto_lo = gap / .05, gap / .15
fee_mix = 23_430 / 5_077.5
vo_5, vo_15 = fee_mix / (260 * .05), fee_mix / (260 * .15)
k = lambda v: f'{v/1000:.1f}k'
def payback(c): return f'{CAPEX/c:.1f} yr' if c > 0 else 'n/a'

# ---------------------------------------------------------------- parse
head = src[:src.find('<main>') + len('<main>')]
tail = src[src.find('</main>'):]
parts = re.split(r'(?=<section )', src[src.find('<main>') + 6:src.find('</main>')])[1:]
D = {re.search(r'id="([^"]+)"', p).group(1): p for p in parts}
WORDMARK = re.search(r'<span aria-label="ParkFlow" class="wordmark">.*?</svg></span>', D['problem'], re.S).group(0)
BRAND = re.search(r'<span class="brand">.*?</span></span>', D['cover'], re.S).group(0)

def rep(s, old, new, count=1):
    assert old in s, f'missing: {old[:70]}'
    return s.replace(old, new, count)

def edit(i, *pairs):
    for o, n in pairs: D[i] = rep(D[i], o, n)

# ---------------------------------------------------------------- edits to kept slides
edit('cover',
     ('<p class="cv-kicker">Proposed member service</p>', '<p class="cv-kicker">Proposed parking service</p>'),
     ('<h1>Member parking<br/>for <em>SDP malls</em></h1>', '<h1>Priority parking<br/>for <em>SDP malls</em></h1>'),
     ('Reserved access for members.<br/>KLGCC Mall is a proposed first pilot.', 'Open to every shopper; fee credited for members.<br/>KLGCC Mall is a proposed first pilot.'),
     ('revision 9 November 2026', 'revision 10 November 2026'))
edit('problem',
     ('<p>Parking friction at malls like KLGCC can lead to <em>lost visits</em>, <em>lower spending</em> and <em>weaker repeat visits</em>.</p>',
      '<p>Bays are finite, so the question is <em>allocation</em>: parking friction can lead to <em>lost visits</em>, <em>lower spending</em> and <em>weaker repeat visits</em>.</p>'))
edit('service',
     ('a dedicated <em>Priority Zone.</em>', 'a dedicated <em>parking zone.</em>'),
     ('Let shoppers reserve access to a ~100-bay Priority Zone near the mall lifts, with capacity planned between reservations and walk-ins.',
      'Any shopper can reserve a dedicated zone (one level, ~200 bays); members’ fee is credited to their parking bill.'),
     ('<b>Priority Zone</b><span>~100 parking bays</span>', '<b>Parking zone</b><span>one level, ~200 bays</span>'),
     ('Book a space in the Priority Zone before arrival, via the ParkFlow app.', 'Book a space in the zone before arrival. Members use their mall membership; the fee is credited to the bill.'),
     ('Zone LPR cameras recognise the plate, confirm the booking and admit the car.', 'The existing LPR recognises the plate, confirms the booking and admits the car.'),
     ('Choose any free bay in the shared zone, close to the mall lifts.', 'Choose any free bay in the zone. Unclaimed bookings are released after a 15-minute grace period.'),
     ('Demand forecasts and a rolling three-hour plan set how many spaces open for reservations. Current free capacity and accepted bookings decide every admission, so walk-ins keep their space.',
      'LPR counts and accepted bookings decide every admission, so walk-ins keep their space. A booking is a claim on the zone, not a fixed bay; unclaimed claims return to the pool.'),
     ('Utilisation, member value and booking income to test in the pilot.', 'Booking income from non-members, member engagement and tenant sales to test in the pilot.'),
     ('Proposed service. ~100 bays matches the reference zone used in the offline simulations; zone size, layout, LPR placement and live deployment remain to be confirmed in the site audit. Benefits are pilot hypotheses, not measured results.',
      'Proposed service. A whole level of about 200 bays is the planning size (Team Hexa site visit; level not named). Offline simulations were rerun at 200 bays (appendix). LPR and CCTV are site observations, to be confirmed with the mall. Benefits are pilot hypotheses, not measured results.'))
# (the member slide is rebuilt in full further down, so the V2 member slide is not edited here)
edit('operator',
     ('<div><dt>Audit</dt>', '<div><dt>Revenue</dt><dd>Track paid vs credited bookings, no-shows and voucher use (proposed addition).</dd></div><div><dt>Audit</dt>'))
edit('admission',
     ('<h3>100-bay zone right now</h3>', '<h3>Zone right now · 100 bays shown</h3>'),
     ('<li>Counts + live ledger show the zone right now</li>', '<li>LPR entry/exit counts + live plate ledger show the zone right now</li>'))
D['admission'] = re.sub(r'(<div class="source">.*?)(</div><footer)',
    lambda m: m.group(1) + ' LPR count drift was simulated: at 1% missed reads, unseen cars peak at about 6 (99th percentile), so the safety buffer is sized from the pilot’s read accuracy.' + m.group(2),
    D['admission'], count=1, flags=re.S)
edit('integration', ('Connect the new zone to the mall', 'Connect the zone to the mall'),
     ('Can the two NEW zone LPR cameras produce reconciled entry/exit events?', 'Can the existing level LPR provide reconciled entry/exit events and a plate ledger?'),
     ('Buy cameras only after local coverage and false-free errors are tested.', 'CCTV is an audit layer, not the counter: buy cameras only where the survey finds blind spots.'),
     ('Existing mall; additional zone equipment required.', 'Existing mall: LPR and CCTV observed on our site visit (to be confirmed).'),
     ('<dd>Two new zone cameras; verify plate support, interfaces and controller handoff.</dd>', '<dd>Existing LPR observed; confirm vendor, data/API access and read accuracy.</dd>'),
     ('<dd>Survey coverage before pricing additional cameras.</dd>', '<dd>Survey blind spots; add cameras only where the audit needs them.</dd>'),
     ('<dd>Confirm member identity, API rights and payment settlement.</dd>', '<dd>Mall membership system: confirm identity, API rights and payment settlement.</dd>'),
     ('New-zone scope includes two additional LPR cameras. Confirm controller', 'LPR is a Team Hexa site observation, not mall-confirmed. Confirm controller'))
edit('alternatives', ('Extend beyond EV bays to member parking', 'Extend beyond EV bays to the whole zone'))
edit('team', ('building a member parking proposition', 'building a parking proposition'))
edit('roadmap',
     ('2 new zone LPR cameras, LED sign, works', 'Blind-spot CCTV (if surveyed), display, works'),
     ('CAPEX RM80.0k', f'CAPEX RM{CAPEX/1000:.1f}k'),
     ('hardware &amp; works RM20.0k + integration RM60.0k', f'hardware &amp; works RM{(CAPEX-INTEGRATION)/1000:.1f}k + integration RM{INTEGRATION/1000:.1f}k'))
D['decision'] = D['decision'].replace('<a href="../presentation/consulting_v2_finance.py">V2 calculation</a>; <a href="financial-sources.md">Sources, scope and unresolved costs</a>', '<a href="../analysis/v3_zone200.py">V3 simulation</a>; data register in the appendix')
D['roadmap'] = D['roadmap'].replace('<a href="../presentation/consulting_v2_finance.py">V2 calculation</a>; <a href="financial-sources.md">Sources, scope and unresolved costs</a>', '<a href="../analysis/v3_zone200.py">V3 simulation</a>; data register in the appendix')
edit('pilot-design',
     ('<li>Member baseline + price offers</li>', '<li>Member baseline + price and voucher arms</li>'),
     ('<li>Zone counts + data integration</li>', '<li>LPR counts + data integration</li>'),
     ('<li>Member visits vs control group</li>', '<li>Visits vs control; price, voucher arms</li>'))
edit('decision',
     ('<b>RM90.5k +</b><span>Reference new-zone subtotal<br/>Two NEW zone LPR cameras included</span>',
      f'<b>RM{CAPEX/1000:.1f}k</b><span>Reference upfront, KLGCC zone<br/>Range RM{CAPEX_LO/1000:.1f}–{CAPEX_HI/1000:.1f}k · plus RM10.5k/yr running</span>'),
     ('Two new LPR cameras, complete zone works, support and lease-linked net visit value; no double-counting.',
      'Installed integration quote, CCTV survey result, support and lease-linked net visit value; no double-counting.'),
     ('Price conversion, 30/60/90-day return rates and extra mall visits against a control.',
      'Price and voucher conversion, 30/60/90-day return rates and extra mall visits against a control.'))
D['decision'] = D['decision'].replace('data-financial-model="v2-2026-11-09"', 'data-financial-model="v3-2026-11-10"')

# ---------------------------------------------------------------- new slides
def new(id_, label, section, appendix, topbar, title, body, source, cls='slide v3p'):
    return (f'<section aria-label="{label}" class="{cls}" data-appendix="{appendix}" data-financial-model="v3-2026-11-10" data-section="{section}" id="{id_}">'
            f'<div class="frame"><h2 class="slide-title">{title}</h2>'
            f'<div class="content">{body}</div><div class="source">{source}</div><footer class="footer"></footer></div></section>')

def compact(id_, label, title, body, source):
    return (f'<section aria-label="{label}" class="slide compact" data-appendix="true" data-financial-model="v3-2026-11-10" data-section="Appendix" id="{id_}">'
            f'<div class="frame"><h2 class="slide-title">{title}</h2><div class="content">{body}</div><div class="source">{source}</div><footer class="footer"></footer></div></section>')

T = lambda c, t: f'<span class="v3-t v3-t--{c}">{t}</span>'
S, M, A = T('s', 'Sourced'), T('m', 'Simulated'), T('a', 'Assumed')


def rep_html(html, old, new_):
    assert old in html, old[:60]
    return html.replace(old, new_, 1)


def remove_div(html, marker):
    a = html.index(marker); depth = 0; i = a
    while True:
        o = html.find('<div', i); c = html.find('</div>', i)
        if o != -1 and o < c: depth += 1; i = o + 4
        else:
            depth -= 1; i = c + 6
            if depth == 0: return html[:a] + html[i:]

# customer journey: new prototype screens (origin/main, driver prototype)
phones = [('1 · Home', 'proto-home', 'Prototype home screen'), ('2 · Reserve', 'proto-reserve', 'Reserve screen with arrival time and fee'),
          ('3 · Confirm', 'proto-confirmed', 'Booking confirmed with QR entry pass'), ('4 · Zone', 'proto-zone', 'Zone capacity by level')]
ph = '<li class="v3-arr" aria-hidden="true"></li>'.join(f'<li><span>{a}</span><figure><img alt="{c}" src="assets/{b}.webp"/></figure></li>' for a, b, c in phones)
D['member'] = new('member', 'Customer booking journey', 'Product', 'false', '', 'Customer journey: <em>reserve, enter, park.</em>',
    f"""<div class="v3-jr"><ol class="v3-phones">{ph}</ol>
<div class="v3-fns"><h3>What the prototype shows</h3>
<div class="v3-fn"><b>Reserve</b><p>Pick a mall, date and arrival time. The fee and the no-show rule are shown before confirming.</p></div>
<div class="v3-fn"><b>Enter</b><p>A QR entry pass after booking. The LPR check is simulated, with no live gate connection.</p></div>
<div class="v3-fn"><b>See the zone</b><p>Occupied, reserved and available bays by level, with safety bays protected.</p></div></div></div>
<div class="v3-sowhat"><span>Pricing test</span><p>RM4 weekday / RM5 peak. Members’ fee is credited to their parking bill; non-members pay it on top. It is kept if the customer does not arrive (15-minute grace).</p></div>""",
    'Screens captured from the ParkFlow driver prototype, simulated data (it shows 100 bays and a RM5 demo fee). No payment processing or live gate connection. Offline simulation results are separate.')

# site readiness: photos move here from the pilot slide
photos = [('klgcc-visit-entry-barrier', 'Entry barrier and LPR', '55% 55%'), ('klgcc-visit-camera-check', 'Mapping camera positions', '50% 35%'),
          ('klgcc-visit-cctv-aisle', 'CCTV over the aisles', '50% 30%'), ('klgcc-visit-cctv-ceiling', 'Ceiling camera coverage', '50% 45%'),
          ('klgcc-visit-rates-board', 'Posted rates and payments', '60% 35%'), ('klgcc-visit-staff-interview', 'Customer-service interview', '50% 30%')]
aside = ('<aside class="v3-photos">' + ''.join(f'<figure><img alt="{c}" src="assets/{f}.webp" style="object-position:{p}"/><figcaption>{c}</figcaption></figure>' for f, c, p in photos)
         + '<p>Observed on the 9 Nov 2026 site visit. Vendor, data access and blind spots are still to be confirmed.</p></aside>')
D['integration'] = re.sub(r'<aside class="capability-assets">.*?</aside>', lambda m: aside, D['integration'], flags=re.S)
edit('integration', ('<h2 class="slide-title">Site and system integration</h2>', '<h2 class="slide-title">Site readiness: <em>what the pilot must confirm.</em></h2>'))

# pilot: photos out, decision gates in
D['pilot-design'] = remove_div(D['pilot-design'], '<div class="pv-strip">')
edit('pilot-design', (' Photos: Team Hexa site visit to KLGCC Mall, 9 Nov 2026, including an interview with KLGCC customer-service staff.', ''))
gates = (f'<div class="v3-gates"><h3>Decision gates</h3><ol><li><b>G0</b><span>Approve scope discovery</span><em>No CAPEX yet</em></li>'
         f'<li><b>G1</b><span>Installed quote → investment approval</span><em>CAPEX RM{CAPEX/1000:.1f}k</em></li>'
         '<li><b>G2</b><span>Readiness check → go live</span><em>Running RM10.5k a year</em></li>'
         '<li><b>G3</b><span>Scale, extend or stop</span><em>Month-6 review</em></li></ol></div>')
D['pilot-design'] = rep_html(D['pilot-design'], '</div><div class="source">', gates + '</div><div class="source">')

# ask: one-line path to scale
hz = ('<div class="v3-hz"><h3>If the gates pass · direction, not a forecast</h3><ol><li><b>H1 · Prove</b><span>KLGCC service · 0–6 months</span></li>'
      '<li><b>H2 · Replicate</b><span>SDP malls, e.g. Elmina, KL East · 6–24 months</span></li>'
      '<li><b>H3 · Scale</b><span>External operators · 24–60 months</span></li></ol></div>')
D['decision'] = rep_html(D['decision'], '</div><div class="source">', hz + '</div><div class="source">')

D['paths'] = new('paths', 'Two paths to priority parking', 'Business', 'false', 'Pricing and retention',
    'Two paths to a bay, <em>one loyalty loop.</em>',
    f'''<div class="v3-paths">
<article class="v3-path"><header><span>01</span><h3>Pay to reserve</h3></header>
<div class="v3-path__body"><div class="v3-fig"><b>RM4<small>–5</small></b><span>per booking · weekday / peak · open to every shopper</span></div>
<ul><li><b>Members:</b> fee is credited to the parking bill, so they pay at least RM4 in total.</li><li><b>Non-members:</b> fee is charged on top of normal parking.</li><li><b>No-show:</b> fee is kept as a commitment deposit.</li></ul></div>
<p class="v3-path__goal">Monetises convenience-seekers and gives non-members a reason to join.</p></article>
<article class="v3-path v3-path--red"><header><span>02</span><h3>Spend to earn</h3></header>
<div class="v3-path__body"><div class="v3-fig"><b>RM300<small>+</small></b><span>example threshold · set per mall’s loyalty programme</span></div>
<ul><li>Qualifying spend unlocks a <b>priority-parking voucher</b> for a future visit.</li><li>Limited to available slots, mainly off-peak, so a bay that would sit empty costs little.</li><li>Funded from the mall’s existing loyalty or marketing budget.</li></ul></div>
<p class="v3-path__goal">Rewards valuable shoppers and gives them a reason to return.</p></article></div>
<div class="v3-loop"><ol><li>Visit</li><li>Spend</li><li>Earn</li><li>Return</li></ol><p><b>Hypothesis to measure:</b> repeat visits → incremental tenant sales → potential GTO rental uplift. A paid booking also shows the spend-to-earn offer.</p></div>
<div class="v3-sowhat"><span>Test it</span><p>A voucher costs about RM{fee_mix:.1f} of foregone fee. It pays back if roughly <b>1 in {1/vo_5:.0f} holders (5% rent clause) to 1 in {1/vo_15:.0f} (15%)</b> makes a visit they would not otherwise make.</p></div>''',
    'Voucher arithmetic: RM4.6 = fee forgone per booking (RM23,430 gross fees ÷ 5,077.5 paid bookings in the reference mix of 30 peak and 7.5 weekday bookings a day at RM5 / RM4; an upper bound, since members’ fee is credited to their bill anyway) ÷ (RM260 mean recalled trip spend × 5–15% gross turnover-rent clause). Assumes an induced visit spends the average and that the spend is at tenants above their rent floor. Spend: <a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026">Vase.ai</a>; lease range: <a href="https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32">Tropicana</a>. Precedent: <a href="https://www.1utama.com.my/services/">1 Utama spend-linked parking</a>. RM300 is an example threshold, not a finding.')

def cell(n, s):
    c = contrib(n, s)
    cls = 'neg' if c <= 0 else ('mid' if CAPEX / c > 5 else 'good')
    return f'<td class="v3-c v3-c--{cls}"><b>{"−" if c < 0 else ""}RM{abs(c)/1000:.1f}k</b><small>{payback(c)}</small></td>'
sens = ''.join(f'<tr><th scope="row">≈{n:.0f} / day</th>{cell(n,30)}{cell(n,50)}{cell(n,70)}</tr>' for n in rows_n)
D['revenue'] = new('revenue', 'Booking revenue model', 'Business', 'false', 'Commercial model',
    'Revenue depends on <em>who books</em>, not just how many.',
    f'''<div class="v3-rev">
<section><h3 class="module-title red">What one booking adds to the mall</h3>
<table class="v3-tbl"><thead><tr><th></th><th>Weekday</th><th>Weekend</th></tr></thead><tbody><tr><th scope="row">Non-member or no-show</th><td><b>RM4</b></td><td><b>RM5</b></td></tr><tr><th scope="row">Member, up to 3 hours</th><td><b>RM1</b></td><td><b>RM2</b></td></tr><tr><th scope="row">Member, over 3 hours</th><td><b>RM1</b></td><td><b>RM0</b></td></tr></tbody></table>
<p class="v3-note">Booking fee RM4 weekday, RM5 weekend. A member’s fee is credited to the parking bill, so only any excess counts. A no-show pays the fee, like a non-member.</p></section>
<section><h3 class="module-title red">Annual contribution by volume and member share</h3>
<table class="v3-tbl v3-sens"><thead><tr><th>Accepted bookings</th><th>30% members</th><th>50% members</th><th>70% members</th></tr></thead><tbody>{sens}</tbody></table>
<p class="v3-note">After 6% SST, 20% operator allocation, card fees and RM10.5k running; payback on RM{CAPEX/1000:.1f}k upfront. Capacity at 200 bays {M} · volume and member share {A}</p></section></div>
<div class="v3-sowhat"><span>So what</span><p>At 50% members, about <b>{be_op:.0f} bookings a day</b> cover running cost, <b>{be_5:.0f}</b> recover the capital in 5 years and <b>{be_3:.0f}</b> in 3. Capacity is not the limit: <b>demand and willingness to pay are</b>.</p></div>''',
    'Contribution = accepted bookings × gross per booking × 365 × net factor − running cost, from the 200-bay simulation. Volume and member share are scenarios; the 20% operator share is unagreed. Derivation: appendix.')

bars = [('Software and integration', INTEGRATION, 'a', f'RM{DAY_RATE:.0f}/day × {BUILD_DAYS:.0f} days; quote before G1'),
        ('Power, network and works', 7_500, 'a', 'Allowance; survey firms it up'),
        ('Blind-spot CCTV: 4 cameras', N_CAM * CAM, 'a', f'RM{CAM:,} each; quote after survey'),
        ('Guidance display (optional)', 2_033, 's', 'Viskou list price, tax extra'),
        ('LPR cameras', 0, 's', 'Existing at KLGCC; RM3,226 each if absent')]
bar_html = ''.join(
    f'<div class="v3-bar"><div class="v3-bar__n"><b>{n}</b><small>{d}</small></div><div class="v3-bar__t"><i class="v3-bar__f v3-bar__f--{t}" style="width:{max(v/INTEGRATION*100, 0):.1f}%"></i></div><div class="v3-bar__v">RM{v:,}{" "+(S if t=="s" else A)}</div></div>'
    for n, v, t, d in bars)
D['cost'] = new('cost', 'KLGCC zone cost', 'Business', 'false', 'Cost per zone',
    f'KLGCC zone: <em>RM{CAPEX/1000:.1f}k upfront</em>, RM10.5k a year.',
    f'''<div class="v3-cost"><section><h3 class="module-title red v4-band"><b>CAPEX</b><span>One-time, upfront investment</span></h3>{bar_html}
<div class="v3-total"><span>Total upfront</span><b>RM{CAPEX:,}</b><em>range RM{CAPEX_LO/1000:.1f}k (no CCTV, no display) to RM{CAPEX_HI/1000:.1f}k (10 cameras, display, +{OVERRUN*100:.0f}% build overrun)</em></div></section>
<aside><h3 class="module-title">Other malls: same template, different inputs</h3>
<ol class="v3-ready"><li><b>LPR at the zone?</b><span>If absent: +RM3.2k per camera</span></li><li><b>Counts from LPR?</b><span>If not: add a counting method</span></li><li><b>CCTV blind spots?</b><span>0 / 4 / 10 cameras = RM0 / {N_CAM*CAM/1000:.0f}k / {10*CAM/1000:.0f}k</span></li><li><b>Member API and payment?</b><span>Drives the integration quote</span></li></ol>
<p class="v3-note">The platform build is paid once; later malls pay site integration only.</p></aside></div>
<div class="v3-sowhat"><span>So what</span><p>Integration is <b>{INTEGRATION/CAPEX*100:.0f}% of upfront cost</b> and is an effort estimate, not a quote: that is the biggest risk. A pilot-scope build is about <b>RM{PILOT_BUILD/1000:.0f}k</b>.</p></div>''',
    'Later malls pay site integration only; the platform build is paid once. Sources: <a href="https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows">Viskou display</a>; <a href="https://mall.lapasar.com/office-management/it-electronics/products/hikvision-ds-2cd2046g2-iusl-4mp/121">Hikvision 4MP</a>; <a href="https://www.payscale.com/research/MY/Job=Senior_Software_Developer/Salary">Payscale</a>; <a href="https://aws-pricing.com/ap-southeast-5.html">AWS Malaysia</a>. Effort days, cable run and labour are assumptions. Who funds the build is not yet agreed: these are zone costs, not a quote. Derivation: appendix.')

D['value'] = new('value', 'Value to SDP', 'Business', 'false', 'Value to SDP',
    'For SDP, the bar is <em>low</em>; the evidence is directional.',
    f'''<div class="v3-val">
<article><span class="v3-eyebrow">GTO break-even</span><b>RM{gto_lo/1000:.0f}–{gto_hi/1000:.0f}k</b><p>extra eligible tenant sales a year closes the 5-year capital gap at 15% to 5% rent clauses, in the low-volume case (≈{rows_n[0]:.0f} bookings/day, 50% members).</p><div class="v3-meas"><b>Pilot measure</b>Eligible tenant sales of members versus control, tenant by tenant and above the rent floor.</div></article>
<article><span class="v3-eyebrow">Voucher break-even</span><b>1 in {1/vo_5:.0f}–{1/vo_15:.0f}</b><p>voucher holders must make a visit they would not otherwise make for a RM{fee_mix:.1f} voucher to pay back through turnover rent.</p><div class="v3-meas"><b>Pilot measure</b>Voucher redemption, and the share of holders whose return visit is incremental versus control.</div></article>
<article><span class="v3-eyebrow">Spend gap · association only</span><div class="v3-cmp"><div><i style="height:{195/327*100:.0f}%"></i><span>RM195<small>1–2 visits / month</small></span></div><div><i class="hi" style="height:100%"></i><span>RM327<small>5+ visits / month</small></span></div></div><p>Recalled trip spend, +68%. It does not show that parking causes either.</p><div class="v3-meas"><b>Pilot measure</b>30/60/90-day return rate and visits per member versus an eligible control cohort.</div></article></div>
<div class="v3-sowhat"><span>Caveat</span><p>Gross turnover rent has a floor: extra sales below it add <b>zero</b> rent. Count it tenant by tenant, and net out vouchers, support and displacement before calling it profit.</p></div>''',
    f'Gap = RM{CAPEX/1000:.1f}k ÷ 5 − RM{low/1000:.1f}k contribution. Sales needed = gap ÷ rent rate. Sources: <a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026">Vase.ai (N=500)</a>; <a href="https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32">Tropicana lease terms</a>; <a href="https://www.simedarbyproperty.com/sites/default/files/2024-05/Reply%20Letter%20to%20MSWG%20%2817052024%29.pdf">SDP reply to MSWG</a>. No SDP-specific rent rate or retention effect is claimed. Derivation: appendix.')

reg = [('Reservation fee RM4 weekday / RM5 peak', A, 'Price test. Local anchor: Sunway ParkEasy reservations reported at 6–8 credits (RM1 each) per booking; verify current price.'),
       ('Standard parking bill', S, 'KLGCC official tariff: RM3 weekday; weekend RM3 to 3h, then RM2/h, cap RM10.'),
       ('Member offset rule', A, 'Fee credited to the bill; excess kept as revenue; deposit kept on no-show. Our design choice.'),
       ('No-show rate 5–20%', A, 'Other settings report 10–31% (campground model, car rental, one city system). Not parking at malls.'),
       ('Grace period 15 min, soft release', M, 'Tested at 10–30 min; with soft release the choice barely moves idle bay-hours.'),
       ('Bookings per day, member share', A, 'No local data. Scenario ranges; the pilot measures both.'),
       ('LPR and CCTV at KLGCC', S, 'Team Hexa site visit, 9 Nov 2026. Vendor, data access and blind spots unconfirmed.'),
       ('CCTV and site works', A, f'RM{CAM:,} a camera = RM{CAM_HW} camera (sourced) + RM{CAM_CABLE} cable (RM100 per 10 m, 40 m assumed, unverified) + RM{CAM_LABOUR} labour (half-day, assumed). Power, network and works RM{WORKS:,} is a flat allowance for switch, UPS, trunking and signage; no survey yet.'),
       ('LPR miss rate 0.5–3%', M, 'Count-drift simulation; real read accuracy is a pilot measurement.'),
       (f'Software RM{INTEGRATION/1000:.1f}k, running RM{RUN/1000:.1f}k/yr', A, f'{BUILD_DAYS:.0f} person-days × RM{DAY_RATE:.0f}/day; running = 15% of build + hosting. Appendix.'),
       ('Service tax on the booking fee', S, 'Parking is taxed at 6% (Customs guide). A reservation fee is not listed as exempt; treated as tax-inclusive: conservative.'),
       ('Willingness to pay', A, 'Directional only: ParkMobile 67% (US). No local test; first pilot measure.')]
D['a-register'] = compact('a-register', 'Data register', 'Data register: what is sourced, simulated or assumed',
    '<table><colgroup><col style="width:30%"/><col style="width:11%"/><col style="width:59%"/></colgroup><thead><tr><th>Input</th><th>Tier</th><th>Basis</th></tr></thead><tbody>'
    + ''.join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in reg) + '</tbody></table>',
    'Order of preference: web sources, then simulation, then assumptions as a last resort. Web-derived items come from search results and must be opened and checked before submission. Nothing here is a measured KLGCC demand or price response.')

rows_w = ''.join(f'<tr><td>{n}</td><td>{d}</td><td>{pd_}</td></tr>' for n, d, pd_ in WBS)
D['a-build-estimate'] = compact('a-build-estimate', 'Build effort and running cost', 'How the software and running costs are derived',
    f'''<div class="cols"><div class="col"><h3 class="module-title">Work breakdown · person-days (assumed effort)</h3>
<table><colgroup><col style="width:58%"/><col style="width:22%"/><col style="width:20%"/></colgroup><thead><tr><th>Work package</th><th>Production</th><th>Pilot</th></tr></thead><tbody>{rows_w}
<tr><td>Project management and QA, +{PM_UPLIFT*100:.0f}%</td><td>{BUILD_DAYS-sum(w[1] for w in WBS):.1f}</td><td>{PILOT_DAYS-sum(w[2] for w in WBS):.1f}</td></tr>
<tr><td><b>Total person-days</b></td><td><b>{BUILD_DAYS:.0f}</b></td><td><b>{PILOT_DAYS:.0f}</b></td></tr>
<tr><td><b>× RM{DAY_RATE:.0f} a day</b></td><td><b>RM{INTEGRATION:,.0f}</b></td><td><b>RM{PILOT_BUILD:,.0f}</b></td></tr></tbody></table>
<p class="note"><b>Cross-checks.</b> Vendor pages price a comparable app (payment, admin) at RM50–150k, which includes their margin; the prototype here already exists. Payment integration takes 2–3 weeks per vendor guidance (we use 12 days). Surveys put average software overrun at 30–40%: the high-end range adds {OVERRUN*100:.0f}%. All maintenance, enhancements included, would be 30% of build a year (running RM{RUN_ALL/1000:.1f}k).</p></div>
<div class="col"><h3 class="module-title">Day rate · sourced inputs</h3>
<table><colgroup><col style="width:74%"/><col style="width:26%"/></colgroup><thead><tr><th>Step</th><th>Value</th></tr></thead><tbody>
<tr><td>Senior software developer, annual base (Payscale, 2026)</td><td>RM{SALARY:,}</td></tr>
<tr><td>Employer on-costs: EPF 12% + SOCSO/EIS (capped)</td><td>+{ONCOST*100:.0f}%</td></tr>
<tr><td>Productive days a year (assumed)</td><td>{PROD_DAYS}</td></tr>
<tr><td><b>Cost per person-day, no agency margin</b></td><td><b>RM{DAY_RATE:.0f}</b></td></tr></tbody></table>
<h3 class="module-title">Running cost a year</h3>
<table><colgroup><col style="width:74%"/><col style="width:26%"/></colgroup><thead><tr><th>Item</th><th>RM</th></tr></thead><tbody>
<tr><td>Maintenance: {MAINT_RATE*100:.0f}% of build (derived, see note)</td><td>{MAINT_RATE*INTEGRATION:,.0f}</td></tr>
<tr><td>Hosting: 2 × t3.medium, AWS Malaysia, 24×7, at RM{USD_MYR}/USD</td><td>{HOSTING:,.0f}</td></tr>
<tr><td><b>Running</b></td><td><b>{RUN:,.0f}</b></td></tr></tbody></table></div></div>''',
    'Effort per work package is an assumption: it is itemised so a vendor can replace each line with a quote. Payscale and AWS figures were opened and checked. Maintenance: studies put it at 60–90% of software cost; at the lowest, 60% over 5 years, that is 30% of build a year, and corrective plus adaptive work (45%) gives 13.6%, rounded up to 15%. Enhancements are excluded. A vendor quote would add its margin on top of this cost basis.')

D['a-method-notes'] = compact('a-method-notes', 'Commercial and value derivations', 'How the commercial and value numbers are derived',
    f'''<div class="cols"><div class="col"><h3 class="module-title">Commercial model · slide 10</h3><ul>
<li><b>Net factor {NET:.3f} per RM of fee:</b> 0.8 ÷ 1.06 (the operator takes 20% of the ex-tax fee) − 1.944% (card fee on the amount collected).</li>
<li><b>Service tax 6%:</b> parking is taxed at 6% (Customs guide). A reservation fee is not listed as exempt, so the fee is treated as tax-inclusive. If untaxed, contribution is about 6% higher.</li>
<li><b>Gross per booking:</b> RM{G[50]:.2f} at 50% members, from the 200-bay simulation (40 synthetic days per volume; deposits credited to members’ bills).</li>
<li><b>Displaced parking revenue:</b> cars sent to other levels pay the same KLGCC tariff, so only walk-ins who leave the mall are a loss. The pilot measures it.</li>
<li><b>Break-even at 50% members:</b> running cost at {be_op:.0f} bookings a day, 5-year recovery at {be_5:.0f}, 3-year at {be_3:.0f}.</li></ul></div>
<div class="col"><h3 class="module-title">Value to SDP · slide 12</h3><ul>
<li><b>Gap:</b> RM{CAPEX/1000:.1f}k ÷ 5 − RM{low/1000:.1f}k contribution at ≈{rows_n[0]:.0f} bookings a day = RM{gap/1000:.1f}k a year.</li>
<li><b>Sales needed:</b> gap ÷ rent clause (5–15%, Tropicana valuation) = RM{gto_lo/1000:.0f}k–{gto_hi/1000:.0f}k. Turnover rent has a floor: extra sales below it add zero.</li>
<li><b>Voucher:</b> RM{fee_mix:.1f} fee forgone per booking (RM23,430 gross ÷ 5,077.5 paid bookings in the reference mix; an upper bound, as members’ fee is credited) ÷ (RM260 mean recalled trip spend × rent clause).</li>
<li><b>Spend gap:</b> RM195 against RM327 recalled trip spend (Vase.ai, N=500), +68%. Association only.</li>
<li><b>Pilot measures:</b> member sales versus control tenant by tenant above the rent floor; voucher redemption and incremental return visits; 30/60/90-day return rate.</li></ul></div></div>''',
    'Every figure here is a scenario or a sensitivity, not a forecast. Sources: appendix source slides.')

sw = ''.join(f'<tr><td>{r["req_per_day"]}</td><td>{a:.0f}</td><td>{r["fulfilled"]:.0f}</td><td>{r["noshow"]+r["expired"]:.0f}</td><td>{r["walkins"]:.0f}</td><td>{r["rejection_pct"]:.1f}%</td></tr>' for r, a in zip(sweep, acc))
gr = ''.join(f'<tr><td>{g["grace_min"]} min</td><td>{g["idle_bayh"]:.1f}</td><td>{g["late_in"]:.1f}</td><td>{g["late_denied"]:.1f}</td></tr>' for g in R['grace_test'])
dr = ''.join(f'<tr><td>{d["p_miss"]*100:.1f}%</td><td>{d["unseen_p99"]:.0f}</td><td>{d["ghost_p99"]:.0f}</td></tr>' for d in R['lpr_drift'])
D['a-sim200'] = compact('a-sim200', '200-bay zone simulation', '200-bay zone: capacity, grace period and LPR count drift',
    f'''<div class="cols"><div class="col"><h3 class="module-title">Volume sweep · guard + fixed buffer 10 · grace 15 min</h3>
<table><thead><tr><th>Requests/day</th><th>Accepted</th><th>Arrived</th><th>Unclaimed</th><th>Walk-ins</th><th>Rejected</th></tr></thead><tbody>{sw}</tbody></table>
<p class="note">Mean of 40 synthetic days per row. Walk-in demand scales with zone size. Demand shape is assumed.</p></div>
<div class="col"><h3 class="module-title">Grace period · 90 requests/day</h3>
<table><thead><tr><th>Grace</th><th>Idle bay-h/day</th><th>Late, admitted</th><th>Late, denied</th></tr></thead><tbody>{gr}</tbody></table>
<h3 class="module-title">LPR count drift · plate ledger, 5h ghost timeout</h3>
<table><thead><tr><th>Missed reads</th><th>Unseen cars (p99)</th><th>Ghost cars (p99)</th></tr></thead><tbody>{dr}</tbody></table></div></div>''',
    'Synthetic demand; late-arrival mix 80/12/6/2% is an assumption. Soft release lets a late customer in when capacity exists. Unseen cars (missed entry) undercount; ghost cars (missed exit) overcount, the safe direction. Code: <a href="../analysis/v3_zone200.py">analysis/v3_zone200.py</a>; results: <a href="../analysis/benchmarks/v3/results.json">results.json</a>.')

src_v3 = [('Payscale: senior software developer, Malaysia', 'https://www.payscale.com/research/MY/Job=Senior_Software_Developer/Salary', 'Opened: RM115,701 average base, 2026.'),
          ('AWS pricing, ap-southeast-5 (Malaysia)', 'https://aws-pricing.com/ap-southeast-5.html', 'Opened: t3.medium USD0.0475 per hour (third-party mirror).'),
          ('Customs: Guide on Parking Services', 'https://ccs-co.com/wp-content/uploads/4.1-Guide-on-Parking-Services-27.12.2021.pdf', 'Opened: 6% on parking (para 11); reserved-signage charges exempt. 2024 rate hold per PwC and Wolters Kluwer, not opened.'),
          ('MIDA: statutory contributions', 'https://www.mida.gov.my/setting-up-business/statutory-contributions/', 'Opened: employer EPF 13% to RM5,000 wage, 12% above; SOCSO 1.75%.'),
          ('Univ. of Cantabria OCW: software maintenance costs', 'https://ocw.unican.es/pluginfile.php/2171/course/section/2000/SMCOSTS.pdf', 'Opened: maintenance is 60–90% of total software cost across studies.'),
          ('Moløkken-Østvold and Jørgensen: estimation surveys', 'https://static.aminer.org/pdf/PDF/000/435/238/a_review_of_surveys_on_software_effort_estimation.pdf', 'Average effort overrun 30–40%, as the authors later summarise it. Not opened.'),
          ('AdvisoryApps: app cost and payment integration, Malaysia', 'https://advisoryapps.com/blog/how-much-does-it-cost-to-develop-an-app-in-malaysia-in-2026', 'RM50–150k mid-range app; payment integration 2–3 weeks. Vendor marketing; script-rendered, not verified.'),
          ('exchangerate.guru: USD to MYR', 'https://exchangerate.guru/usd/myr/', 'About 4.06 on 1 Nov 2026 as reported by search; not an official BNM rate.'),
          ('AlienVoIP: 4CH POE CCTV installation bundle', 'https://www.alienvoip.com/?p=17605', 'RM2,599 bundle, RM100 per extra 10 m cable, per search. Script-rendered, not verified.'),
          ('EdgeProp: KLGCC Mall early footfall', 'https://www.edgeprop.my/content/1914504/sime-darby-property-sees-klgcc-mall-breaking-even-sooner-expected-amid-strong-footfall', 'About 100,000 visitors in the first weeks; no annual figure.'),
          ('Autobuzz: Sunway Pyramid reservation bays', 'https://autobuzz.my/2019/06/12/reserve-park-and-charge-at-reserve-shell-recharge-bays-in-sunway-pyramid/', 'ParkEasy booking reported at 6 (weekday) / 8 (weekend) credits, 1 credit = RM1; 2019, EV bays.'),
          ('TP-Link VIGI C340i, Lelong', 'https://www.lelong.com.my/tp-link-vigi-c340i-4mp-outdoor-ir-bullet-network-camera-comtalk-I6348897-2007-01-Sale-I.htm', '4MP outdoor IP camera, RM199 listing.'),
          ('Hikvision 4MP, Lapasar', 'https://mall.lapasar.com/office-management/it-electronics/products/hikvision-ds-2cd2046g2-iusl-4mp/121', 'About RM750 per unit; B2B listing.'),
          ('Manitou Springs reservation minutes', 'https://www.manitouspringsco.gov/DocumentCenter/View/2688/FIRS-Update-Meeting-Minutes-September-16-2020', 'One city system: 31% weekly no-show. Directional only.'),
          ('Campground reservation policy brief', 'https://jonathan-e-hughes.github.io/policy-briefs/campground-reservations.html', 'Modelled 10.2% no-show; fees reduce unused bookings.'),
          ('Car rental no-show analysts', 'https://www.autorentalnews.com/articles/charging-for-no-shows-could-improve-profits', '20–30% no-shows, analyst estimate; not parking.'),
          ('ATRI truck-parking survey', 'https://www.truckinginfo.com/news/truckers-like-reserved-parking-but-not-paying-for-it', 'Almost half would refuse to pay for reserved parking; different population.')]
src_cost = src_v3[:9] + src_v3[11:13]; src_v3 = src_v3[9:11] + src_v3[13:]
D['a-sources-v3'] = compact('a-sources-v3', 'Added sources', 'Added sources for V3 (secondary, directional)',
    '<div class="cols"><div class="col">' + ''.join(f'<article class="g2-source-entry"><b><a href="{u}">{t}</a></b><p>{p}</p></article>' for t, u, p in src_v3[:3])
    + '</div><div class="col">' + ''.join(f'<article class="g2-source-entry"><b><a href="{u}">{t}</a></b><p>{p}</p></article>' for t, u, p in src_v3[3:]) + '</div></div>',
    'Found by web search; pages were not opened for this version. Open and verify each before submission. None of these measures KLGCC demand or price response.')
D['a-sources-cost'] = compact('a-sources-cost', 'Cost sources', 'Sources for the cost model',
    '<div class="cols"><div class="col">' + ''.join(f'<article class="g2-source-entry"><b><a href="{u}">{t}</a></b><p>{p}</p></article>' for t, u, p in src_cost[:6])
    + '</div><div class="col">' + ''.join(f'<article class="g2-source-entry"><b><a href="{u}">{t}</a></b><p>{p}</p></article>' for t, u, p in src_cost[6:]) + '</div></div>',
    'Opened and checked: Payscale, AWS, Customs guide, MIDA, Cantabria notes. The others were not opened or are script-rendered; verify before submission. Effort days, cable run and labour remain assumptions.')


# ---------------------------------------------------------------- compose

# ------------------------------------------------------------------ native charts (SVG, numbers from the model)
NAVY, RED, STEEL = '#102a43', '#b71c1c', '#6b8fb3'

def _axes(W, H, L, R, T, B, X, Y, xt, yt, xfmt, yfmt, xtitle, ytitle):
    o = []
    for v in yt:
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#e3e8f0" stroke-width="1"/>')
        o.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" class="ax">{yfmt(v)}</text>')
    for v in xt:
        o.append(f'<text x="{X(v):.1f}" y="{H-B+20}" text-anchor="middle" class="ax">{xfmt(v)}</text>')
    o.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" text-anchor="middle" class="ax">{xtitle}</text>')
    o.append(f'<text transform="translate(13 {(T+H-B)/2:.0f}) rotate(-90)" text-anchor="middle" class="ax">{ytitle}</text>')
    return o

def rev_chart():
    W, H, L, R, T, B = 760, 420, 62, 168, 14, 44
    xmax, ymin, ymax = 120, -20000, 120000
    X = lambda n: L + (W - L - R) * n / xmax
    Y = lambda v: T + (H - T - B) * (ymax - v) / (ymin * -1 + ymax)
    k = lambda v: f'{"−" if v < 0 else ""}{abs(v)//1000}k'
    o = [f'<svg class="v3-ch" viewBox="0 0 {W} {H}" role="img" aria-label="Annual contribution against accepted bookings per day, for 30, 50 and 70 percent member share. At 50 percent members, running cost is covered at {be_op:.0f} bookings a day and capital is recovered in 5 years at {be_5:.0f} and in 3 years at {be_3:.0f}.">']
    o += _axes(W, H, L, R, T, B, X, Y, range(0, 121, 20), range(-20000, 120001, 20000), lambda v: str(v), k, 'Accepted bookings per day', 'Annual contribution, RM')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{NAVY}" stroke-width="1.5"/>')
    o.append(f'<text x="{W-R-4}" y="{Y(0)+15:.1f}" text-anchor="end" class="ref0">running cost covered</text>')
    for v, name in ((CAPEX / 5, '5-year recovery'), (CAPEX / 3, '3-year recovery')):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{RED}" stroke-width="1.2" stroke-dasharray="5 4"/>')
        o.append(f'<text x="{W-R-4}" y="{Y(v)-5:.1f}" text-anchor="end" class="ref">{name} · RM{v/1000:.1f}k</text>')
    for sh, col, lab in ((30, STEEL, '30% members'), (50, RED, '50% members'), (70, NAVY, '70% members')):
        pts = ' '.join(f'{X(n):.1f},{Y(contrib(n, sh)):.1f}' for n in range(0, 121, 2))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><title>{lab}: RM{contrib(rows_n[0],sh)/1000:.1f}k at {rows_n[0]:.0f}/day, RM{contrib(rows_n[2],sh)/1000:.1f}k at {rows_n[2]:.0f}/day</title></polyline>')
        ye = Y(contrib(120, sh))
        o.append(f'<circle cx="{W-R+10}" cy="{ye:.1f}" r="5" fill="{col}"/><text x="{W-R+20}" y="{ye+4.5:.1f}" class="lab">{lab}</text>')
    for n, v in ((be_op, 0), (be_5, CAPEX / 5), (be_3, CAPEX / 3)):
        o.append(f'<circle cx="{X(n):.1f}" cy="{Y(v):.1f}" r="6" fill="{RED}" stroke="#fff" stroke-width="2"><title>{n:.0f} bookings/day at 50% members</title></circle>')
    o.append('</svg>')
    return ''.join(o)

def val_chart():
    """Number line: extra eligible tenant sales that close the annual gap; labels step up like a staircase so none overlap."""
    W, H, L, Rr = 760, 316, 40, 40
    xmax = math.ceil(gto_hi * 1.12 / 25000) * 25000
    X = lambda v: L + (W - L - Rr) * v / xmax
    AY = 240
    o = [f'<svg class="v3-ch" viewBox="0 0 {W} {H}" role="img" aria-label="Extra eligible tenant sales needed to close the RM{gap/1000:.1f}k annual gap: RM{gto_lo/1000:.0f}k at a 15 percent rent clause, RM{gap/.10/1000:.0f}k at 10 percent and RM{gto_hi/1000:.0f}k at 5 percent.">']
    o.append(f'<text x="{L}" y="18" class="ax">Extra sales needed = RM{gap/1000:.1f}k annual gap ÷ rent clause</text>')
    o.append(f'<rect x="{X(gto_lo):.1f}" y="{AY-14}" width="{X(gto_hi)-X(gto_lo):.1f}" height="28" rx="4" fill="{RED}" opacity=".12"/>')
    o.append(f'<line x1="{L}" x2="{W-Rr}" y1="{AY}" y2="{AY}" stroke="{NAVY}" stroke-width="2"/>')
    for v in range(0, int(xmax) + 1, 25000):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{AY-5}" y2="{AY+5}" stroke="{NAVY}" stroke-width="1.5"/><text x="{X(v):.1f}" y="{AY+28}" text-anchor="middle" class="ax">{v//1000}k</text>')
    o.append(f'<text x="{(X(gto_lo)+X(gto_hi))/2:.1f}" y="{AY+52}" text-anchor="middle" class="ref">break-even range RM{gto_lo/1000:.0f}k – RM{gto_hi/1000:.0f}k</text>')
    o.append(f'<text x="{(L+W-Rr)/2:.0f}" y="{H-4}" text-anchor="middle" class="ax">Extra eligible tenant sales a year, RM</text>')
    BW, BH = 138, 56
    for (rate, col, ink), top in zip(((.15, NAVY, NAVY), (.10, '#3d5f82', '#3d5f82'), (.05, STEEL, '#4a6f94')), (160, 98, 36)):
        v = gap / rate; x = X(v)
        bx = min(max(x - BW / 2, 2), W - BW - 2)
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top+BH}" y2="{AY-8}" stroke="{col}" stroke-width="2"/>')
        o.append(f'<rect x="{bx:.1f}" y="{top}" width="{BW}" height="{BH}" rx="9" fill="#fff" stroke="{col}" stroke-width="2.2"/>')
        o.append(f'<text x="{bx+BW/2:.1f}" y="{top+19}" text-anchor="middle" class="ax">{rate*100:.0f}% rent clause</text>')
        o.append(f'<text x="{bx+BW/2:.1f}" y="{top+44}" text-anchor="middle" class="dp-v" fill="{ink}">RM{v/1000:.0f}k</text>')
        o.append(f'<circle cx="{x:.1f}" cy="{AY}" r="8" fill="{col}" stroke="#fff" stroke-width="2.5"><title>RM{v/1000:.0f}k extra sales at a {rate*100:.0f}% clause</title></circle>')
    o.append('</svg>')
    return ''.join(o)

def donut(items, total, size=250, r=84, sw=40, label='upfront'):
    import math
    C = 2 * math.pi * r; cx = cy = size / 2
    o = [f'<svg class="v3-donut" viewBox="0 0 {size} {size}" role="img" aria-label="Upfront cost split of RM{total:,}: ' + ', '.join(f'{n} {v/total*100:.0f}%' for n, v, c in items) + '">']
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#eef1f5" stroke-width="{sw}"/>')
    acc = 0
    for n, v, col in items:
        L_ = v / total * C
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-dasharray="{max(L_-3,0):.1f} {C-max(L_-3,0):.1f}" stroke-dashoffset="{-acc:.1f}" transform="rotate(-90 {cx} {cy})"><title>{n}: RM{v:,} ({v/total*100:.0f}%)</title></circle>')
        acc += L_
    o.append(f'<text x="{cx}" y="{cy-2 if label else cy+7}" text-anchor="middle" class="dn">RM{total/1000:.1f}k</text>{("<text x=" + chr(34) + str(cx) + chr(34) + " y=" + chr(34) + str(cy+20) + chr(34) + " text-anchor=" + chr(34) + "middle" + chr(34) + " class=" + chr(34) + "ds" + chr(34) + ">" + label + "</text>") if label else ""}</svg>')
    return ''.join(o)

# ---- revenue: break-even curve replaces the contribution table
D['revenue'] = new('revenue', 'Booking revenue model', 'Business', 'false', '', 'Revenue depends on who books.',
    f"""<div class="v3-rev v3-rev--chart">
<section><h3 class="module-title red">What one booking adds to the mall</h3>
<table class="v3-tbl"><thead><tr><th></th><th>Weekday</th><th>Weekend</th></tr></thead><tbody><tr><th scope="row">Non-member or no-show</th><td><b>RM4</b></td><td><b>RM5</b></td></tr><tr><th scope="row">Member, up to 3 hours</th><td><b>RM1</b></td><td><b>RM2</b></td></tr><tr><th scope="row">Member, over 3 hours</th><td><b>RM1</b></td><td><b>RM0</b></td></tr></tbody></table>
<p class="v3-note">Booking fee RM4 weekday, RM5 weekend. A member’s fee is credited to the parking bill, so only any excess counts. A no-show pays the fee, like a non-member.</p></section>
<section><h3 class="module-title red">Annual contribution by volume and member share</h3>{rev_chart()}
<p class="v3-note">After 6% SST, 20% operator share, card fees and RM10.5k running cost.</p></section></div>
<div class="v3-sowhat"><span>So what</span><p>At 50% members, about <b>{be_op:.0f} bookings a day</b> cover running cost, <b>{be_5:.0f}</b> recover the capital in 5 years and <b>{be_3:.0f}</b> in 3. Capacity is not the limit: <b>demand and willingness to pay are</b>.</p></div>""",
    'Contribution = accepted bookings × gross per booking × 365 × net factor − running cost, from the 200-bay simulation. Volume and member share are scenarios; the 20% operator share is unagreed. Derivation: appendix.')

# ---- value: rent-versus-sales chart replaces the big numbers
bar = lambda pct, col: f'<span class="vz-track"><i style="width:{min(pct,100):.1f}%;background:{col}"></i></span>'
D['value'] = new('value', 'Value to SDP', 'Business', 'false', '', 'For SDP the bar is low.',
    f"""<div class="vz"><section class="vz-main vz-card"><h3 class="module-title red">Extra rent from extra eligible tenant sales</h3>{val_chart()}
<div class="vz-box"><b>RM{gap/1000:.1f}k a year</b> is the gap to close.<small>Low-volume case: ≈{rows_n[0]:.0f} bookings/day, 50% members. Extra rent = extra sales × the lease’s rent rate.</small></div></section>
<div class="vz-side"><section class="vz-card"><h3 class="module-title">Voucher break-even · share of holders who must return</h3>
<div class="vz-row"><span>5% clause</span>{bar(vo_5*100, STEEL)}<b>{vo_5*100:.0f}%</b></div><div class="vz-row"><span>15% clause</span>{bar(vo_15*100, NAVY)}<b>{vo_15*100:.0f}%</b></div>
<p class="vz-note">A free booking for qualifying spend pays back if <b>1 in {1/vo_5:.0f} (5% clause) to 1 in {1/vo_15:.0f} (15%)</b> makes a visit they would not otherwise make.</p></section>
<section class="vz-card"><h3 class="module-title">Spend gap · association only</h3>
<div class="vz-row"><span>1–2 visits / month</span>{bar(195/327*100, '#9aa8bb')}<b>RM195</b></div><div class="vz-row"><span>5+ visits / month</span>{bar(100, RED)}<b>RM327</b></div>
<p class="vz-note">Recalled trip spend, +68%. Association only, not proof that parking causes it.</p></section></div></div>
<div class="v3-sowhat"><span>Caveat</span><p>Gross turnover rent has a floor: extra sales below it add <b>zero</b> rent. Count it tenant by tenant, and net out vouchers, support and displacement before calling it profit.</p></div>""",
    f'Gap = RM{CAPEX/1000:.1f}k ÷ 5 − RM{low/1000:.1f}k contribution. Sales needed = gap ÷ rent rate. Sources: <a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026">Vase.ai (N=500)</a>; <a href="https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32">Tropicana lease terms</a>; <a href="https://www.simedarbyproperty.com/sites/default/files/2024-05/Reply%20Letter%20to%20MSWG%20%2817052024%29.pdf">SDP reply to MSWG</a>. No SDP-specific rent rate or retention effect is claimed. Derivation: appendix.')

# ---- cost: donut + legend replaces the bar list
slices = [('Software and integration', INTEGRATION, RED, 'a', f'RM{DAY_RATE:.0f}/day × {BUILD_DAYS:.0f} days; quote before G1'),
          ('Blind-spot CCTV, 4 cameras', N_CAM * CAM, NAVY, 'a', f'RM{CAM:,} each; quote after survey'),
          ('Power, network and works', 7_500, STEEL, 'a', 'Allowance; survey firms it up'),
          ('Guidance display (optional)', 2_033, '#c5ced9', 's', 'Viskou list price, tax extra')]
leg = ''.join(f'<li><i style="background:{c}"></i><div><b>{n}</b><small>{d}</small></div><span>RM{v:,}{S if t=="s" else ""}</span></li>' for n, v, c, t, d in slices)
leg += f'<li class="v3-zero"><i></i><div><b>LPR cameras</b><small>Existing at KLGCC; RM3,226 each if absent</small></div><span>RM0{S}</span></li>'
D['cost'] = new('cost', 'KLGCC zone cost', 'Business', 'false', '', f'KLGCC zone: RM{CAPEX/1000:.1f}k upfront, RM10.5k a year.',
    f"""<div class="v3-cost"><section><h3 class="module-title red v4-band"><b>CAPEX</b><span>One-time, upfront investment</span></h3>
<p class="v3-note v3-frame">Marked items have a published price; the rest are assumptions the site survey and a vendor quote will replace.</p>
<div class="v3-donutrow">{donut([(n, v, c) for n, v, c, t, d in slices], CAPEX, label='')}<ul class="v3-dleg">{leg}</ul></div>
<div class="v3-total"><span>Total upfront</span><b>RM{CAPEX:,}</b><em>range RM{CAPEX_LO/1000:.1f}k to RM{CAPEX_HI/1000:.1f}k (high: 10 cameras, +{OVERRUN*100:.0f}% overrun)</em></div>
<p class="v4-unpriced"><b>Not yet priced</b> gate work and equipment SST.</p></section>
<aside><h3 class="module-title red v4-band"><b>OPEX</b><span>Recurring, every year</span></h3>
<p class="v3-note v3-frame">Hosting is priced; maintenance is 15% of the build estimate, so it moves with it.</p>
<div class="v3-runrow">{donut([('Maintenance', int(MAINT_RATE*INTEGRATION), RED), ('Hosting', HOSTING, NAVY)], RUN, size=210, r=72, sw=34, label='')}<ul class="v3-dleg v3-dleg--s"><li><i style="background:{RED}"></i><div><b>Maintenance</b><small>15% of the build a year</small></div><span>RM{int(MAINT_RATE*INTEGRATION):,}</span></li><li><i style="background:{NAVY}"></i><div><b>Hosting</b><small>2 servers, AWS Malaysia, 24×7</small></div><span>RM{HOSTING:,}{S}</span></li></ul></div><div class="v3-total"><span>Total running</span><b>RM{RUN:,} a year</b><em>maintenance 15% of the build, plus hosting</em></div>
<p class="v4-unpriced"><b>Not yet priced</b> central support.</p></aside></div>
<div class="v3-sowhat"><span>So what</span><p>Integration is <b>{INTEGRATION/CAPEX*100:.0f}% of upfront cost</b> and is an effort estimate, not a quote: that is the biggest risk. A pilot-scope build is about <b>RM{PILOT_BUILD/1000:.0f}k</b>.</p></div>""",
    'Later malls pay site integration only; the platform build is paid once. Sources: <a href="https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows">Viskou display</a>; <a href="https://mall.lapasar.com/office-management/it-electronics/products/hikvision-ds-2cd2046g2-iusl-4mp/121">Hikvision 4MP</a>; <a href="https://www.payscale.com/research/MY/Job=Senior_Software_Developer/Salary">Payscale</a>; <a href="https://aws-pricing.com/ap-southeast-5.html">AWS Malaysia</a>. Effort days, cable run and labour are assumptions. Who funds the build is not yet agreed: these are zone costs, not a quote. Derivation: appendix.')

LABELS = {'team': 'The team', 'problem': 'Problem statement', 'alternatives': 'Market context', 'service': 'Introducing ParkFlow', 'member': 'Prototype demo',
          'operator': 'Operator view', 'admission': 'Capacity guard', 'paths': 'Pricing and retention', 'revenue': 'Commercial model',
          'value': 'Value to SDP', 'cost': 'Cost per zone', 'integration': 'Site readiness', 'pilot-design': 'Pilot plan', 'decision': 'Next steps'}
TITLES = {'team': 'Five students, <em>one pilot proposal.</em>', 'problem': 'Parking uncertainty can cost malls <em>planned visits.</em>',
          'alternatives': 'Existing programmes leave <em>capacity efficiency</em> open.',
          'service': 'A reservation service for one <em>parking zone.</em>',
          'member': 'Customer journey: <em>reserve, enter, park.</em>',
          'operator': 'One operator view of <em>capacity and exceptions.</em>',
          'admission': 'Forecasts plan; <em>observed capacity decides.</em>',
          'paths': 'Two paths to a bay, <em>one loyalty loop.</em>',
          'revenue': 'Revenue depends on <em>who books.</em>',
          'value': 'For SDP the bar is <em>low</em>; the evidence is <em>directional.</em>',
          'cost': f'KLGCC zone: <em>RM{CAPEX/1000:.1f}k upfront</em>, RM10.5k a year.',
          'integration': 'What the site <em>must confirm</em> before the pilot.',
          'pilot-design': 'Eight weeks: <em>prepare, reserve, shadow, decide.</em>',
          'decision': 'The ask: <em>one survey, one pilot.</em>'}
DECO = ('<div class="dcbands" aria-hidden="true"><i></i><i></i><i></i></div><div class="dctri" aria-hidden="true"></div>'
        '<div class="dcbar">' + WORDMARK + '<i aria-hidden="true"></i><span>LABEL</span></div>')

# capacity guard, rebuilt natively: one verified capacity, a buffer that flexes with demand
cells = ['o'] * 50 + ['c'] * 18 + ['s'] * 2 + ['f'] * 30
waffle = ''.join(f'<i class="{c}"></i>' for c in cells)
def alloc_row(name, sub, held, tone):
    return (f'<div class="cg-row cg-row--{tone}"><div class="cg-row__n"><b>{name}</b><span>{sub}</span></div>'
            f'<div class="cg-bar"><i class="h" style="width:{held/30*100:.1f}%">{held}</i><i class="w">{30-held}</i></div>'
            f'<div class="cg-row__v"><b>{held}</b> held for bookings<br/><b>{30-held}</b> open to walk-ins</div></div>')
D['admission'] = new('admission', 'Capacity guard', 'Product', 'false', '', 'One verified capacity.',
    f"""<div class="cg"><section class="cg-zone"><h3>Zone right now <small>illustrative · 100 bays shown</small></h3>
<div class="cg-waffle" role="img" aria-label="100 bays: 50 occupied, 18 accepted claims, 2 safety bays, 30 free">{waffle}</div>
<dl class="cg-leg"><div><dt><i class="o"></i>Occupied</dt><dd>50</dd></div><div><dt><i class="c"></i>Accepted claims</dt><dd>18</dd></div><div><dt><i class="s"></i>Safety bays</dt><dd>2</dd></div><div class="cg-free"><dt><i class="f"></i>Free</dt><dd>30</dd></div></dl></section>
<section class="cg-right"><div class="cg-steps">
<div><span>Observed now · decides</span><b>LPR counts and plate ledger</b><p>Every admission is checked against verified free bays.</p></div>
<div><span>Recent traffic · sets the buffer</span><b>Booking requests, last 30 min</b><p>Refreshed every 15 minutes.</p></div>
<div class="opt"><span>Forecast · optional input</span><b>Expected requests, next 3 h</b><p>Tested against the simple rule in the pilot.</p></div></div>
<h3 class="cg-h">Allocation of the 30 free bays as demand changes</h3>
{alloc_row('Quiet', 'about 2 booking requests in 30 min', 3, 'q')}
{alloc_row('Normal', 'about 4 requests in 30 min', 6, 'n')}
{alloc_row('Surge', '7 or more requests in 30 min', 10, 's')}
<p class="cg-key"><i class="h"></i>Held for bookings (the buffer) <i class="w"></i>Open to walk-ins</p></section></div>
<div class="v3-sowhat"><span>The rule</span><p>Bookings take any verified free bay. Walk-ins only get bays <b>above the buffer</b>, and the buffer follows demand. Only verified free bays become promises.</p></div>""",
    'Illustrative numbers. Buffer = recent booking requests per hour × 45-minute hold, between a floor of 2 bays and a cap of 10% of the zone (see appendix). In the 200-bay simulation a buffer of about 5 accepted every booking at ~76 requests/day (synthetic demand). Forecasts inform the plan; they never create an available bay.')
TITLES['admission'] = 'One verified capacity. A buffer that <em>flexes with demand.</em>'

# appendix: the buffer rule
D['a-buffer'] = compact('a-buffer', 'How the buffer follows demand', 'How the buffer follows demand',
    """<div class="cols"><div class="col"><h3 class="module-title">The rule, refreshed every 15 minutes</h3>
<p class="v3-formula">B = clamp( requests per hour × hold time , floor , cap )</p>
<ul><li><b>Requests per hour:</b> booking requests in the last 30 minutes, doubled and smoothed.</li>
<li><b>Hold time:</b> about 45 minutes, how long a held bay waits to be claimed.</li>
<li><b>Floor and cap:</b> 2 bays, and 10% of the zone (10 bays at 100, 20 at 200).</li>
<li><b>Free bays</b> = total − occupied − accepted claims − safety bays.</li></ul>
<h3 class="module-title">Worked example · 100-bay zone, B = 6</h3>
<table><thead><tr><th>Free bays</th><th>Walk-in arrives</th><th>Booking request arrives</th></tr></thead><tbody>
<tr><td>16</td><td>Admitted (16 &gt; 6)</td><td>Accepted</td></tr><tr><td>7</td><td>Admitted (7 &gt; 6)</td><td>Accepted</td></tr>
<tr><td>6</td><td>Turned away</td><td>Accepted</td></tr><tr><td>0</td><td>Turned away</td><td>Rejected</td></tr></tbody></table></div>
<div class="col"><h3 class="module-title">B at three demand levels (illustrative)</h3>
<table><thead><tr><th>Demand</th><th>Requests, last 30 min</th><th>Calculated</th><th>Buffer</th></tr></thead><tbody>
<tr><td>Quiet</td><td>2</td><td>3</td><td>3</td></tr><tr><td>Normal</td><td>4</td><td>6</td><td>6</td></tr><tr><td>Surge</td><td>7 or more</td><td>10.5</td><td>10 (cap)</td></tr></tbody></table>
<h3 class="module-title">What a forecast changes</h3>
<p>Only the input. It replaces last-30-minute requests with expected requests for the next hours, so the buffer can rise before a surge. In the offline study this did not beat reacting to recent traffic, so the pilot tests it in shadow mode against this rule.</p>
<h3 class="module-title">Measured in the pilot</h3>
<p>Booking rejection rate, idle bay-hours (free bays while a walk-in is turned away), and walk-ins admitted. The floor, cap and hold time are calibrated on the baseline counts.</p></div></div>""",
    'Rule and numbers are a design proposal; the demand levels are illustrative. Evidence: <a href="../analysis/benchmarks/decision_value/report.md">event-driven report</a> and <a href="../analysis/v3_zone200.py">200-bay simulation</a> (synthetic demand).')

# ---- capacity slide, rebuilt around the rolling plan: look three hours ahead, re-plan every 15 minutes
def rh_chart():
    W, H, L, R, T, B = 700, 330, 40, 110, 44, 44
    mmax, ymax = 180, 40
    X = lambda m: L + (W - L - R) * m / mmax
    Y = lambda v: T + (H - T - B) * (ymax - v) / ymax
    hhmm = lambda m: f'{9 + m // 60}:{m % 60:02d}'
    bookings = [3, 5, 7, 10, 15, 21, 27]; walkins = [10, 13, 17, 22, 25, 28, 31]; leaving = [4, 9, 15, 20, 22, 19, 17]
    o = [f'<svg class="v3-ch" viewBox="0 0 {W} {H}" role="img" aria-label="Illustrative three-hour plan made at 9:00: expected bookings rise toward noon, expected walk-ins rise, and expected departures of cars already parked peak mid-morning. The plan is refreshed every 15 minutes.">']
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="#9aa8bb" stroke-width="1.2"/>')
    o.append(f'<text x="{L-8}" y="{Y(0)+4:.1f}" text-anchor="end" class="ax">low</text><text x="{L-8}" y="{Y(ymax)+4:.1f}" text-anchor="end" class="ax">high</text>')
    for m in range(0, 181, 30):
        o.append(f'<text x="{X(m):.1f}" y="{H-B+22}" text-anchor="middle" class="tm">{hhmm(m)}</text>')
    o.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-6}" text-anchor="middle" class="ax">Expected vehicles per 30 minutes (illustrative)</text>')
    o.append(f'<rect x="{X(120):.1f}" y="{T}" width="{X(180)-X(120):.1f}" height="{H-T-B}" fill="{RED}" opacity=".07"/><text x="{(X(120)+X(180))/2:.1f}" y="{T+16}" text-anchor="middle" class="ref">booking peak</text>')
    for m in range(0, 181, 15):
        o.append(f'<line x1="{X(m):.1f}" x2="{X(m):.1f}" y1="{T-16}" y2="{T-8}" stroke="{NAVY}" stroke-width="1.5"/>')
    o.append(f'<text x="{L}" y="{T-24}" class="ref0">plan made at 9:00, re-planned every 15 minutes (ticks)</text>')
    for vals, col, dash, lab in ((walkins, STEEL, '', 'Expected walk-ins'), (bookings, RED, '', 'Expected bookings'), (leaving, NAVY, '6 4', 'Expected departures')):
        pts = ' '.join(f'{X(i*30):.1f},{Y(v):.1f}' for i, v in enumerate(vals))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="{dash}"><title>{lab}</title></polyline>')
        for i, v in enumerate(vals):
            o.append(f'<circle cx="{X(i*30):.1f}" cy="{Y(v):.1f}" r="3.6" fill="{col}" stroke="#fff" stroke-width="1.5"><title>{lab}, {hhmm(i*30)}</title></circle>')
        ye = Y(vals[-1])
        o.append(f'<text x="{W-R+10}" y="{ye+4.5:.1f}" class="lab">{lab.replace("Expected ", "")}</text>')
    o.append('</svg>')
    return ''.join(o)

CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>'
def rh_row(time, text, occ, held, free, note, last=False):
    h = int(time.split(':')[0]); mer = 'PM' if h == 12 or h < 8 else 'AM'
    return (f'<div class="rh-row{" rh-last" if last else ""}"><div class="rh-time">{CLOCK}<b>{time}</b><small>{mer}</small></div>'
            f'<div class="rh-body"><b>{text}</b><div class="rh-bar"><i class="o" style="width:{occ}%"></i><i class="h" style="width:{held}%"><em>{held} held</em></i><i class="f" style="width:{free}%"></i></div></div></div>')

D['admission'] = new('admission', 'Adaptive capacity', 'Product', 'false', '', 'An adaptive plan.',
    f"""<div class="rh"><section class="rh-left"><h3 class="module-title red">What the plan looks at</h3>{rh_chart()}
<div class="rh-in"><span>Inputs, every 15 minutes</span><ul><li>Expected bookings</li><li>Expected walk-ins</li><li>Expected departures, from the plate ledger</li><li>Verified free bays and accepted claims</li></ul></div></section>
<section class="rh-right"><h3 class="module-title red">How the 100 bays are split over time <small>illustrative</small></h3>
{rh_row('9:00', 'Most walk-ins now will leave before noon, so admit them.', 30, 10, 60, 'Wide walk-in allowance')}
{rh_row('10:30', 'Bookings are building, so hold more bays back.', 55, 20, 25, 'Held bays grow')}
{rh_row('12:00', 'Held bays are ready for the booking peak.', 72, 18, 10, 'Peak served', last=True)}
<p class="rh-key"><i class="o"></i>Occupied <i class="h"></i>Held for bookings <i class="f"></i>Open to walk-ins</p></section></div>
<div class="v3-sowhat"><span>Pilot test</span><p>Verified capacity still decides every admission; the plan only sets how many bays to hold back. Tested against a fixed buffer on <b>rejected bookings at peak, idle bay-hours and walk-ins admitted</b>.</p></div>""",
    'Illustrative, not measured. In the offline simulation (synthetic demand) the three-hour plan did not beat a fixed 5-bay buffer, so the pilot runs it in shadow mode first. Forecasts inform the plan; they never create an available bay. Rule and calibration: appendix.')
TITLES['admission'] = 'An adaptive plan: <em>three hours ahead, every 15 minutes.</em>'
LABELS['admission'] = 'Adaptive capacity'

# ---- site readiness as an evidence matrix
def sr_photos(items):
    return ''.join(f'<figure><img alt="{c}" src="assets/{f}.webp" style="object-position:{p}"/><figcaption>{c}</figcaption></figure>' for f, c, p in items)
_I = lambda p_: f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{p_}</svg>'
SR_DB = _I('<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>')
SR_AIM = _I('<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>')
SR_CAR = _I('<path d="M5 16v-5l2-5h10l2 5v5M3 16h18M7 16v2M17 16v2"/><circle cx="8" cy="13.2" r="1"/><circle cx="16" cy="13.2" r="1"/>')
SR_MON = _I('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>')
SR_SUN = _I('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>')
SR_USERS = _I('<circle cx="9" cy="8" r="3"/><path d="M3 20v-1a6 6 0 0 1 12 0v1"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14a5 5 0 0 1 4 5v1"/>')
SR_SYNC = _I('<path d="M20 11a8 8 0 0 0-14-4M4 5v4h4M4 13a8 8 0 0 0 14 4M20 19v-4h-4"/>')
SR_CLOCK = _I('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>')
SR_CHECK = _I('<path d="M5 12l5 5 9-10"/>')
def sr_row(n, title, q, why, photos, observed, confirm, plan=('weeks 1–2', '')):
    items = ''.join(f'<li><span class="sr-ic">{ic}</span><span><b>{t}</b>' + (f'<small>{sub}</small>' if sub else '') + '</span></li>' for ic, t, sub in confirm)
    return (f'<article class="sr-row"><div class="sr-ph sr-ph--{len(photos)}">{sr_photos(photos)}</div>'
            f'<div class="sr-title"><span class="sr-n">{n}</span><h3>{title}</h3></div>'
            f'<div class="sr-obs"><span class="sr-pill sr-pill--ok"><i class="sr-tick">{SR_CHECK}</i>Observed 9 Nov</span><p>{observed}</p></div>'
            f'<div class="sr-tbc"><span class="sr-pill sr-pill--tbc"><i>!</i>Confirm in {plan[0]}</span><ul>{items}</ul><div class="sr-foot"><p><b>Proposed pass test</b>{plan[1]}</p></div></div></article>')
D['integration'] = new('integration', 'Site readiness', 'Product', 'false', '', 'What the site must confirm.',
    '<div class="sr"><h4 class="mc-tab sr-head"><span>Site visit at KLGCC Mall, 9 Nov 2026</span><em>Team Hexa on site: photos and a customer-service interview. <b>No capex before gate G1;</b> if a check fails, scope shrinks first.</em></h4>'
    + sr_row('01', 'Zone counts from LPR', 'Can the existing level LPR give reconciled entry and exit events and a plate ledger?',
             'the capacity guard needs a verified zone count.',
             [('klgcc-visit-entry-barrier', 'Entry barrier and LPR', '55% 55%')],
             'LPR at the entry barrier', [(SR_DB, 'Data and API access', 'Vendor, API or export'), (SR_AIM, 'Read accuracy', 'Share of plates read correctly'), (SR_CAR, 'Zone count', 'Entry and exit events, plate ledger')], ('weeks 1–2', 'Counts match a manual count over one full day.'))
    + sr_row('02', 'Camera coverage', 'Do the existing cameras cover the aisles, and where are the blind spots?',
             'CCTV is an audit layer; add cameras only where gaps are found.',
             [('klgcc-visit-cctv-aisle', 'Aisle camera', '50% 30%'), ('klgcc-visit-cctv-ceiling', 'Ceiling camera', '50% 45%'), ('klgcc-visit-camera-check', 'Mapping positions', '50% 35%')],
             'Aisle and ceiling cameras', [(SR_MON, 'Blind spots', 'Coverage gaps'), (SR_DB, 'Footage access', 'Access and retention period'), (SR_SUN, 'Glare and pillars', 'Light and obstructions')], ('weeks 1–4', 'Every aisle covered, or gaps mapped and priced.'))
    + sr_row('03', 'Member and payment systems', 'Can member identity, payment and booking expiry connect to the controller?',
             'one valid admission decision and a traceable exception path.',
             [('klgcc-visit-rates-board', 'Posted rates and payments', '60% 35%'), ('klgcc-visit-staff-interview', 'Customer-service interview', '50% 30%')],
             'Card and e-wallet payment, posted rates', [(SR_USERS, 'Member API', 'Membership identity'), (SR_SYNC, 'Settlement', 'Refunds and no-shows'), (SR_CLOCK, 'Booking expiry', 'Link to the controller')], ('weeks 1–2', 'Member lookup, payment and refund work in a test account.'))
    + '</div>',
    'Sources: <a href="https://www.simedarbyproperty.com/malls/klgcc-mall/">KLGCC Mall: official parking information</a>. Observed items are Team Hexa site-visit observations (9 Nov 2026), not mall-confirmed. Confirm controller, power/network, gate safety, local coverage and incumbent interfaces.')
TITLES['integration'] = 'Three site checks come <em>before any capex</em>'

# ---- pilot slide now carries the ask
D['pilot-design'] = D['pilot-design'].replace('<em>Month-6 review</em>', '<em>Month-6 review, then other SDP malls</em>', 1)
D['pilot-design'] = D['pilot-design'].replace('</div><div class="source">',
    '<div class="v3-ask"><span>The ask</span><p>Nominate a KLGCC sponsor and operator counterpart, and enable the site survey, integration talks and baseline counts. <b>Reference upfront RM' + f'{CAPEX/1000:.1f}' + 'k</b> (range RM' + f'{CAPEX_LO/1000:.1f}–{CAPEX_HI/1000:.1f}' + 'k) plus RM10.5k a year. Pilot-scope software build alone: about <b>RM' + f'{PILOT_BUILD/1000:.0f}' + 'k</b> (assisted service, no barrier integration).</p></div></div><div class="source">', 1)
# pilot slide: Gantt replaces the phase arrows, cards and lane bars
def gantt():
    rows = [('n', 'Member baseline, price and voucher arms', 'Loyalty', 1, 2), ('n', 'LPR counts, integration, guard readiness', 'Operator · IT', 1, 2),
            ('f', 'Installed scope and net capture', 'Finance', 1, 4), ('r', 'Controlled reservations, fixed buffer', 'Operator · Loyalty', 3, 6),
            ('r', 'Assisted service and incident log', 'Operator', 3, 8), ('b', 'Optimizer shadow replay on real events', 'Team · Operator', 5, 6),
            ('f', 'Cost and investment review', 'Finance', 5, 8), ('n', 'Visits vs control, price and voucher arms', 'Loyalty', 7, 8)]
    h = '<div class="pl-plan"><div class="pl-gantt" role="table" aria-label="Eight-week pilot schedule"><div class="pg-grid"></div><div class="pg-head">Workstream · owner</div>'
    for c, (w, n) in zip(range(2, 10, 2), [('W1–2', 'Prepare'), ('W3–4', 'Reserve'), ('W5–6', 'Shadow AI'), ('W7–8', 'Decide')]):
        h += f'<div class="pg-ph{" pg-ph--ai" if n == "Shadow AI" else ""}" style="grid-column:{c} / span 2"><b>{w}</b>{n}</div>'
    for i in range(1, 9):
        h += f'<div class="pg-wk" style="grid-column:{i+1}">{i}</div>'
    for k, (c, t, o, x, y) in enumerate(rows):
        r = k + 3
        h += f'<div class="pg-lbl" style="grid-row:{r}"><b>{t}</b><small>{o}</small></div><div class="pg-bar pg-bar--{c}" style="grid-row:{r};grid-column:{x+1} / {y+2}"></div>'
    r = len(rows) + 3
    h += f'<div class="pg-lbl pg-lbl--m" style="grid-row:{r}"><b>Decision milestones</b></div>'
    for col, t, al in [(3, 'Reservation readiness', 'm'), (7, 'Live-AI decision', 'm'), (9, 'Scale / extend / stop', 'e')]:
        h += f'<div class="pg-ms pg-ms--{al}" style="grid-row:{r};grid-column:{col}"><i></i><span>{t}</span></div>'
    return h + '</div></div>'
_a = D['pilot-design'].index('<div class="pl-plan">'); _b = D['pilot-design'].index('<div class="v3-gates">')
D['pilot-design'] = D['pilot-design'][:_a] + gantt() + D['pilot-design'][_b:]
TITLES['pilot-design'] = 'The ask: <em>an eight-week pilot at KLGCC.</em>'
LABELS['pilot-design'] = 'Pilot and ask'

# ---- how it works: the parts, and what the customer pays
def _bill(hours, weekend):
    return 3 if not weekend else min(10, 3 if hours <= 3 else 3 + 2 * (hours - 3))
def _price_row(label, weekend, hours):
    if label == '1–3 hours':      # the only stay length where weekday and weekend both apply: slash = weekday / weekend
        return f'<tr><th scope="row">{label}</th><td>RM3</td><td class="mc-mem"><b>RM4 / 5</b></td><td>RM7 / 8</td></tr>'
    fee = 5; b = _bill(hours, True)
    return f'<tr><th scope="row">{label}</th><td>RM{b}</td><td class="mc-mem"><b>RM{max(fee, b)}</b></td><td>RM{fee + b}</td></tr>'
price_rows = ''.join(_price_row(*r) for r in (('1–3 hours', True, 2), ('Weekend 4 h', True, 4), ('Weekend 6 h', True, 6), ('Weekend 7 h+', True, 7)))
def _ic(paths): return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
IC_ID = _ic('<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="9" cy="11" r="2"/><path d="M6.2 15a3 3 0 0 1 5.6 0M16 10h2M16 14h2"/>')
IC_CARD = _ic('<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>')
IC_SERVER = _ic('<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>')
def _img(f, pos): return f'<img alt="" src="assets/{f}.webp" style="object-position:{pos}"/>'
def _node(title, text, tag, kind, vis=''):
    return (f'<div class="mc-node mc-node--{kind}"><div class="mc-vis">{vis}</div><div class="mc-txt"><span class="mc-tag mc-tag--{kind}">{tag}</span>'
            f'<b>{title}</b><p>{text}</p></div></div>')
ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h16M14 6l6 6-6 6"/></svg>'
ARROW2 = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h16M7 6l-6 6 6 6M17 6l6 6-6 6"/></svg>'
D['mechanism'] = new('mechanism', 'How it works and what it costs', 'Product', 'false', '', 'Behind the booking: the parts and the price.',
    f"""<div class="mc"><section class="mc-parts">
<div class="mc-grid"><div class="mc-col"><h4 class="mc-tab"><span>Customer side</span></h4>
{_node('Booking app', 'Book and get a QR pass.', 'New', 'new', _img('proto-confirmed', '50% 62%'))}
{_node('Mall membership', 'Identity and member rate.', 'Existing', 'ex', IC_ID)}
{_node('Payment', 'Fee by card or e-wallet.', 'Existing', 'ex', IC_CARD)}</div>
<div class="mc-arr">{ARROW}{ARROW}{ARROW}</div>
<div class="mc-ctl"><div class="mc-ctl__h"><div class="mc-vis">{IC_SERVER}</div><div><h4>ParkFlow controller</h4><span class="mc-tag mc-tag--new">New</span></div></div>
<ol><li><b>Booking ledger</b>claims and no-shows</li><li><b>Capacity guard</b>verified free bays decide</li><li><b>Buffer plan</b>rolling, every 15 minutes</li><li><b>Price and credit rules</b>fee credited to a member’s bill</li></ol></div>
<div class="mc-arr">{ARROW2}{ARROW2}{ARROW2}</div>
<div class="mc-col"><h4 class="mc-tab"><span>On site</span></h4>
{_node('LPR and barrier', 'Reads plates, admits, counts.', 'Existing', 'ex', _img('klgcc-visit-entry-barrier', '55% 55%'))}
{_node('CCTV', 'Audit only; covers blind spots.', 'Existing', 'ex', _img('klgcc-cctv-crop', '50% 50%'))}
{_node('Operator dashboard', 'Plan, verify, audit.', 'New', 'new', _img('op-overview', '0% 0%'))}</div></div></section>
<section class="mc-price"><h4 class="mc-tab"><span>What the customer pays per visit</span></h4>
<p class="v3-note mc-fee">Booking fee RM4 weekday, RM5 weekend; kept on a no-show. Slashes show weekday / weekend. Weekday parking is RM3 at any length.</p>
<div class="mc-tblwrap"><table class="v3-tbl mc-tbl"><thead><tr><th>Stay</th><th>Normal parking rate</th><th>Member booking</th><th>Non-member booking</th></tr></thead><tbody>{price_rows}</tbody></table></div>
</section></div>
<div class="v3-sowhat"><span>The rule</span><p>A member never pays more than the <b>larger of the fee and the parking bill</b>. A non-member pays <b>both</b>. That gap, RM3–10 a visit, is the reason to join.</p></div>""",
    'KLGCC tariff: RM3 weekday; weekend RM3 for the first 3 hours, then RM2 an hour, capped at RM10, excluding 6% SST (<a href="https://www.simedarbyproperty.com/malls/klgcc-mall/">official page</a>). Weekend hours round up. Booking-service tax is unconfirmed. The member credit is a proposed rule, not an SDP policy. LPR and CCTV are site observations, to be confirmed with the mall.')
TITLES['mechanism'] = 'Behind the booking: <em>the parts and the price.</em>'
LABELS['mechanism'] = 'How it works'

# problem slide: cleaner, consistent stat icons (Lucide-style outlines, same size and stroke)
ICON_OPEN = '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
STAT_ICONS = [
    ICON_OPEN + '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/></svg>',
    ICON_OPEN + '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/><circle cx="18" cy="6" r="4.4" fill="#fff"/><path d="M15 9l6-6"/></svg>',
    ICON_OPEN + '<path d="M8 2v4M16 2v4"/><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18"/><path d="m9 16 2 2 4-4"/></svg>']
_it = iter(STAT_ICONS)
D['problem'] = re.sub(r'(<div class="ps-num">.*?)<svg.*?</svg>', lambda m: m.group(1) + next(_it), D['problem'], flags=re.S)

# service: new 3D whole-level layout with fresh leader lines
D['service'] = D['service'].replace('assets/priority-zone-pilot-concept.png', 'assets/klgcc-zone-3d.webp')
D['service'] = re.sub(r'<svg aria-hidden="true" class="sv-map__lines".*?</svg>',
    '<svg aria-hidden="true" class="sv-map__lines" preserveAspectRatio="none" viewBox="0 0 100 100">'
    '<path d="M17 19 L27 46" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" vector-effect="non-scaling-stroke"></path>'
    '<path d="M17 19 L27 46" fill="none" stroke="#b71c1c" stroke-width="2" vector-effect="non-scaling-stroke"></path>'
    '<ellipse cx="27" cy="46" rx="1.1" ry="1.95" fill="#b71c1c" stroke="#fff" stroke-width="1.5" vector-effect="non-scaling-stroke"></ellipse>'
    '<path d="M60 13 L56.5 33" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" vector-effect="non-scaling-stroke"></path>'
    '<path d="M60 13 L56.5 33" fill="none" stroke="#102a43" stroke-width="2" vector-effect="non-scaling-stroke"></path>'
    '<ellipse cx="56.5" cy="33" rx="1.1" ry="1.95" fill="#102a43" stroke="#fff" stroke-width="1.5" vector-effect="non-scaling-stroke"></ellipse></svg>',
    D['service'], count=1, flags=re.S)
D['service'] = D['service'].replace('Illustrative concept only. Not a surveyed or approved KLGCC floor plan.', 'Illustrative 3D layout of a whole level. Not a surveyed or approved KLGCC floor plan.')
# ===================== V4: align the deck with the commitment architecture (ledger, stay forecast, rolling planner, safety guard) =====================
# main slide carries no simulation numbers; evidence and limits are in the appendix (built from analysis/benchmarks/commitment/*.json)
_chart = (rh_chart().replace('Expected bookings', 'Bookings due').replace('Expected departures', 'Expected departures (stay forecast)')
          .replace('plan made at 9:00, re-planned every 15 minutes (ticks)', 'plan made at 9:00, re-planned every 15 minutes (ticks)'))
D['admission'] = new('admission', 'How capacity is planned', 'Product', 'false', '', 'A booking is a commitment.',
    f"""<div class="rh"><section class="rh-left"><h3 class="module-title red">What the plan looks at</h3>{_chart}
</section>
<section class="rh-right"><h3 class="module-title red">How the 100 bays are split over time <small>illustrative</small></h3>
{rh_row('9:00', 'Most walk-ins now will leave before noon, so admit them.', 30, 10, 60, 'Wide walk-in allowance')}
{rh_row('10:30', 'Bookings are building, so hold more bays back.', 55, 20, 25, 'Held bays grow')}
{rh_row('12:00', 'Held bays are ready for the booking peak.', 72, 18, 10, 'Peak served', last=True)}
<p class="rh-key"><i class="o"></i>Occupied <i class="h"></i>Held for bookings <i class="f"></i>Open to walk-ins</p></section></div>
<div class="v4-strip"><article class="v4-layer"><i>1</i><div><b>Booking ledger</b><p>Confirmed bookings are hard constraints.</p></div></article>
<article class="v4-layer"><i>2</i><div><b>Stay forecast</b><p>Arrivals, departures and overstay risk.</p></div></article>
<article class="v4-layer"><i>3</i><div><b>Rolling planner</b><p>Re-plans every 15 minutes; three-hour lookahead, widened if stays run long.</p></div></article>
<article class="v4-layer"><i>4</i><div><b>Safety guard</b><p>Verified free bays and plate counts decide every admission.</p></div></article></div>""",
    'Illustrative design, not measured. A booking is a claim on capacity, not one named bay; confirmed bookings are planned as hard constraints and verified free bays decide every admission. An overstaying car can still break a booking, so the pilot measures failed bookings per 100, walk-ins turned away and idle bay-hours against a simple buffer rule. Simulation evidence and limits: appendix.')
TITLES['admission'] = 'A booking is a <em>commitment</em>, planned ahead.'
LABELS['admission'] = 'How capacity is planned'
D['operator'] = rep_html(D['operator'], 'Review the next-three-hour recommendation and its uncertainty.', 'Review the planner’s recommendation and its uncertainty.')

# appendix: planner specification (the old buffer slide stays as the baseline rule it is compared against)
D['a-planner'] = compact('a-planner', 'How the planner decides', 'How the planner decides',
    """<div class="cols v4-small"><div class="col"><h3 class="module-title">Booking request</h3>
<p class="v4-lead">Accept if, at every 15-minute check during the booking's stay window, expected occupancy plus this booking stays within capacity.</p>
<ul class="v4-tight"><li><b>Expected occupancy</b> = parked cars still expected to be there + confirmed bookings, each counted as certain to arrive.</li>
<li><b>Safety margin</b> = z &times; the spread of that estimate. z is set separately for bookings and walk-ins.</li>
<li>An optional cap on bookings per hour limits commitments in crowded windows.</li></ul>
<h3 class="module-title">Walk-in arrives</h3>
<p class="v4-lead">Admit if a bay is physically free and the same check holds at every 15-minute point inside the lookahead, using that car's expected stay.</p>
<ul class="v4-tight"><li>Later walk-ins face the same check, so protecting bookings needs no separate demand forecast.</li>
<li>The lookahead starts at 3 hours; the pilot tests longer ones (5 to 8 hours) against observed stay lengths.</li></ul>
<h3 class="module-title">Example: a 7 PM booking made at 9 AM</h3>
<p class="v4-lead">9:00 accept only if capacity for 7 PM can be committed. 12:00 admit walk-ins unless a long stay could still be parked at 7 PM. 16:00 tighten as long stays begin to overlap. 18:00 confirm free bays. 19:00 honour the booking.</p></div>
<div class="col"><h3 class="module-title">Stay model (layer 2)</h3>
<ul class="v4-tight"><li><b>Inputs:</b> time of entry, how long the car has been parked, booking type and declared duration; plate history where available.</li>
<li><b>Output:</b> the chance each parked car is still there at each check. It starts as one pooled stay distribution; gradient boosting is added only if pilot data show it helps.</li>
<li><b>Refresh:</b> every 5 to 15 minutes from the plate ledger.</li></ul>
<h3 class="module-title">Safeguards</h3>
<ul class="v4-tight"><li>Verified counts decide admission; the plan only adds restrictions.</li>
<li>Uncertain counts pause new commitments (see fault handling).</li>
<li>The simple buffer rule on the next slide runs alongside in shadow mode as the comparison.</li></ul>
<h3 class="module-title">Settings the pilot calibrates</h3>
<p class="v4-lead">Lookahead, the two margins, the booking cap, and the planned show-up rate (1.0 means no overbooking).</p></div></div>""",
    'Design specification. The rule and settings come from the simulation study in this appendix; none is calibrated to KLGCC data. Stay-model inputs other than entry time and age are proposed.')
D['a-buffer'] = D['a-buffer'].replace('How the buffer follows demand', 'Baseline rule: a buffer that follows demand')

# fault handling: failed-booking remedy; layer-2 and forecast slides: weather and events were tested and are not used
D['risk'] = rep_html(D['risk'], '<div class="exception-rail">', '<div class="exception-rail" style="grid-template-columns:repeat(4,1fr);gap:24px">')
D['risk'] = rep_html(D['risk'], '<div><b>Low paid demand</b>',
    '<div><b>Booking cannot be honoured</b><span>Proposed rule: refund the fee, offer a bay on the nearest level at no extra charge and log a failure. Failures per 100 bookings is a pilot metric.</span></div><div><b>Low paid demand</b>')
D['risk'] = rep_html(D['risk'], 'Admit eligible vehicles only when the agreed promise and buffer rules pass.', 'Admit eligible vehicles only when verified free bays and the planner’s booking checks pass.')
D['ml-stack'] = rep_html(D['ml-stack'], 'Site connections, weather/events/cinema inputs and the operating learning loop remain proposed.',
    'Weather and event inputs did not improve the forecast on 28 UK car parks, so they are not used. Site connections remain proposed.')
# appendix: redraw the ML architecture slide as the four layers, with what is tested for each
import textwrap
def _arch_svg():
    """Data-flow diagram in the V2 style (inputs -> models -> outputs), with the four layers numbered on the boxes."""
    NAVY, RED, LIGHT, MUTED, TXT = '#102a43', '#b71c1c', '#e8eef7', '#53647a', '#2b3a4d'
    o = ['<svg viewBox="0 0 1472 520" role="img" aria-label="Data flow: occupancy signals and stay inputs feed the occupancy and stay forecasts (layer 2); with the booking ledger (layer 1) they feed the rolling planner (layer 3), which feeds the safety guard (layer 4)" style="width:100%;height:auto;display:block;font-family:inherit">']
    o.append('<defs><marker id="arA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#53647a"/></marker></defs>')

    def box(x, y, w, h, title, body, dark=False, badge=None, bcol=NAVY, outline=False, size=16):
        fill = NAVY if dark else ('#fff' if outline else LIGHT)
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}"' + (f' stroke="{NAVY}" stroke-width="2.5"' if outline else '') + '/>')
        tx = x + 16
        if badge:
            o.append(f'<circle cx="{x+26}" cy="{y+26}" r="14" fill="{"#fff" if dark else bcol}"/><text x="{x+26}" y="{y+32}" text-anchor="middle" font-size="16" font-weight="800" fill="{bcol if dark else "#fff"}">{badge}</text>')
            tx = x + 50
        o.append(f'<text x="{tx}" y="{y+32}" font-size="19" font-weight="700" fill="{"#fff" if dark else NAVY}">{title}</text>')
        yy = y + 62
        for para in (body if isinstance(body, list) else [body]):
            for ln in textwrap.wrap(para, max(14, int((w - 32) / (size * 0.50)))):
                o.append(f'<text x="{x+16}" y="{yy}" font-size="{size}" fill="{"#dbe6f3" if dark else TXT}">{ln}</text>')
                yy += size + 6
            yy += 6

    def arrow(x1, y1, x2, y2, xm=None):
        d = f'M{x1} {y1}H{x2}' if xm is None and y1 == y2 else f'M{x1} {y1}H{xm}V{y2}H{x2}'
        o.append(f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="2.4" marker-end="url(#arA)"/>')

    def lane(y, text):
        o.append(f'<text x="0" y="{y}" font-size="13.5" font-weight="800" letter-spacing=".08em" fill="{RED}">{text}</text>')

    lane(30, 'OCCUPANCY FORECAST · REAL PUBLIC-DATA BENCHMARK (28 UK CAR PARKS)')
    box(0, 46, 230, 148, 'Occupancy signals', 'Current and recent levels; time, weekday, car park; same time last week.')
    box(280, 46, 240, 68, 'Weekly pattern', "Adjusted to today's level")
    box(280, 126, 240, 68, 'LightGBM', 'Learned patterns')
    box(570, 46, 250, 148, 'Expected occupancy', 'Weighted blend at 30 / 60 / 120 / 180 minutes, with an 80% range.', dark=True, badge='2', bcol=NAVY)
    arrow(230, 120, 280, 80, 255); arrow(230, 120, 280, 160, 255)
    arrow(520, 80, 570, 120, 545); arrow(520, 160, 570, 120, 545)

    lane(226, 'STAY FORECAST · SYNTHETIC STUDY, NO REAL STAY DATA YET')
    box(0, 242, 230, 124, 'Stay inputs', 'Plate-ledger entry time, booking type, declared duration.')
    box(280, 242, 240, 124, 'Stay model', 'Pooled distribution now; gradient boosting if pilot data show it helps.', badge='2', bcol=NAVY)
    box(570, 242, 250, 124, 'Still parked?', 'Chance each parked car is still there at every 15-minute check.', dark=True, badge='2', bcol=NAVY)
    arrow(230, 304, 280, 304); arrow(520, 304, 570, 304)

    lane(398, 'BOOKING LEDGER · DESIGN')
    box(0, 414, 230, 92, 'Booking ledger', 'Confirmed bookings, windows, durations.', badge='1', bcol=RED)
    arrow(230, 460, 870, 460)
    o.append(f'<text x="550" y="450" text-anchor="middle" font-size="15" font-weight="700" fill="{MUTED}">confirmed bookings are hard constraints</text>')

    box(870, 46, 300, 460, 'Rolling planner',
        ['Every 15 minutes.',
         'Accept a booking, or admit a walk-in, only if expected occupancy stays within capacity at every check ahead.',
         'Lookahead starts at 3 hours and is widened if stays run long.',
         'Optional cap on bookings per hour limits commitments in crowded windows.'], dark=True, badge='3', bcol=NAVY, size=17)
    arrow(820, 120, 870, 120); arrow(820, 304, 870, 304)

    box(1220, 180, 252, 190, 'Safety guard',
        ['Verified free bays and plate counts decide every admission.', 'Uncertain counts pause new commitments.'], badge='4', bcol=NAVY, outline=True, size=17)
    arrow(1170, 275, 1220, 275)
    o.append('</svg>')
    return ''.join(o)
D['ml-stack'] = re.sub(r'<figure class="g2-plot g2-architecture">.*?</figure>', '<figure class="g2-plot g2-architecture">' + _arch_svg() + '</figure>', D['ml-stack'], count=1, flags=re.S)
D['ml-stack'] = D['ml-stack'].replace('ML forecasting architecture', 'Architecture: four layers and what is tested')
D['ml-stack'] = re.sub(r'<div class="source">.*?</div>', '<div class="source">Sources: <a href="../analysis/benchmark_occupancy_v2.py">occupancy forecast code</a>; <a href="../analysis/simulate_architecture.py">stay model and planner simulation</a>; <a href="../analysis/backtest_signals.py">weather and event test</a>. Diagram redrawn for the commitment architecture.</div>', D['ml-stack'], count=1, flags=re.S)
D['ml-stack'] = rep_html(D['ml-stack'], 'The occupancy ensemble and request model are separate offline tasks.', 'Numbers 1 to 4 mark the four layers; the proposed site loop is log actuals, check errors, retrain, validate before deployment.')
D['forecast'] = rep_html(D['forecast'], '18,074 forecasts across 28 UK car parks; six weekly holdouts.', '18,074 forecasts, 28 UK car parks, six weekly holdouts. Weather and event flags added no accuracy.')
D['forecast'] = rep_html(D['forecast'], 'Causal occupancy benchmark</a>.', 'Causal occupancy benchmark</a>; <a href="../analysis/backtest_signals_results.txt">weather and event test</a>.')
# merge the two source slides: cost-model sources plus the secondary (directional) references as a third column
_ents = re.findall(r'<article class="g2-source-entry">.*?</article>', D['a-sources-v3'], flags=re.S)
assert len(_ents) == 6
_third = '<div class="col"><h3 class="module-title">Secondary, directional</h3>' + ''.join(_ents) + '</div>'
D['a-sources-cost'] = rep_html(D['a-sources-cost'], '</div></div></div><div class="source">', '</div>' + _third + '</div></div><div class="source">')
D['a-sources-cost'] = rep_html(D['a-sources-cost'], '<div class="cols">', '<div class="cols v4-small" style="grid-template-columns:repeat(3,1fr);gap:26px">')
D['a-sources-cost'] = D['a-sources-cost'].replace('Sources for the cost model', 'Sources: cost model and secondary references')
D['a-sources-cost'] = rep_html(D['a-sources-cost'], '<div class="source">', '<div class="source">Right-hand column: found by web search, pages not opened; verify before submission, none measures KLGCC demand or price response. ')
CM = ROOT / 'analysis/benchmarks/commitment'
V5 = json.loads((CM / 'results_v5.json').read_text())
V6 = json.loads((CM / 'results_v6.json').read_text())
TG = ('0.01', '0.005', '0.001')


def _row(label, x, d=None):
    t = x['test']
    diff = '' if d is None else f"{d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]"
    return f"<tr><td>{label}</td><td>{t['honored']:.0f}</td><td>{t['wi']:.0f}</td><td>{100*t['breach']:.2f}%</td><td>{t['score']:.0f}</td><td>{diff or '–'}</td></tr>"


_rows = ''
for _t, _name in (('0.01', 'Up to 1%'), ('0.005', 'Up to 0.5%'), ('0.001', 'Up to 0.1%')):
    _o = V5['0.5']
    _rows += f'<tr><td colspan="6"><b>Failure ceiling: {_name}</b></td></tr>'
    _rows += _row('Tuned simple rule', _o['res'][f'{_t}|quota']) + _row('Hybrid planner', _o['res'][f'{_t}|V3_hybrid'], _o['diff'][f'{_t}|V3_hybrid']['score'])
_gain = [V5['0.5']['diff'][f'{t}|V3_hybrid']['score'][0] for t in TG]
_gain0 = V5['0.0']['diff']['0.001|V3_hybrid']['score'][0]
_worst = min(V5['0.5']['diff'][f'{t}|{v}']['score'][0] for t in TG for v in ('V0_reference', 'V1_hard_bookings', 'V2_separate_risk'))
_hy = [V5['0.5']['res'][f'{t}|V3_hybrid']['test']['bpd'] for t in TG]

def _gain_svg():
    NAVY, RED, STEEL, MUTED = '#102a43', '#b71c1c', '#7c9cc0', '#53647a'
    rows = []
    for t, lab in (('0.01', 'up to 1%'), ('0.005', 'up to 0.5%'), ('0.001', 'up to 0.1%')):
        rows.append((lab, V5['0.5']['diff'][f'{t}|V3_hybrid']['score'], V5['0.0']['diff'][f'{t}|V3_hybrid']['score']))
    xmax = 28.0
    X = lambda v: 150 + (600 - 150) * v / xmax
    o = ['<svg viewBox="0 0 640 220" role="img" aria-label="Hybrid planner minus tuned simple rule, score per day with 95% intervals, at three failure ceilings, for predictable and unpredictable stays" style="width:100%;height:auto;display:block;font-family:inherit">']
    o.append(f'<text x="0" y="16" font-size="14" font-weight="800" fill="{NAVY}">Hybrid minus tuned simple rule · score per day, 95% interval</text>')
    for v in (0, 10, 20):
        o.append(f'<line x1="{X(v):.0f}" x2="{X(v):.0f}" y1="30" y2="168" stroke="#d5dde7" stroke-width="1"/><text x="{X(v):.0f}" y="186" text-anchor="middle" font-size="13" fill="{MUTED}">{v}</text>')
    for i, (lab, a, b) in enumerate(rows):
        y = 56 + i * 44
        o.append(f'<text x="0" y="{y+5}" font-size="14" font-weight="700" fill="{NAVY}">Failures {lab}</text>')
        for (m, lo, hi), col, dy in ((a, NAVY, -8), (b, STEEL, 9)):
            o.append(f'<line x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="{y+dy}" y2="{y+dy}" stroke="{col}" stroke-width="3"/><circle cx="{X(m):.1f}" cy="{y+dy}" r="6" fill="{col}"/>')
            o.append(f'<text x="{X(hi)+10:.1f}" y="{y+dy+5}" font-size="13" font-weight="700" fill="{col}">{m:+.0f}</text>')
    o.append(f'<circle cx="150" cy="208" r="5" fill="{NAVY}"/><text x="162" y="212" font-size="12.5" fill="{MUTED}">predictable stays (R² 0.38)</text><circle cx="360" cy="208" r="5" fill="{STEEL}"/><text x="372" y="212" font-size="12.5" fill="{MUTED}">unpredictable stays</text>')
    o.append('</svg>')
    return ''.join(o)


def _win_svg():
    NAVY, RED, MUTED = '#102a43', '#b71c1c', '#53647a'
    X = lambda v: 150 + 410 * v
    o = ['<svg viewBox="0 0 640 152" role="img" aria-label="Share of random worlds where the hybrid scores higher and where failures stay under the ceiling" style="width:100%;height:auto;display:block;font-family:inherit">']
    o.append(f'<text x="0" y="13" font-size="13.5" font-weight="800" fill="{NAVY}">Share of 60 random worlds · hybrid planner</text>')
    for i, (t, lab) in enumerate((('0.01', 'ceiling 1%'), ('0.005', 'ceiling 0.5%'), ('0.001', 'ceiling 0.1%'))):
        y = 26 + i * 38
        h = _S[t]['V3_hybrid']
        o.append(f'<text x="0" y="{y+19}" font-size="13.5" font-weight="700" fill="{NAVY}">{lab}</text>')
        for dy, v, col, name in ((0, h['win'], NAVY, 'higher score'), (17, h['under'], RED, 'under ceiling')):
            o.append(f'<rect x="150" y="{y+dy}" width="410" height="13" rx="3" fill="#eef1f5"/><rect x="150" y="{y+dy}" width="{410*v:.0f}" height="13" rx="3" fill="{col}"/>')
            o.append(f'<text x="158" y="{y+dy+11}" font-size="12.5" font-weight="700" fill="#fff">{v*100:.0f}%  {name}</text>')
        q = _S[t]['quota']['under']
        o.append(f'<line x1="{X(q):.0f}" x2="{X(q):.0f}" y1="{y+15}" y2="{y+32}" stroke="{MUTED}" stroke-width="2.5"/>')
    o.append(f'<text x="150" y="148" font-size="12" fill="{MUTED}">grey tick: share of worlds where the tuned simple rule stays under the same ceiling</text>')
    o.append('</svg>')
    return ''.join(o)


D['a-guarantee'] = compact('a-guarantee', 'Booking failures against walk-ins', 'Simulation: failed bookings against walk-ins',
    f"""<div class="cols v4-small"><div class="col"><table><thead><tr><th>Policy</th><th>Bookings honoured / day</th><th>Walk-ins / day</th><th>Failed bookings</th><th>Score</th><th>Score vs simple rule</th></tr></thead><tbody>{_rows}</tbody></table>
<p class="v4-lead" style="font-size:14px">100 bays, 200 fresh test days, settings chosen on 150 other days. Score = 5 × bookings honoured + walk-ins admitted. Brackets: 95% interval. <b>Limits:</b> synthetic demand and stays with assumed stay effects; hybrid tested with an 8-hour lookahead only; overstaying cars cause the remaining failures; fallback level and refund not modelled; {V5['0.5']['n_configs']} settings searched on calibration days, test days never used to choose.</p></div>
<div class="col"><h3 class="module-title">What it shows</h3><ul class="v4-tight">
<li>The <b>hybrid</b> keeps the simple rule's cap on bookings and adds the stay-risk check on walk-ins. It beat the tuned simple rule at every failure ceiling, by about {min(_gain):.0f} to {max(_gain):.0f} score a day (1 to 2%).</li>
<li>It honours about the same bookings and admits <b>more walk-ins</b>, at {min(_hy):.2f} to {max(_hy):.2f} failed bookings a day.</li>
<li>With unpredictable stays the gain shrinks ({_gain0:+.0f} a day at the strictest ceiling).</li>
<li>Planning without the booking cap lost by up to {abs(_worst):.0f} score a day at tight ceilings. A last-minute hard hold added nothing in an earlier run.</li></ul>
{_gain_svg()}</div></div>""",
    'Sources: <a href="../analysis/benchmarks/commitment/report_v5.md">report_v5.md</a>, <a href="../analysis/benchmarks/commitment/protocol_architecture.md">protocol</a>, <a href="../analysis/simulate_v5.py">simulate_v5.py</a>. Earlier runs, including the first full run (not breach-matched), are kept in the same folder.')

_S = V6['summary']
_pc = lambda x: f'{100*x:.0f}%'
_rr = ''
for _t, _name in (('0.01', '1%'), ('0.005', '0.5%'), ('0.001', '0.1%')):
    _q = _S[_t]['quota']
    _rr += f'<tr><td colspan="6"><b>Failure ceiling {_name}</b>: the tuned simple rule stays under it in {_pc(_q["under"])} of worlds</td></tr>'
    for _f, _lab in (('V3_hybrid', 'Hybrid planner'), ('V2_separate_risk', 'Planner, separate margins')):
        _x = _S[_t][_f]
        _rr += f"<tr><td>{_lab}</td><td>{_pc(_x['win'])}</td><td>{_x['med_diff']:+.1f} [{_x['p10']:+.1f}, {_x['p90']:+.1f}]</td><td>{_pc(_x['under'])}</td><td>{100*_x['med_fail']:.2f}% / {100*_x['p90_fail']:.2f}%</td><td>{_pc(_x['win_under'])}</td></tr>"
_R = V6['ranges']
D['a-robust'] = compact('a-robust', 'Robustness to assumptions', f"Robustness: {V6['n_worlds']} random sets of assumptions",
    f"""<div class="cols v4-small"><div class="col"><table><thead><tr><th>Policy</th><th>Beats simple rule (worlds)</th><th>Median score gain [10th, 90th pct]</th><th>Failures under ceiling (worlds)</th><th>Failure rate: median / 90th pct</th><th>Both: higher score and under ceiling</th></tr></thead><tbody>{_rr}</tbody></table></div>
<div class="col"><h3 class="module-title">What it shows</h3><ul class="v4-tight">
<li>The hybrid scored higher than the tuned simple rule in <b>{min(_S[t]['V3_hybrid']['win'] for t in TG)*100:.0f} to {max(_S[t]['V3_hybrid']['win'] for t in TG)*100:.0f}%</b> of worlds, with a median gain of {min(_S[t]['V3_hybrid']['med_diff'] for t in TG):.0f} to {max(_S[t]['V3_hybrid']['med_diff'] for t in TG):.0f} score a day.</li>
<li>Failures stayed under the ceiling in {min(_S[t]['V3_hybrid']['under'] for t in TG)*100:.0f} to {max(_S[t]['V3_hybrid']['under'] for t in TG)*100:.0f}% of worlds; the simple rule managed {_S['0.01']['quota']['under']*100:.0f}% at the 1% ceiling and {_S['0.001']['quota']['under']*100:.0f}% at 0.1%.</li>
<li>If real stays are worse than assumed, failures can exceed the ceiling; recalibrate the margins on pilot data.</li></ul>
<h3 class="module-title">How it was run</h3><ul class="v4-tight">
<li>60 random worlds, 30 days each, redrawing show-up, stay shock and spread, booking volume, pulse size, overstay noise, stay predictability and advance share. Settings tuned on the base case are <b>not retuned</b>; the planner refits its stay model in each world.</li></ul>
{_win_svg()}</div></div>""",
    'Sources: <a href="../analysis/benchmarks/commitment/report_v6.md">report_v6.md</a>, <a href="../analysis/simulate_mc.py">simulate_mc.py</a>; ranges fixed in the protocol before the run. The ranges are my assumptions: they test sensitivity and do not make the numbers true for KLGCC.')

# methods table: one row for the earlier controller studies, one for the commitment study
D['a-method'] = re.sub(r'<tr class=""><td>Earlier batch controller</td>.*?</tr><tr class=""><td>Event-driven controller</td>.*?</tr>',
    '<tr class=""><td>Earlier controller studies</td><td>6,500 synthetic policy-day runs; guard only matched LP; learned forecasts showed no clear advantage.</td><td>Synthetic demand; superseded by the commitment study for the architecture claim.</td></tr>'
    '<tr class=""><td>Commitment planner study</td><td>Synthetic 100-bay days: settings tuned on 150 days, tested on 200 fresh days; plus 60 random sets of assumptions.</td><td>Stay effects and demand shapes are assumed; one level, no fallback modelled.</td></tr>', D['a-method'], count=1, flags=re.S)
D['a-method'] = rep_html(D['a-method'], '18,074 forecasts; 28 UK car parks; 30/60/120/180 minutes.', '18,074 forecasts; 28 UK car parks; 30/60/120/180 minutes. Weather and event flags added no accuracy.')
D['a-method'] = rep_html(D['a-method'], 'Sources: <a href="../analysis/benchmarks/decision_value/report.md">', 'Sources: <a href="../analysis/benchmarks/commitment/report_v5.md">commitment study</a>; <a href="../analysis/benchmarks/decision_value/report.md">')

# appendix: deployment options, from the existing cost sheet (analysis/v3_costs.py); nothing new is priced here
RUN_HI = int(round(MAINT_RATE * INTEGRATION * (1 + OVERRUN) + HOSTING, -2))
def _need5(cap, run): return (run + cap / 5) / (G[50] * 365 * NET)
def _pay(cap, run, n):
    c_ = contrib_opt(n, run)
    return f'{cap/c_:.1f} yr' if c_ > 0 else 'n/a'
def contrib_opt(n, run): return n * G[50] * 365 * NET - run
_opts = [
    ('Existing LPR + software', CAPEX_LO, RUN, 'Entry and exit plate ledger; the capacity guard and booking checks.', 'No independent count. At 0.5 to 1% missed reads the 200-bay simulation shows 5 to 6 unseen and 7 to 10 ghost cars (99th percentile).'),
    ('+ CCTV count audit and display (base case)', CAPEX, RUN, f'{N_CAM} cameras over blind spots, one display; an independent count and audit trail.', 'Coverage depends on the site survey; add cameras only where it finds gaps.'),
    ('High case: 10 cameras, 35% build overrun', CAPEX_HI, RUN_HI, 'Fuller aisle coverage.', 'Revenue is unchanged, so only worth it if the survey finds wide blind spots.'),
]
_orows = ''.join(f"<tr><td><b>{n}</b></td><td>RM{cap/1000:.1f}k</td><td>RM{run/1000:.1f}k</td><td>{_need5(cap, run):.0f}</td><td>{_pay(cap, run, rows_n[0])} / {_pay(cap, run, rows_n[1])}</td><td>{adds}</td><td>{risk}</td></tr>" for n, cap, run, adds, risk in _opts)
_orows += '<tr><td><b>Bay-level sensing or a digital twin</b></td><td colspan="4">Not costed: no quote or source.</td><td>Per-bay occupancy and guidance.</td><td>Not tested. The guarantee here is checked at zone level from counts, not per bay.</td></tr>'
D['a-options'] = compact('a-options', 'Deployment options', 'Deployment options: what each spends, earns and risks',
    f"""<div class="v4-small"><table><thead><tr><th>Option</th><th>Upfront</th><th>Running a year</th><th>Bookings a day for 5-year recovery</th><th>Payback at {rows_n[0]:.0f} / {rows_n[1]:.0f} bookings a day</th><th>What it adds</th><th>Main risk</th></tr></thead><tbody>{_orows}</tbody></table>
<p class="v4-lead" style="margin-top:10px;font-size:15.5px">What it earns is the same under every option: RM{G[50]:.2f} gross per accepted booking at 50% members, {NET:.3f} net of tax, operator share and card fees (slide 10). The options differ in cost and in how well the count can be trusted. Upfront cost is a scenario: RM{DAY_RATE:.0f}/day build rate sourced, effort and site works assumed, hardware from listed prices.</p></div>""",
    'Derived from <a href="../analysis/v3_costs.py">v3_costs.py</a> (each input marked sourced, derived or assumed) and <a href="../analysis/v3_zone200.py">v3_zone200.py</a>. Break-even uses the same net factor and gross per booking as the revenue slide. Not a quote.')

APX_TAKE = {
    'risk': 'A booking we cannot honour is refunded and logged as a failure; the pilot reports failed bookings per 100.',
    'a-guarantee': 'Keeping the simple rule\u2019s booking cap and adding the stay-risk check on walk-ins gave about 1 to 2% more score at near-zero failures.',
    'a-robust': 'It scores higher in almost every world, but the failure ceiling must be recalibrated on pilot stay data.',
    'a-sim200': 'Capacity is not the limit at this scale: demand and willingness to pay are.',
    'a-options': 'Revenue is the same under every option; the choice is how much count accuracy to buy.',
    'a-method': 'Only occupancy and camera results use real data. Demand and booking behaviour stay synthetic until the pilot.',
}
# ---- slides 5-7: same design, content de-duplicated (journey stays on slide 5; slide 6 shows what exists; slide 7 uses the four-layer vocabulary)
D['service'] = rep_html(D['service'], 'LPR counts and accepted bookings decide every admission, so walk-ins keep their space. A booking is a claim on the zone, not a fixed bay; unclaimed claims return to the pool.',
    'A booking is a claim on the zone, not a fixed bay, so walk-ins keep their space. How the capacity is planned is shown later in this deck.')
TITLES['member'] = 'The prototype: <em>what is built, what is simulated.</em>'
D['member'] = rep_html(D['member'], '<h3>What the prototype shows</h3>', '<h3>What exists today</h3>')
D['member'] = rep_html(D['member'], '<b>Reserve</b><p>Pick a mall, date and arrival time. The fee and the no-show rule are shown before confirming.</p>',
    '<b>Built</b><p>A booking flow: mall, date and arrival time, with the fee and no-show rule shown before confirming.</p>')
D['member'] = rep_html(D['member'], '<b>Enter</b><p>A QR entry pass after booking. The LPR check is simulated, with no live gate connection.</p>',
    '<b>Simulated</b><p>The QR entry pass and the LPR check. No live gate, payment or controller connection.</p>')
D['member'] = rep_html(D['member'], '<b>See the zone</b><p>Occupied, reserved and available bays by level, with safety bays protected.</p>',
    '<b>Zone view</b><p>Occupied, reserved and available bays by level, with safety bays protected (simulated data).</p>')
D['mechanism'] = rep_html(D['mechanism'], '<li><b>Capacity guard</b>verified free bays decide</li><li><b>Buffer plan</b>rolling, every 15 minutes</li>',
    '<li><b>Stay forecast and planner</b>re-plans every 15 minutes</li><li><b>Safety guard</b>verified free bays decide</li>')
# slide 7: a second way in, shown as a small box under the fee table
D['mechanism'] = rep_html(D['mechanism'], '</table></div>\n</section>',
    f'</table></div>'
    f'<div class="v4-box"><h4>Another way in: earn a booking</h4>'
    f'<div class="v4-box__row"><b>Earn</b><span>Spend above a set amount in store, get one booking.</span></div>'
    f'<div class="v4-box__row"><b>Cost</b><span>Fee forgone; pays back if 1 in {1/vo_5:.0f} to 1 in {1/vo_15:.0f} visit again.</span></div>'
    f'<div class="v4-box__row"><b>Pilot</b><span>Tested against the paid booking. Store-issued tickets later.</span></div></div>\n</section>')

# ---- slides 12, 14: finding-led titles; caveat bars become plain notes; slides 10, 11 likewise
TITLES['value'] = f'Extra tenant sales of <em>RM{gto_lo/1000:.0f}k\u2013{gto_hi/1000:.0f}k</em> a year would cover the gap'
TITLES['revenue'] = 'Booking revenue depends on <em>who books</em> and how many'
for _k in ('revenue', 'cost', 'value'):
    D[_k] = re.sub(r'<div class="v3-sowhat"><span>[^<]*</span><p>(.*?)</p></div>', r'<p class="v4-foot">\1</p>', D[_k], flags=re.S)
D['value'] = rep_html(D['value'], 'Gap = RM', 'Directional evidence, not a forecast. Gap = RM')

TITLES['cost'] = f'KLGCC zone: <em>RM{CAPEX/1000:.1f}k upfront</em> (capex), RM10.5k a year (opex)'
IC_DOC = _ic('<path d="M6 3h9l3 3v15H6z"/><path d="M9 11h6M9 15h6"/>')
IC_CAL = _ic('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>')
IC_SHIELD = _ic('<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>')
IC_TAGP = _ic('<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.2"/>')
for _t, _i in (('Booking ledger', IC_DOC), ('Stay forecast and planner', IC_CAL), ('Safety guard', IC_SHIELD), ('Price and credit rules', IC_TAGP)):
    D['mechanism'] = rep_html(D['mechanism'], f'<li><b>{_t}</b>', f'<li><span class="mc-ic">{_i}</span><b>{_t}</b>')
IC_GIFT = _ic('<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13M5 12v9h14v-9M12 8c-2-4-6-3-5 0 .6 1.6 3 1.2 5 0zM12 8c2-4 6-3 5 0-.6 1.6-3 1.2-5 0z"/>')
IC_PCT = _ic('<path d="M19 5L5 19"/><circle cx="7" cy="7" r="2.2"/><circle cx="17" cy="17" r="2.2"/>')
IC_FLASK = _ic('<path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3"/><path d="M7.5 15h9"/>')
D['problem'] = rep_html(D['problem'], 'Parking area during our site visit (Saturday, ~7:00 PM), where most bays were occupied.', 'Parking area during our site visit (9 Nov 2026), where most bays were occupied.')
MAIN = ['cover', 'team', 'problem', 'alternatives', 'service', 'member', 'mechanism', 'admission', 'operator',
        'revenue', 'cost', 'value', 'integration', 'pilot-design', 'thanks']
SECTION = {'cover': 'Overview', 'team': 'Overview', 'problem': 'Overview', 'thanks': 'Overview',
           'alternatives': 'Product', 'service': 'Product', 'member': 'Product', 'mechanism': 'Product', 'operator': 'Product', 'admission': 'Product', 'integration': 'Product',
           'paths': 'Business', 'revenue': 'Business', 'cost': 'Business', 'value': 'Business',
           'pilot-design': 'Implementation', 'decision': 'Implementation'}
APPX = ['ml-stack', 'a-planner', 'a-buffer', 'risk', 'forecast', 'simulation', 'a-guarantee', 'a-robust', 'a-sim200', 'a-register', 'a-method-notes',
        'a-build-estimate', 'a-options', 'roadmap', 'horizons', 'scorecard', 'a-method', 'a-sources', 'a-sources-cost']
for _k in ('member', 'admission', 'integration'):
    D[_k] = re.sub(r'<div class="v3-sowhat">.*?</p></div>', '', D[_k], flags=re.S)
order = MAIN + APPX
TABS = ['Overview', 'Product', 'Business', 'Implementation', 'Appendix']
out = []
for n, i in enumerate(order, 1):
    p = D[i]
    sec = SECTION.get(i, 'Appendix')
    if i in LABELS:
        p = re.sub(r'<h2 class="slide-title">.*?</h2>', lambda m: f'<h2 class="slide-title">{TITLES[i]}</h2>', p, count=1, flags=re.S)
        p = p.replace('<div class="frame">', '<div class="frame">' + DECO.replace('LABEL', LABELS[i]), 1)
    p = re.sub(r'data-appendix="(true|false)"', f'data-appendix="{"false" if i in MAIN else "true"}"', p, count=1)
    p = re.sub(r'data-section="[^"]*"', f'data-section="{sec}"', p, count=1)
    if i in APX_TAKE:
        p = rep_html(p, '</div><div class="source">', f'<div class="apx-take"><span>Takeaway</span><p>{APX_TAKE[i]}</p></div></div><div class="source">')
    footer = f'<footer class="footer">{BRAND}<span class="page">{"" if i in MAIN else "Appendix · "}{n:02d} / {len(order)}</span></footer>'
    p = re.sub(r'<footer class="footer">.*?</footer>', lambda m: footer, p, count=1, flags=re.S)
    out.append(p)

CSS = (SITE / 'index-v2.html').read_text(encoding='utf-8')
IDS = [i for i in MAIN if i not in ('cover', 'thanks')]
def sel(t): return ','.join([f'body.edition-v2 #{i} {t}' for i in IDS] + [f'body.edition-v2 .v3p {t}'])
UNI = (sel('[class*="-stripes"]') + ',' + sel('[class*="-corner"]') + ',' + sel('[class*="-topbar"]') + ',' + sel('.frame:before') + '{display:none!important}'
       + sel('.slide-title') + '{position:absolute!important;top:92px!important;left:64px!important;right:64px!important;width:auto!important;padding:2px 0!important;'
       'border:0!important;font-size:40px!important;line-height:1.15!important;font-weight:700!important;letter-spacing:-.012em!important;'
       'color:#102a43!important;white-space:normal!important;z-index:3}'
       + sel('.slide-title em') + '{color:#b71c1c!important;font-style:normal!important}'
       + sel('.content') + '{top:176px!important;bottom:112px!important}'
       + 'body.edition-v2 #service .sv-sub{top:150px!important;left:64px!important;right:64px!important;font-size:19px!important}'
       + 'body.edition-v2 #service .content{top:196px!important}'
       + 'body.edition-v2 #team .tm-sub{position:absolute!important;top:150px!important;left:64px!important;right:64px!important;font-size:19px!important}'
       + 'body.edition-v2 #team .content{top:196px!important}:root{--red:#b71c1c}')
V3CSS = '<style id="v3-style">' + UNI + (Path(__file__).parent / 'v3-extra.css').read_text(encoding='utf-8') + '</style>'

h = head.replace('<title>ParkFlow | Member parking pilot · V2</title>', '<title>ParkFlow | Priority parking pilot · V3</title>')
h = h.replace('ParkFlow member parking: product', 'ParkFlow priority parking: product')
h = h.replace('</head>', V3CSS + '</head>', 1)
body = ''.join(out)
def _tidy_title(m):
    t = m.group(2).strip()
    t = re.sub(r'\.(</em>)?$', lambda x: x.group(1) or '', t)
    return m.group(1) + t.replace(' \u00b7 ', ': ', 1) + m.group(3)
body = re.sub(r'(<h2 class="slide-title">)(.*?)(</h2>)', _tidy_title, body, flags=re.S)
_MID = [
    ('Universiti Malaya \u00b7 revision 10 November 2026', 'Universiti Malaya, revision 10 November 2026'),
    (' \u00b7 Universiti Malaya', ', Universiti Malaya'),
    ('BCG for Uber, 2017 \u00b7 as reported', 'BCG for Uber, 2017, as reported'),
    ('INRIX, 2017 \u00b7 7,035 UK drivers', 'INRIX, 2017, 7,035 UK drivers'),
    ('ParkMobile, 2024 \u00b7 US survey', 'ParkMobile, 2024, US survey'),
    ('1 \u00b7 Home', '1. Home'), ('2 \u00b7 Reserve', '2. Reserve'), ('3 \u00b7 Confirm', '3. Confirm'), ('4 \u00b7 Zone', '4. Zone'),
    ('fee RM4 \u00b7 bill RM3', 'fee RM4, bill RM3'), ('fee RM5 \u00b7 bill RM3', 'fee RM5, bill RM3'),
    ('5-year recovery \u00b7 RM', '5-year recovery: RM'), ('3-year recovery \u00b7 RM', '3-year recovery: RM'),
    ('Voucher break-even \u00b7 share of holders who must return', 'Voucher break-even: share of holders who must return'),
    ('Spend gap \u00b7 association only', 'Spend gap (association only)'),
    ('Workstream \u00b7 owner', 'Workstream and owner'),
    ('Operator \u00b7 IT', 'Operator, IT'), ('Operator \u00b7 Loyalty', 'Operator, Loyalty'), ('Team \u00b7 Operator', 'Team, Operator'),
    ('OCCUPANCY FORECAST \u00b7 REAL', 'OCCUPANCY FORECAST: REAL'), ('STAY FORECAST \u00b7 SYNTHETIC', 'STAY FORECAST: SYNTHETIC'), ('BOOKING LEDGER \u00b7 DESIGN', 'BOOKING LEDGER: DESIGN'),
    ('Worked example \u00b7 100-bay zone', 'Worked example: 100-bay zone'),
    ('Verified plate \u00b7 current counts \u00b7 live controller \u00b7 valid entitlement', 'Verified plate, current counts, live controller, valid entitlement'),
    ('Interleaved synthetic requests \u00b7 100 bays \u00b7 60 held-out days \u00b7 selected comparators', 'Interleaved synthetic requests, 100 bays, 60 held-out days, selected comparators'),
    ('Event-driven benchmark \u00b7 8 Nov 2026', 'Event-driven benchmark, 8 Nov 2026'),
    ('Hybrid minus tuned simple rule \u00b7 score per day', 'Hybrid minus tuned simple rule: score per day'),
    ('Share of 60 random worlds \u00b7 hybrid planner', 'Share of 60 random worlds: hybrid planner'),
    ('Volume sweep \u00b7 guard + fixed buffer 10 \u00b7 grace 15 min', 'Volume sweep: guard + fixed buffer 10, grace 15 min'),
    ('Grace period \u00b7 90 requests/day', 'Grace period at 90 requests/day'),
    ('LPR count drift \u00b7 plate ledger', 'LPR count drift: plate ledger'),
    ('Commercial model \u00b7 slide 10', 'Commercial model (slide 10)'), ('Value to SDP \u00b7 slide 12', 'Value to SDP (slide 12)'),
    ('Work breakdown \u00b7 person-days', 'Work breakdown: person-days'), ('Day rate \u00b7 sourced inputs', 'Day rate: sourced inputs'),
    ('Illustrative expansion of scope \u00b7 planning windows', 'Illustrative expansion of scope; planning windows'),
    ('Gate 1 \u00b7 Before expansion', 'Gate 1: before expansion'), ('Gate 2 \u00b7 Before wider deployment', 'Gate 2: before wider deployment'), ('Gate 3 \u00b7 Before external rollout', 'Gate 3: before external rollout'),
    ('Commercial sources \u00b7 checked', 'Commercial sources, checked'),
]
for _o, _n in _MID:
    for _v in (_o, _o.replace('\u00b7', '&middot;'), _o.replace('\u00b7', '&#183;')):
        if _v in body:
            body = body.replace(_v, _n); break
    else:
        print('MIDDOT NOT FOUND:', _o)
body = re.sub(r'<span aria-label="ParkFlow" class="wordmark">park<span>flow</span><svg.*?</svg></span>', '<span aria-label="ParkFlow" class="wordmark pf2">parkflow<b>//</b></span>', body, flags=re.S)
(SITE / 'index-v3.html').write_text((h + body + tail).replace('RM10.5k', f'RM{RUN/1000:.1f}k'), encoding='utf-8')  # running cost token, one source: analysis/v3_costs.py
print('slides', len(order), 'main', len(MAIN), 'capex', CAPEX, 'be', round(be_op, 1), round(be_5, 1), round(be_3, 1), 'gap', round(gap), 'gto', round(gto_lo), round(gto_hi), 'vo', round(1/vo_5, 1), round(1/vo_15, 1))

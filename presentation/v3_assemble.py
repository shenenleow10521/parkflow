"""Run: python -B presentation/v3_assemble.py (after analysis/v3_zone200.py). One-off assembler: site-consulting/index-v2.html -> index-v3.html (V2 left untouched).
Keeps V2 design/CSS; reorders, edits, drops and adds slides. Numbers come from
analysis/benchmarks/v3/results.json so the text cannot drift from the simulation."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site-consulting'
src = (SITE / 'index-v2.html').read_text(encoding='utf-8')
R = json.loads((ROOT / 'analysis/benchmarks/v3/results.json').read_text())

# ---------------------------------------------------------------- model numbers
NET = 1 - .20 - .018 * 1.08            # after 20% operator allocation (assumed) and card fee
RUN = 10_500
CAPEX = 60_000 + 7_500 + 4 * 2_500 + 2_033   # integration + works + 4 CCTV @2.5k + display
CAPEX_LO, CAPEX_HI = 60_000 + 7_500, 60_000 + 7_500 + 10 * 2_500 + 2_033
sweep = R['volume_sweep_200bays']
acc = [r['fulfilled'] + r['noshow'] + r['expired'] for r in sweep]
G = {s: sum(r[f'gross_per_day_s{s}'] / a for r, a in zip(sweep, acc)) / len(sweep) for s in (30, 50, 70)}  # gross RM per accepted booking
def contrib(n, s): return n * G[s] * 365 * NET - RUN
def need(n_years, s): return (RUN + (CAPEX / n_years if n_years else 0)) / (G[s] * 365 * NET)
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
edit('member',
     ('<h2 class="slide-title">Member booking journey</h2>', '<h2 class="slide-title">Customer booking journey</h2>'),
     ('Choose a mall and arrival time, with the fee and registered plate visible.', 'Choose an arrival window. Fee, plate and the no-show rule are shown before paying.'),
     ('Zone LPR checks the registered plate and valid arrival window.', 'LPR checks the registered plate and the arrival window.'),
     ('See availability by level and use any available eligible bay in the zone.', 'Use any free bay in the zone. Members’ fee is credited to the parking bill; non-members pay the fee plus parking.'),
     ('RM4 weekday / RM5 peak is a proposed pricing test, additional to normal parking charges.',
      'RM4 weekday / RM5 peak is a proposed pricing test. Fee is non-refundable if the customer does not arrive (15-minute grace after the window).'))
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
     ('hardware &amp; works RM20.0k + integration RM60.0k', f'hardware &amp; works RM{(CAPEX-60_000)/1000:.1f}k + integration RM60.0k'))
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
    'Voucher arithmetic: RM4.6 reference fee mix ÷ (RM260 average trip spend × 5–15% gross turnover-rent clause). Assumes all induced spend is incremental and above the rent floor. Spend: <a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026">Vase.ai</a>; lease range: <a href="https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32">Tropicana</a>. Precedent: <a href="https://www.1utama.com.my/services/">1 Utama spend-linked parking</a>. RM300 is an example threshold, not a finding.')

def cell(n, s):
    c = contrib(n, s)
    cls = 'neg' if c <= 0 else ('mid' if CAPEX / c > 5 else 'good')
    return f'<td class="v3-c v3-c--{cls}"><b>{"−" if c < 0 else ""}RM{abs(c)/1000:.1f}k</b><small>{payback(c)}</small></td>'
sens = ''.join(f'<tr><th scope="row">≈{n:.0f} / day</th>{cell(n,30)}{cell(n,50)}{cell(n,70)}</tr>' for n in rows_n)
D['revenue'] = new('revenue', 'Booking revenue model', 'Business', 'false', 'Commercial model',
    'Revenue depends on <em>who books</em>, not just how many.',
    f'''<div class="v3-rev">
<section><h3 class="module-title red">What one booking adds to the mall</h3>
<table class="v3-tbl"><thead><tr><th></th><th>Weekday<small>fee RM4 · bill RM3</small></th><th>Weekend<small>fee RM5 · bill RM3–10</small></th></tr></thead><tbody>
<tr><th scope="row">Non-member</th><td><b>RM4</b><small>fee on top of the bill</small></td><td><b>RM5</b><small>fee on top of the bill</small></td></tr>
<tr><th scope="row">Member</th><td><b>RM1</b><small>pays RM4 in total; RM3 was already the bill</small></td><td><b>RM0–2</b><small>pays max(fee, bill); ≥4h stays add nothing</small></td></tr>
<tr><th scope="row">No-show</th><td><b>RM4</b><small>deposit kept</small></td><td><b>RM5</b><small>deposit kept</small></td></tr></tbody></table>
<p class="v3-note">Non-members carry the revenue; members carry the engagement. Fee levels {A} · KLGCC tariff {S}</p></section>
<section><h3 class="module-title red">Annual contribution by volume and member share</h3>
<table class="v3-tbl v3-sens"><thead><tr><th>Accepted bookings</th><th>30% members</th><th>50% members</th><th>70% members</th></tr></thead><tbody>{sens}</tbody></table>
<p class="v3-note">After 20% operator allocation, card fees and RM10.5k running; payback on RM{CAPEX/1000:.1f}k upfront. Capacity at 200 bays {M} · volume and member share {A}</p></section></div>
<div class="v3-sowhat"><span>So what</span><p>At 50% members, about <b>{be_op:.0f} bookings a day</b> cover running cost and <b>{be_5:.0f}</b> recover the capital in 5 years. The 200-bay simulation accepted every request up to ~120 a day, so capacity is not the limit: <b>demand and willingness to pay are</b>. The pilot measures both.</p></div>''',
    'Contribution = accepted bookings × gross per booking × 365 × (1 − 20% operator allocation − 1.944% card fee) − RM10.5k running. Gross per booking comes from the 200-bay simulation with deposits credited to members’ bills (<a href="../analysis/v3_zone200.py">v3_zone200.py</a>). Volume and member share are scenarios, not forecasts; the 20% operator allocation is unagreed. Willingness to pay is untested locally.')

bars = [('Software and integration', 60_000, 'a', 'Placeholder, no quote. Platform build (once) + site integration'),
        ('Power, network and works', 7_500, 'a', 'Allowance, no survey'),
        ('Blind-spot CCTV: 4 cameras', 10_000, 'a', 'RM2.5k installed each; hardware RM199–750 sourced'),
        ('Guidance display (optional)', 2_033, 's', 'Viskou benchmark, tax extra'),
        ('LPR cameras', 0, 's', 'Existing at KLGCC (site observation); RM3,226 each if absent')]
bar_html = ''.join(
    f'<div class="v3-bar"><div class="v3-bar__n"><b>{n}</b><small>{d}</small></div><div class="v3-bar__t"><i class="v3-bar__f v3-bar__f--{t}" style="width:{max(v/60_000*100, 0):.1f}%"></i></div><div class="v3-bar__v">RM{v:,}{" "+(S if t=="s" else A)}</div></div>'
    for n, v, t, d in bars)
D['cost'] = new('cost', 'KLGCC zone cost', 'Business', 'false', 'Cost per zone',
    f'KLGCC zone: <em>RM{CAPEX/1000:.1f}k upfront</em>, RM10.5k a year.',
    f'''<div class="v3-cost"><section><h3 class="module-title red">Upfront cost · KLGCC reference</h3>{bar_html}
<div class="v3-total"><span>Total upfront</span><b>RM{CAPEX:,}</b><em>range RM{CAPEX_LO/1000:.1f}k (no new cameras) to RM{CAPEX_HI/1000:.1f}k (10 cameras)</em></div></section>
<aside><h3 class="module-title">Other malls: same template, different inputs</h3>
<ol class="v3-ready"><li><b>LPR at the zone?</b><span>If absent: +RM3.2k per camera</span></li><li><b>Counts from LPR?</b><span>If not: add a counting method</span></li><li><b>CCTV blind spots?</b><span>0 / 4 / 10 cameras = RM0 / 10k / 25k</span></li><li><b>Member API and payment?</b><span>Drives the integration quote</span></li></ol>
<p class="v3-note">The platform build is paid once by the first mall; later malls pay site integration only. The split needs a quote.</p></aside></div>
<div class="v3-sowhat"><span>So what</span><p>Integration is <b>75% of upfront cost</b>: its quote is the biggest risk. Camera count barely moves the total, so the CCTV survey needs an estimate, not precision.</p></div>''',
    'Sources: <a href="https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows">Viskou display</a>; <a href="https://www.lelong.com.my/tp-link-vigi-c340i-4mp-outdoor-ir-bullet-network-camera-comtalk-I6348897-2007-01-Sale-I.htm">TP-Link VIGI C340i RM199</a>; <a href="https://mall.lapasar.com/office-management/it-electronics/products/hikvision-ds-2cd2046g2-iusl-4mp/121">Hikvision 4MP RM750</a>. Excludes gate/loop work if needed, central support, taxes and contingency. Installed cameras: labour and cabling are assumptions. Running RM10.5k/yr is an unquoted allowance.')

D['value'] = new('value', 'Value to SDP', 'Business', 'false', 'Value to SDP',
    'For SDP, the bar is <em>low</em>; the evidence is directional.',
    f'''<div class="v3-val">
<article><span class="v3-eyebrow">GTO break-even</span><b>RM{gto_lo/1000:.0f}–{gto_hi/1000:.0f}k</b><p>extra eligible tenant sales a year closes the 5-year capital gap at 15% to 5% rent clauses, in the low-volume case (≈{rows_n[0]:.0f} bookings/day, 50% members).</p><div class="v3-meas"><b>Pilot measure</b>Eligible tenant sales of members versus control, tenant by tenant and above the rent floor.</div></article>
<article><span class="v3-eyebrow">Voucher break-even</span><b>1 in {1/vo_5:.0f}–{1/vo_15:.0f}</b><p>voucher holders must make a visit they would not otherwise make for a RM{fee_mix:.1f} voucher to pay back through turnover rent.</p><div class="v3-meas"><b>Pilot measure</b>Voucher redemption, and the share of holders whose return visit is incremental versus control.</div></article>
<article><span class="v3-eyebrow">Spend gap · association only</span><div class="v3-cmp"><div><i style="height:{195/327*100:.0f}%"></i><span>RM195<small>1–2 visits / month</small></span></div><div><i class="hi" style="height:100%"></i><span>RM327<small>5+ visits / month</small></span></div></div><p>Recalled trip spend, +68%. It does not show that parking causes either.</p><div class="v3-meas"><b>Pilot measure</b>30/60/90-day return rate and visits per member versus an eligible control cohort.</div></article></div>
<div class="v3-sowhat"><span>Caveat</span><p>Gross turnover rent has a floor: extra sales below it add <b>zero</b> rent. Count it tenant by tenant, and net out vouchers, support and displacement before calling it profit.</p></div>''',
    f'Gap = RM{CAPEX/1000:.1f}k ÷ 5 − RM{low/1000:.1f}k contribution = RM{gap/1000:.1f}k a year. Sales needed = gap ÷ rent rate; break-even is a sensitivity, not a forecast. Sources: <a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026">Vase.ai survey (N=500)</a>; <a href="https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32">Tropicana lease terms</a>; <a href="https://www.simedarbyproperty.com/sites/default/files/2024-05/Reply%20Letter%20to%20MSWG%20%2817052024%29.pdf">SDP reply to MSWG</a>. No SDP-specific rent rate or retention effect is claimed.')

reg = [('Reservation fee RM4 weekday / RM5 peak', A, 'Price test. Local anchor: Sunway ParkEasy reservations reported at 6–8 credits (RM1 each) per booking; verify current price.'),
       ('Standard parking bill', S, 'KLGCC official tariff: RM3 weekday; weekend RM3 to 3h, then RM2/h, cap RM10.'),
       ('Member offset rule', A, 'Fee credited to the bill; excess kept as revenue; deposit kept on no-show. Our design choice.'),
       ('No-show rate 5–20%', A, 'Other settings report 10–31% (campground model, car rental, one city system). Not parking at malls.'),
       ('Grace period 15 min, soft release', M, 'Tested at 10–30 min; with soft release the choice barely moves idle bay-hours.'),
       ('Bookings per day, member share', A, 'No local data. Scenario ranges; the pilot measures both.'),
       ('KLGCC footfall', '<span class="v3-t v3-t--n">Not found</span>', 'Opened 24 Oct 2025; about 100k visitors in the first weeks. No annual figure, so not used.'),
       ('LPR and CCTV at KLGCC', S, 'Team Hexa site visit, 9 Nov 2026. Vendor, data access and blind spots unconfirmed.'),
       ('CCTV unit cost', A, 'Hardware RM199–750 sourced; RM2.5k installed per camera assumed.'),
       ('LPR miss rate 0.5–3%', M, 'Count-drift simulation; real read accuracy is a pilot measurement.'),
       ('Software integration RM60k', A, 'Placeholder. No quote.'),
       ('Willingness to pay', A, 'Directional only: ParkMobile 67% (US). No local test; first pilot measure.')]
D['a-register'] = compact('a-register', 'Data register', 'Data register: what is sourced, simulated or assumed',
    '<table><colgroup><col style="width:30%"/><col style="width:11%"/><col style="width:59%"/></colgroup><thead><tr><th>Input</th><th>Tier</th><th>Basis</th></tr></thead><tbody>'
    + ''.join(f'<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>' for a, b, c in reg) + '</tbody></table>',
    'Order of preference: web sources, then simulation, then assumptions as a last resort. Web-derived items come from search results and must be opened and checked before submission. Nothing here is a measured KLGCC demand or price response.')

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

src_v3 = [('EdgeProp: KLGCC Mall early footfall', 'https://www.edgeprop.my/content/1914504/sime-darby-property-sees-klgcc-mall-breaking-even-sooner-expected-amid-strong-footfall', 'About 100,000 visitors in the first weeks; no annual figure.'),
          ('Autobuzz: Sunway Pyramid reservation bays', 'https://autobuzz.my/2019/06/12/reserve-park-and-charge-at-reserve-shell-recharge-bays-in-sunway-pyramid/', 'ParkEasy booking reported at 6 (weekday) / 8 (weekend) credits, 1 credit = RM1; 2019, EV bays.'),
          ('TP-Link VIGI C340i, Lelong', 'https://www.lelong.com.my/tp-link-vigi-c340i-4mp-outdoor-ir-bullet-network-camera-comtalk-I6348897-2007-01-Sale-I.htm', '4MP outdoor IP camera, RM199 listing.'),
          ('Hikvision 4MP, Lapasar', 'https://mall.lapasar.com/office-management/it-electronics/products/hikvision-ds-2cd2046g2-iusl-4mp/121', 'About RM750 per unit; B2B listing.'),
          ('Manitou Springs reservation minutes', 'https://www.manitouspringsco.gov/DocumentCenter/View/2688/FIRS-Update-Meeting-Minutes-September-16-2020', 'One city system: 31% weekly no-show. Directional only.'),
          ('Campground reservation policy brief', 'https://jonathan-e-hughes.github.io/policy-briefs/campground-reservations.html', 'Modelled 10.2% no-show; fees reduce unused bookings.'),
          ('Car rental no-show analysts', 'https://www.autorentalnews.com/articles/charging-for-no-shows-could-improve-profits', '20–30% no-shows, analyst estimate; not parking.'),
          ('ATRI truck-parking survey', 'https://www.truckinginfo.com/news/truckers-like-reserved-parking-but-not-paying-for-it', 'Almost half would refuse to pay for reserved parking; different population.')]
D['a-sources-v3'] = compact('a-sources-v3', 'Added sources', 'Added sources for V3 (secondary, directional)',
    '<div class="cols"><div class="col">' + ''.join(f'<article class="g2-source-entry"><b><a href="{u}">{t}</a></b><p>{p}</p></article>' for t, u, p in src_v3[:4])
    + '</div><div class="col">' + ''.join(f'<article class="g2-source-entry"><b><a href="{u}">{t}</a></b><p>{p}</p></article>' for t, u, p in src_v3[4:]) + '</div></div>',
    'Found by web search; pages were not opened for this version. Open and verify each before submission. None of these measures KLGCC demand or price response.')

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
    W, H, L, R, T, B = 760, 330, 62, 122, 14, 44
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
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><title>{lab}: RM{contrib(22,sh)/1000:.1f}k at 22/day, RM{contrib(79,sh)/1000:.1f}k at 79/day</title></polyline>')
        ye = Y(contrib(120, sh))
        o.append(f'<circle cx="{W-R+10}" cy="{ye:.1f}" r="5" fill="{col}"/><text x="{W-R+20}" y="{ye+4.5:.1f}" class="lab">{lab}</text>')
    for n, v in ((be_op, 0), (be_5, CAPEX / 5), (be_3, CAPEX / 3)):
        o.append(f'<circle cx="{X(n):.1f}" cy="{Y(v):.1f}" r="6" fill="{RED}" stroke="#fff" stroke-width="2"><title>{n:.0f} bookings/day at 50% members</title></circle>')
        o.append(f'<text x="{X(n)+9:.1f}" y="{Y(v)+19:.1f}" class="dl">{n:.0f}/day</text>')
    o.append('</svg>')
    return ''.join(o)

def val_chart():
    W, H, L, R, T, B = 760, 320, 62, 118, 14, 44
    xmax, ymax = 250000, 40000
    X = lambda x: L + (W - L - R) * x / xmax
    Y = lambda v: T + (H - T - B) * (ymax - v) / ymax
    o = [f'<svg class="v3-ch" viewBox="0 0 {W} {H}" role="img" aria-label="Extra gross turnover rent against extra eligible tenant sales at 5, 10 and 15 percent rent clauses. The RM{gap/1000:.1f}k annual gap is closed at RM{gto_lo/1000:.0f}k of extra sales at 15 percent and RM{gto_hi/1000:.0f}k at 5 percent.">']
    o += _axes(W, H, L, R, T, B, X, Y, range(0, 250001, 50000), range(0, 40001, 10000), lambda v: f'{v//1000}k' if v else '0', lambda v: f'{v//1000}k' if v else '0', 'Extra eligible tenant sales a year, RM', 'Extra rent, RM')
    o.append(f'<rect x="{X(gto_lo):.1f}" y="{T}" width="{X(gto_hi)-X(gto_lo):.1f}" height="{H-T-B}" fill="{RED}" opacity=".07"/>')
    o.append(f'<text x="{(X(gto_lo)+X(gto_hi))/2:.1f}" y="{T+18}" text-anchor="middle" class="ref">break-even range RM{gto_lo/1000:.0f}k – RM{gto_hi/1000:.0f}k</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(gap):.1f}" y2="{Y(gap):.1f}" stroke="{RED}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    o.append(f'<text x="{W-R-4}" y="{Y(gap)+17:.1f}" text-anchor="end" class="ref">annual gap RM{gap/1000:.1f}k</text>')
    for rate, col in ((.05, STEEL), (.10, '#3d5f82'), (.15, NAVY)):
        o.append(f'<line x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(xmax):.1f}" y2="{Y(rate*xmax):.1f}" stroke="{col}" stroke-width="2.6" stroke-linecap="round"><title>{rate*100:.0f}% clause: RM{rate*100000/1000:.0f}k extra rent per RM100k extra sales</title></line>')
        o.append(f'<circle cx="{W-R+10}" cy="{Y(rate*xmax):.1f}" r="5" fill="{col}"/><text x="{W-R+20}" y="{Y(rate*xmax)+4.5:.1f}" class="lab">{rate*100:.0f}% clause</text>')
        o.append(f'<circle cx="{X(gap/rate):.1f}" cy="{Y(gap):.1f}" r="6" fill="{col}" stroke="#fff" stroke-width="2"><title>RM{gap/rate/1000:.0f}k extra sales at a {rate*100:.0f}% clause</title></circle>')
    o.append('</svg>')
    return ''.join(o)

def donut(items, total, size=250, r=84, sw=40):
    import math
    C = 2 * math.pi * r; cx = cy = size / 2
    o = [f'<svg class="v3-donut" viewBox="0 0 {size} {size}" role="img" aria-label="Upfront cost split of RM{total:,}: ' + ', '.join(f'{n} {v/total*100:.0f}%' for n, v, c in items) + '">']
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#eef1f5" stroke-width="{sw}"/>')
    acc = 0
    for n, v, col in items:
        L_ = v / total * C
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-dasharray="{max(L_-3,0):.1f} {C-max(L_-3,0):.1f}" stroke-dashoffset="{-acc:.1f}" transform="rotate(-90 {cx} {cy})"><title>{n}: RM{v:,} ({v/total*100:.0f}%)</title></circle>')
        acc += L_
    o.append(f'<text x="{cx}" y="{cy-2}" text-anchor="middle" class="dn">RM{total/1000:.1f}k</text><text x="{cx}" y="{cy+20}" text-anchor="middle" class="ds">upfront</text></svg>')
    return ''.join(o)

# ---- revenue: break-even curve replaces the contribution table
D['revenue'] = new('revenue', 'Booking revenue model', 'Business', 'false', '', 'Revenue depends on who books.',
    f"""<div class="v3-rev v3-rev--chart">
<section><h3 class="module-title red">What one booking adds to the mall</h3>
<table class="v3-tbl"><thead><tr><th></th><th>Weekday<small>fee RM4 · bill RM3</small></th><th>Weekend<small>fee RM5 · bill RM3–10</small></th></tr></thead><tbody>
<tr><th scope="row">Non-member</th><td><b>RM4</b><small>fee on top of the bill</small></td><td><b>RM5</b><small>fee on top of the bill</small></td></tr>
<tr><th scope="row">Member</th><td><b>RM1</b><small>pays RM4 in total; RM3 was already the bill</small></td><td><b>RM0–2</b><small>pays max(fee, bill); ≥4h stays add nothing</small></td></tr>
<tr><th scope="row">No-show</th><td><b>RM4</b><small>deposit kept</small></td><td><b>RM5</b><small>deposit kept</small></td></tr></tbody></table>
<p class="v3-note">Non-members carry the revenue; members carry the engagement. Fee levels {A} · KLGCC tariff {S}</p></section>
<section><h3 class="module-title red">Annual contribution by volume and member share</h3>{rev_chart()}
<p class="v3-note">After 20% operator allocation, card fees and RM10.5k running. Capacity at 200 bays {M} · volume and member share {A}</p></section></div>
<div class="v3-sowhat"><span>So what</span><p>At 50% members, about <b>{be_op:.0f} bookings a day</b> cover running cost and <b>{be_5:.0f}</b> recover the capital in 5 years. The 200-bay simulation accepted every request up to ~120 a day, so capacity is not the limit: <b>demand and willingness to pay are</b>. The pilot measures both.</p></div>""",
    'Contribution = accepted bookings × gross per booking × 365 × (1 − 20% operator allocation − 1.944% card fee) − RM10.5k running. Gross per booking comes from the 200-bay simulation with deposits credited to members’ bills (<a href="../analysis/v3_zone200.py">v3_zone200.py</a>). Volume and member share are scenarios, not forecasts; the 20% operator allocation is unagreed. Willingness to pay is untested locally.')

# ---- value: rent-versus-sales chart replaces the big numbers
bar = lambda pct, col: f'<span class="vz-track"><i style="width:{min(pct,100):.1f}%;background:{col}"></i></span>'
D['value'] = new('value', 'Value to SDP', 'Business', 'false', '', 'For SDP the bar is low.',
    f"""<div class="vz"><section class="vz-main"><h3 class="module-title red">Extra rent from extra eligible tenant sales</h3>{val_chart()}
<p class="vz-note"><b>RM{gto_lo/1000:.0f}k–{gto_hi/1000:.0f}k</b> of extra eligible tenant sales a year closes the RM{gap/1000:.1f}k gap, in the low-volume case (≈{rows_n[0]:.0f} bookings/day, 50% members). <em>Pilot measure:</em> member sales versus control, tenant by tenant, above the rent floor.</p></section>
<div class="vz-side"><section><h3 class="module-title">Voucher break-even</h3>
<div class="vz-row"><span>5% clause</span>{bar(vo_5*100, STEEL)}<b>{vo_5*100:.0f}%</b></div><div class="vz-row"><span>15% clause</span>{bar(vo_15*100, NAVY)}<b>{vo_15*100:.0f}%</b></div>
<p class="vz-note"><b>How it works:</b> qualifying spend (example RM300, set per mall programme) earns a free priority booking for a later visit, limited to available slots.</p><p class="vz-note">Share of voucher holders who must make a visit they would not otherwise make, for a RM{fee_mix:.1f} voucher to pay back: <b>1 in {1/vo_5:.0f} to 1 in {1/vo_15:.0f}</b>. <em>Pilot measure:</em> redemption and incremental return visits versus control.</p></section>
<section><h3 class="module-title">Spend gap · association only</h3>
<div class="vz-row"><span>1–2 visits / month</span>{bar(195/327*100, '#9aa8bb')}<b>RM195</b></div><div class="vz-row"><span>5+ visits / month</span>{bar(100, RED)}<b>RM327</b></div>
<p class="vz-note">Recalled trip spend, +68%. It does not show that parking causes either. <em>Pilot measure:</em> 30/60/90-day return rate versus control.</p></section></div></div>
<div class="v3-sowhat"><span>Caveat</span><p>Gross turnover rent has a floor: extra sales below it add <b>zero</b> rent. Count it tenant by tenant, and net out vouchers, support and displacement before calling it profit.</p></div>""",
    f'Gap = RM{CAPEX/1000:.1f}k ÷ 5 − RM{low/1000:.1f}k contribution = RM{gap/1000:.1f}k a year. Sales needed = gap ÷ rent rate; break-even is a sensitivity, not a forecast. Sources: <a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026">Vase.ai survey (N=500)</a>; <a href="https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32">Tropicana lease terms</a>; <a href="https://www.simedarbyproperty.com/sites/default/files/2024-05/Reply%20Letter%20to%20MSWG%20%2817052024%29.pdf">SDP reply to MSWG</a>. No SDP-specific rent rate or retention effect is claimed.')

# ---- cost: donut + legend replaces the bar list
slices = [('Software and integration', 60_000, RED, 'a', 'Placeholder, no quote. Platform build (once) + site integration'),
          ('Blind-spot CCTV, 4 cameras', 10_000, NAVY, 'a', 'RM2.5k installed each; hardware RM199–750 sourced'),
          ('Power, network and works', 7_500, STEEL, 'a', 'Allowance, no survey'),
          ('Guidance display (optional)', 2_033, '#c5ced9', 's', 'Viskou benchmark, tax extra')]
leg = ''.join(f'<li><i style="background:{c}"></i><div><b>{n}</b><small>{d}</small></div><span>RM{v:,}<em>{v/CAPEX*100:.0f}%</em>{S if t=="s" else A}</span></li>' for n, v, c, t, d in slices)
leg += f'<li class="v3-zero"><i></i><div><b>LPR cameras</b><small>Existing at KLGCC (site observation); RM3,226 each if absent</small></div><span>RM0{S}</span></li>'
D['cost'] = new('cost', 'KLGCC zone cost', 'Business', 'false', '', f'KLGCC zone: RM{CAPEX/1000:.1f}k upfront, RM10.5k a year.',
    f"""<div class="v3-cost"><section><h3 class="module-title red">Upfront cost · KLGCC reference</h3>
<div class="v3-donutrow">{donut([(n, v, c) for n, v, c, t, d in slices], CAPEX)}<ul class="v3-dleg">{leg}</ul></div>
<div class="v3-total"><span>Total upfront</span><b>RM{CAPEX:,}</b><em>range RM{CAPEX_LO/1000:.1f}k (no new cameras) to RM{CAPEX_HI/1000:.1f}k (10 cameras) · running RM10.5k a year</em></div></section>
<aside><h3 class="module-title">Other malls: same template, different inputs</h3>
<ol class="v3-ready"><li><b>LPR at the zone?</b><span>If absent: +RM3.2k per camera</span></li><li><b>Counts from LPR?</b><span>If not: add a counting method</span></li><li><b>CCTV blind spots?</b><span>0 / 4 / 10 cameras = RM0 / 10k / 25k</span></li><li><b>Member API and payment?</b><span>Drives the integration quote</span></li></ol>
<p class="v3-note">The platform build is paid once by the first mall; later malls pay site integration only. The split needs a quote.</p></aside></div>
<div class="v3-sowhat"><span>So what</span><p>Integration is <b>75% of upfront cost</b>: its quote is the biggest risk. Camera count barely moves the total, so the CCTV survey needs an estimate, not precision.</p></div>""",
    'Sources: <a href="https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows">Viskou display</a>; <a href="https://www.lelong.com.my/tp-link-vigi-c340i-4mp-outdoor-ir-bullet-network-camera-comtalk-I6348897-2007-01-Sale-I.htm">TP-Link VIGI C340i RM199</a>; <a href="https://mall.lapasar.com/office-management/it-electronics/products/hikvision-ds-2cd2046g2-iusl-4mp/121">Hikvision 4MP RM750</a>. Excludes gate/loop work if needed, central support, taxes and contingency. Installed cameras: labour and cabling are assumptions. Running RM10.5k/yr is an unquoted allowance.')

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
<p class="rh-key"><i class="o"></i>Occupied <i class="h"></i>Held for bookings <i class="f"></i>Open to walk-ins</p>
<div class="rh-cmp"><h4>When holding starts</h4>
<div class="rh-lane"><span>Reactive rule</span><div><i class="g" style="width:96%"></i><i class="r" style="width:4%"></i></div><em>12:00, when free bays run low</em></div>
<div class="rh-lane"><span>Rolling plan</span><div><i class="g" style="width:50%"></i><i class="r" style="width:50%"></i></div><em>10:30, as bookings build</em></div></div></section></div>
<div class="v3-sowhat"><span>Pilot test</span><p>Verified capacity still decides every admission; the plan only sets how many bays to hold back. Tested against a fixed buffer on <b>rejected bookings at peak, idle bay-hours and walk-ins admitted</b>.</p></div>""",
    'Illustrative, not measured. In the offline simulation (synthetic demand) the three-hour plan did not beat a fixed 5-bay buffer, so the pilot runs it in shadow mode first. Forecasts inform the plan; they never create an available bay. Rule and calibration: appendix.')
TITLES['admission'] = 'An adaptive plan: <em>three hours ahead, every 15 minutes.</em>'
LABELS['admission'] = 'Adaptive capacity'

# ---- site readiness as an evidence matrix
def sr_photos(items):
    return ''.join(f'<figure><img alt="{c}" src="assets/{f}.webp" style="object-position:{p}"/><figcaption>{c}</figcaption></figure>' for f, c, p in items)
def sr_row(n, title, q, why, photos, observed, confirm):
    return (f'<article class="sr-row"><div class="sr-ph sr-ph--{len(photos)}">{sr_photos(photos)}</div>'
            f'<div class="sr-main"><span class="sr-n">{n}</span><h3>{title}</h3><p>{q}</p><small>Why it matters: {why}</small></div>'
            f'<div class="sr-st"><div class="ok"><b>Observed</b><span>{observed}</span></div><div class="tbc"><b>To confirm</b><span>{confirm}</span></div></div></article>')
D['integration'] = new('integration', 'Site readiness', 'Product', 'false', '', 'What the site must confirm.',
    '<div class="sr">'
    + sr_row('01', 'Zone counts from LPR', 'Can the existing level LPR give reconciled entry and exit events and a plate ledger?',
             'the capacity guard needs a verified zone count, not only a payment event.',
             [('klgcc-visit-entry-barrier', 'Entry barrier and LPR', '55% 55%')],
             'LPR at the entry barrier', 'Vendor, data and API access, read accuracy')
    + sr_row('02', 'Camera coverage', 'Do the existing cameras cover the aisles, and where are the blind spots?',
             'CCTV is an audit layer; add cameras only where the survey finds gaps.',
             [('klgcc-visit-cctv-aisle', 'Aisle camera', '50% 30%'), ('klgcc-visit-cctv-ceiling', 'Ceiling camera', '50% 45%'), ('klgcc-visit-camera-check', 'Mapping positions', '50% 35%')],
             'Aisle and ceiling cameras', 'Blind spots, footage access, glare and pillars')
    + sr_row('03', 'Member and payment systems', 'Can member identity, payment and booking expiry connect to the controller?',
             'the operator needs one valid admission decision and a traceable exception path.',
             [('klgcc-visit-rates-board', 'Posted rates and payments', '60% 35%'), ('klgcc-visit-staff-interview', 'Customer-service interview', '50% 30%')],
             'Card and e-wallet payment, posted rates', 'Mall membership API, settlement and refunds')
    + '</div><div class="v3-sowhat"><span>First action</span><p>A focused site and vendor audit, before any hardware scope is expanded.</p></div>',
    'Sources: <a href="https://www.simedarbyproperty.com/malls/klgcc-mall/">KLGCC Mall: official parking information</a>. Observed items are Team Hexa site-visit observations (9 Nov 2026), not mall-confirmed. Confirm controller, power/network, gate safety, local coverage and incumbent interfaces.')
TITLES['integration'] = 'What the site <em>must confirm</em> before the pilot.'

# ---- pilot slide now carries the ask
D['pilot-design'] = D['pilot-design'].replace('<em>Month-6 review</em>', '<em>Month-6 review, then other SDP malls</em>', 1)
D['pilot-design'] = D['pilot-design'].replace('</div><div class="source">',
    '<div class="v3-ask"><span>The ask</span><p>Nominate a KLGCC sponsor and operator counterpart, and enable the site survey, integration talks and baseline counts. <b>Reference upfront RM' + f'{CAPEX/1000:.1f}' + 'k</b> (range RM' + f'{CAPEX_LO/1000:.1f}–{CAPEX_HI/1000:.1f}' + 'k) plus RM10.5k a year.</p></div></div><div class="source">', 1)
TITLES['pilot-design'] = 'The ask: <em>an eight-week pilot at KLGCC.</em>'
LABELS['pilot-design'] = 'Pilot and ask'

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
MAIN = ['cover', 'team', 'problem', 'alternatives', 'service', 'member', 'operator', 'admission',
        'revenue', 'value', 'cost', 'integration', 'pilot-design', 'thanks']
SECTION = {'cover': 'Overview', 'team': 'Overview', 'problem': 'Overview', 'thanks': 'Overview',
           'alternatives': 'Product', 'service': 'Product', 'member': 'Product', 'operator': 'Product', 'admission': 'Product', 'integration': 'Product',
           'paths': 'Business', 'revenue': 'Business', 'cost': 'Business', 'value': 'Business',
           'pilot-design': 'Implementation', 'decision': 'Implementation'}
APPX = ['a-buffer', 'a-register', 'a-sim200', 'risk', 'ml-stack', 'forecast', 'simulation', 'roadmap', 'horizons', 'scorecard',
        'a-optimizer-study', 'a-forecast-results', 'a-stress-results', 'a-decision-study', 'a-method', 'a-sources', 'a-sources-v3']
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
    footer = f'<footer class="footer">{BRAND}<span class="page">{"" if i in MAIN else "Appendix · "}{n:02d} / {len(order)}</span></footer>'
    p = re.sub(r'<footer class="footer">.*?</footer>', lambda m: footer, p, count=1, flags=re.S)
    out.append(p)

CSS = (SITE / 'index-v2.html').read_text(encoding='utf-8')
IDS = [i for i in MAIN if i not in ('cover', 'thanks')]
def sel(t): return ','.join([f'body.edition-v2 #{i} {t}' for i in IDS] + [f'body.edition-v2 .v3p {t}'])
UNI = (sel('[class*="-stripes"]') + ',' + sel('[class*="-corner"]') + ',' + sel('[class*="-topbar"]') + ',' + sel('.frame:before') + '{display:none!important}'
       + sel('.slide-title') + '{position:absolute!important;top:92px!important;left:64px!important;right:64px!important;width:auto!important;padding:2px 0 2px 24px!important;'
       'border:0!important;border-left:8px solid #b71c1c!important;font-size:40px!important;line-height:1.15!important;font-weight:700!important;letter-spacing:-.012em!important;'
       'color:#102a43!important;white-space:normal!important;z-index:3}'
       + sel('.slide-title em') + '{color:#b71c1c!important;font-style:normal!important}'
       + sel('.content') + '{top:176px!important;bottom:112px!important}'
       + 'body.edition-v2 #service .sv-sub{top:150px!important;left:96px!important;right:64px!important;font-size:19px!important}'
       + 'body.edition-v2 #service .content{top:196px!important}'
       + 'body.edition-v2 #team .tm-sub{position:absolute!important;top:150px!important;left:96px!important;right:64px!important;font-size:19px!important}'
       + 'body.edition-v2 #team .content{top:196px!important}:root{--red:#b71c1c}')
V3CSS = '<style id="v3-style">' + UNI + (Path(__file__).parent / 'v3-extra.css').read_text(encoding='utf-8') + '</style>'

h = head.replace('<title>ParkFlow | Member parking pilot · V2</title>', '<title>ParkFlow | Priority parking pilot · V3</title>')
h = h.replace('ParkFlow member parking: product', 'ParkFlow priority parking: product')
h = h.replace('</head>', V3CSS + '</head>', 1)
body = ''.join(out)
body = re.sub(r'<span aria-label="ParkFlow" class="wordmark">park<span>flow</span><svg.*?</svg></span>', '<span aria-label="ParkFlow" class="wordmark pf2">parkflow<b>//</b></span>', body, flags=re.S)
(SITE / 'index-v3.html').write_text(h + body + tail, encoding='utf-8')
print('slides', len(order), 'main', len(MAIN), 'capex', CAPEX, 'be', round(be_op, 1), round(be_5, 1), round(be_3, 1), 'gap', round(gap), 'gto', round(gto_lo), round(gto_hi), 'vo', round(1/vo_5, 1), round(1/vo_15, 1))

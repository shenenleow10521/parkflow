"""Build an isolated, reference-led consulting deck. Never writes site-vnext.

All financial exhibits share booking_economics.py's constants. Existing experiment
outputs are used as recorded; the builder does not rerun or alter experiments.
"""
from __future__ import annotations

from html import escape
import hashlib
import json
import math
from pathlib import Path
import shutil

from booking_economics import economics, UPFRONT, ANNUAL_RUNNING
from consulting_art_direction import apply_direction, wordmark

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site-consulting"
ORIGINAL = ROOT / "site-vnext" / "index.html"
BASELINE = "62EB8B3AA1CE971016ABECEE50D28017F735CBF88E0E1A0D0D8FA52D3092C740"
BLUE, NAVY, GREY, PALE = "#245bd8", "#102a43", "#8795a7", "#e4e6e9"
SOURCES = {
    "S1": ("KL East Mall official parking information", "https://www.simedarbyproperty.com/malls/kleast-mall/"),
    "S2": ("1 Utama ONECARD official FAQ", "https://www.onecard.com.my/Home/FAQ"),
    "S3": ("Sunway Pyramid official FAQ", "https://www.sunwaypyramid.com/faq"),
    "S4": ("Vase.ai, Malaysia Shopping Mall Report 2026 (n=500)", "https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026"),
    "S5": ("SDP Q4 FY2025 quarterly report", "https://www.simedarbyproperty.com/sites/default/files/2026-02/Quarterly%20Report%20Q4%20FY2025.pdf"),
    "S6": ("AAC current ANPR product listings", "https://store.aacgroup.com.my/?p=list_product&search=anpr"),
    "S7": ("Viskou DS-TVL224 display product", "https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows"),
    "S8": ("Malaysia PDP official Act/guidelines index", "https://www.pdp.gov.my/en/akta709/"),
    "S9": ("CNRPark dataset, CNR institute record", "https://openportal.isti.cnr.it/doc?id=people______%3A%3A82a7de1e67ac2d1a64791ab662b78bfb"),
    "S10": ("UCI Parking Birmingham dataset", "https://archive.ics.uci.edu/dataset/482/parking%2Bbirmingham"),
    "M1": ("ParkFlow shared booking economics", "../presentation/booking_economics.py"),
    "M2": ("ParkFlow policy simulation, recorded output", "../analysis/simulate_pooling_results.txt"),
    "M3": ("ParkFlow ensemble back-test, recorded output", "../analysis/backtest_ensemble_results.txt"),
    "M4": ("ParkFlow camera benchmark, recorded output", "../analysis/cv_benchmark_results.txt"),
}
R = economics()
GAP5, GAP3 = UPFRONT / 5 - R["contribution"], UPFRONT / 3 - R["contribution"]
SLIDES = []


def money(value, decimals=0):
    return ("−" if value < 0 else "") + f"RM{abs(value):,.{decimals}f}"


def tag(text, proposed=False):
    return f'<span class="tag{" proposed" if proposed else ""}">{text}</span>'


def module(title, body, cls=""):
    return f'<div class="col {cls}"><h3 class="module-title">{title}</h3>{body}</div>'


def cols(left, right, cls=""):
    return f'<div class="cols {cls}">{left}{right}</div>'


def table(headers, rows, widths=None, classes=None):
    cg = '<colgroup>' + ''.join(f'<col style="width:{v}%">' for v in widths) + '</colgroup>' if widths else ''
    body = ''.join(f'<tr class="{(classes or {}).get(i, "")}">' + ''.join((f'<td class="{v[1]}">{v[0]}</td>' if isinstance(v,tuple) else f'<td>{v}</td>') for v in row) + '</tr>' for i, row in enumerate(rows))
    return '<table>' + cg + '<thead><tr>' + ''.join(f'<th scope="col">{v}</th>' for v in headers) + '</tr></thead><tbody>' + body + '</tbody></table>'


def bullets(items):
    return '<ul>' + ''.join(f'<li>{item}</li>' for item in items) + '</ul>'


def strip(text):
    return f'<div class="decision-strip">{text}</div>'


def chart(svg, caption=""):
    return '<figure class="chart">' + svg + (f'<figcaption class="chart-caption">{caption}</figcaption>' if caption else '') + '</figure>'


def svg_wrap(parts, height=440, label="Chart"):
    return f'<svg viewBox="0 0 900 {height}" role="img" aria-label="{escape(label, quote=True)}"><g font-family="Public Sans,Arial,Helvetica,sans-serif" fill="#102a43">' + ''.join(parts) + '</g></svg>'


def txt(x, y, text, size=23, colour="#1a1a1a", anchor="middle", weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{colour}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(text))}</text>'


def waterfall(values, labels, max_value, units="RM thousands"):
    parts = [txt(20, 24, units, 18, "#595959", "start")]
    ybase, plot_h = 340, 265
    for tick in range(0, 5):
        value = max_value * tick / 4
        y = ybase - value / max_value * plot_h
        parts += [f'<line x1="65" y1="{y}" x2="885" y2="{y}" stroke="#e4e6e9"/>', txt(53, y + 6, f"{value / 1000:g}", 18, "#595959", "end")]
    running = 0
    step = 800 / len(values)
    for i, value in enumerate(values):
        x = 75 + i * step
        total = i == len(values) - 1
        start = 0 if i == 0 or total else running + min(value, 0)
        top = start + abs(value)
        h = abs(value) / max_value * plot_h
        y = ybase - top / max_value * plot_h
        color = BLUE if total else (NAVY if value >= 0 else GREY)
        parts.append(f'<rect x="{x}" y="{y}" width="{step * .66}" height="{h}" fill="{color}"/>')
        parts.append(txt(x + step * .33, y - 13, money(value / 1000, 1) + 'k', 23, weight=700))
        for j, line in enumerate(labels[i].split('|')):
            parts.append(txt(x + step * .33, 373 + j * 25, line, 20))
        running = value if i == 0 or total else running + value
        if not total:
            cy = ybase - running / max_value * plot_h
            parts.append(f'<line x1="{x + step * .66}" y1="{cy}" x2="{x + step}" y2="{cy}" stroke="#8e949d"/>')
    return svg_wrap(parts, label="Financial waterfall, " + ', '.join(f"{l.replace('|',' ')} {money(v)}" for l, v in zip(labels, values)))


def spend_chart():
    parts = [txt(25, 25, 'Recalled spend per mall visit (RM)', 21, "#595959", "start")]
    for yval in [0, 100, 200, 300]:
        y = 345 - yval * .8
        parts += [f'<line x1="95" y1="{y}" x2="870" y2="{y}" stroke="#e1e3e7"/>',txt(80, y+6, yval, 20, "#595959", "end")]
    for x,v,label,c in [(240,195,'1–2 visits / month',GREY),(580,327,'5+ visits / month',BLUE)]:
        parts += [f'<rect x="{x}" y="{345-v*.8}" width="170" height="{v*.8}" fill="{c}"/>',txt(x+85,325-v*.8,f'RM{v}',29,weight=700),txt(x+85,385,label,22)]
    parts.append(txt(865,65,'+68%',29,BLUE,'end',700))
    return svg_wrap(parts, label='Survey association: RM195 recalled spend for 1–2 visits per month; RM327 for 5+ visits, approximately 68 percent higher.')


def recovery_chart():
    parts = [txt(15,25,'Annual net contribution required (RM thousands)',20,"#595959","start")]
    scale = 790 / 30000
    for i,(years,gap) in enumerate([(5,GAP5),(3,GAP3)]):
        y = 95 + i * 155
        parts.append(txt(15,y-20,f'{years}-year simple recovery',25,anchor='start',weight=700))
        w=R['contribution']*scale
        parts += [f'<rect x="15" y="{y}" width="{w}" height="65" fill="{NAVY}"/>',f'<rect x="{15+w}" y="{y}" width="{gap*scale}" height="65" fill="#e4e6e9"/>',txt(15+w/2,y+40,'7.8k',24,'#ffffff',weight=700),txt(15+w+gap*scale/2,y+40,f'+{gap/1000:.1f}k',24,weight=700),txt(15+(R['contribution']+gap)*scale,y+95,f'Total {money(UPFRONT/years,0)} / year',21,anchor='end')]
    return svg_wrap(parts, 410, 'Five-year recovery needs RM8,524.60 additional net benefit per year; three-year recovery needs RM19,391.27.')


def forecast_chart():
    parts=[txt(20,25,'MAE (% of car-park capacity; lower is better)',20,"#595959","start")]
    for v in [0,2,4,6]:
        y=340-v*44
        parts += [f'<line x1="70" y1="{y}" x2="875" y2="{y}" stroke="#e4e6e9"/>',txt(55,y+6,str(v)+'%',19,"#595959","end")]
    for i,(baseline,ensemble) in enumerate([(5.26,1.41),(5.34,2.07),(5.40,2.63)]):
        x=160+i*260
        for j,(val,c) in enumerate([(baseline,GREY),(ensemble,NAVY)]):
            xx=x+j*83
            parts += [f'<rect x="{xx}" y="{340-val*44}" width="65" height="{val*44}" fill="{c}"/>',txt(xx+32.5,325-val*44,f'{val:.2f}',23,weight=700)]
        parts.append(txt(x+75,385,f'{30+30*i} minutes',23))
    return svg_wrap(parts,label='Forecast MAE: last-week versus ensemble at 30, 60 and 90 minutes.')


def booking_sensitivity():
    rows=[]
    for peak in [10,20,30,40,50]:
        row=[str(peak)]
        for weekday in [2.5,7.5,12.5]:
            v=economics(peak,weekday)['contribution']
            cls='base' if peak==30 and weekday==7.5 else ('neg' if v<0 else 'pos')
            row.append((f'<span class="num">{money(v/1000,1)}k</span>',cls))
        rows.append(row)
    html=table(['Peak bookings / day','2.5 weekday / day','7.5 weekday / day','12.5 weekday / day'],rows,[28,24,24,24])
    # Highlight the exact base-case cell without changing financial values.
    html=html.replace('<span class="num">RM7.8k</span>','<strong class="key">RM7.8k · base</strong>')
    return '<div class="heatmap">'+html+'</div>'


def retention_table(gap=GAP5):
    rows=[]
    for basket in [195,260,327]:
        values=[math.ceil(gap/(52*basket*capture)) for capture in [.03,.05,.08]]
        rows.append([f'RM{basket}']+[(str(v),'neg' if v>20 else ('pos' if v<=12 else '')) for v in values])
    return '<div class="heatmap">'+table(['Spend / visit','3% capture','5% capture','8% capture'],rows,[28,24,24,24])+'</div>'


def add(id,section,title,takeaway,body,sources=(),note='',cls='',appendix=False):
    SLIDES.append(dict(id=id,section=section,title=title,takeaway=takeaway,body=body,sources=sources,note=note,cls=cls,appendix=appendix))


def build_content():
    add('cover','Overview','', '', '''<h1>Priority parking.<br>A measurable member benefit.</h1><p class="cover-deck">ParkFlow: a bounded operating and investment case for KL East Mall.</p><p class="cover-meta">Sime Darby Property University Hackathon 2026<br>Team Hexa · Universiti Malaya<br>Consulting edition · November 2026</p><aside class="cover-mark"><strong>THE DECISION</strong><p>Validate a member Priority Zone before committing to portfolio scale.</p><p>One site. One operating policy.<br>One reconciled value case.</p></aside>''',cls='cover')

    people=[('SE','Leow Shen En','Team lead, product &amp; UI/UX','Data Science'),('PC','Pohyi Chong','Forecasting &amp; ML models','Data Science'),('IT','Isaac Teo','Data analysis &amp; simulation','Data Science'),('JS','Lee Jia Shern','Business case &amp; finance','Actuarial Science'),('ZL','Choong Zhuo Lin','AI engineering &amp; prototype','Artificial Intelligence')]
    add('team','Overview','TEAM HEXA','Five Universiti Malaya students combining operating design, analytics and commercial evaluation.', '<div class="team-grid">'+''.join(f'<article class="person"><div class="initial">{a}</div><h3>{n}</h3><p class="role">{r}</p><p class="study">{s}</p></article>' for a,n,r,s in people)+'</div>'+strip('Delivery focus: a working prototype, transparent evidence and an investment decision that SDP can scrutinize.'),cls='opening')

    add('executive','Overview','EXECUTIVE RECOMMENDATION','Approve pilot preparation, then release deployment funding against a confirmed scope and measurement plan.',
        table(['Decision lens','What the evidence supports','What must be established'],[
            ['Situation','KL East already has LPR parking; premium access needs a defined member and operating proposition.','Current peak occupancy, search time, eligible members and existing vendor access.'],
            ['Key question','Can a pooled Priority Zone improve the member experience without wasting capacity?','Live admission reliability, utilisation, member uptake and incremental value.'],
            ['Recommendation','Integrate verified capacity control with the member journey; use forecasts for planning and efficiency.','Validate the exact combined policy, including faults, no-shows and emergency procedures.'],
            ['Funding boundary','RM92k initial scope subtotal: RM81.5k upfront plus RM10.5k annual zone running allowance.','Obtain full installed quotes, support allocation, tax treatment and contingency before sanction.']
        ],[16,42,42])+strip('<strong>Scale decision:</strong> proceed only when the service promise and fully loaded economics both meet the agreed investment hurdle.'),['S1','M1'],note='Budget and demand are planning inputs; no KL East field pilot or signed commercial approval is represented.')

    add('context','Product','THE PARKING OPPORTUNITY','KL East already has LPR; ParkFlow must add a measurable member service above the existing payment journey.',
        cols(module('Existing foundation',bullets(['The official mall page publishes cashless parking and licence-plate recognition.','This creates a potential reuse path for identity, vehicle events and payment reconciliation.','Vendor permissions, API access and zone-level capacity are still to be surveyed.'])),module('The unmet question', '<p class="statement">Can a member rely on access near the lifts before setting off?</p><div class="steps"><div class="step"><h3>Member experience</h3><p>Measure search time, late arrivals and failed trips locally.</p></div><div class="step"><h3>Mall operations</h3><p>Protect accepted promises while keeping idle capacity visible.</p></div></div>')),
        ['S1'],note='A proposed B1 Priority Zone is a concept; existing zone availability and physical feasibility are not established.',cls='opening')

    add('alternatives','Product','MARKET ALTERNATIVES','Member parking, premium areas and reservations already exist; differentiation needs a precise operating promise.',
        table(['Alternative','Publicly documented capability','ParkFlow design implication'],[
            ['KL East existing parking','LPR and online parking payment.','Integrate with the incumbent system before procuring duplicate equipment.'],
            ['1 Utama ONECARD','Member preferred parking and LPR-linked access/payment.','A member-only zone is an established proposition, not a unique feature claim.'],
            ['Sunway Pyramid','Preferred parking areas; the FAQ also describes EV bay reservation via ParkEasy.','Do not claim that reservation is absent from competing malls. Compare use case and fulfilment.'],
            ['ParkFlow proposal','Pooled member-zone promises, verified admissions, advisory forecasts and an auditable exception log.','Test reliability, capacity efficiency and member value together at KL East.']
        ],[20,39,41])+strip('<strong>Positioning:</strong> an auditable service commitment and operating model, integrated with the mall’s existing systems.'),['S1','S2','S3'],note='Capabilities reflect reviewed public pages. Unmentioned capabilities are not treated as absent.')

    add('service','Product','SERVICE DESIGN','Book access to a shared zone, verify the vehicle, park in any available bay, then reconcile exit.',
        '<div class="flow">'+''.join(f'<article><h3>{h}</h3><p>{p}</p></article>' for h,p in [
            ('1 · Reserve','An eligible member selects an arrival window and registered plate.'),('2 · Verify','The gate checks identity, active entitlement and current capacity.'),('3 · Park','The member uses an available zone bay; no individual bay is assigned.'),('4 · Reconcile','Exit releases capacity and closes the booking and payment record.')])+'</div>'+strip('The member is promised zone access under published conditions. Arrival windows, cancellation/refund terms and exceptions require operator approval.'),cls='opening')

    add('member','Product','MEMBER JOURNEY','Keep booking, arrival guidance and support within one clearly explained journey.',
        cols('<div class="app-pair"><img src="assets/app-home.webp" alt="ParkFlow member app prototype, home and booking view"><img src="assets/app-guidance.webp" alt="ParkFlow member app prototype with parking guidance"></div>',module('What the member needs to know','<div class="steps"><div class="step"><h3>Before booking</h3><p>Eligibility, extra booking fee, arrival window and cancellation rule.</p></div><div class="step"><h3>Before entry</h3><p>Registered plate, route to the correct gate and a visible support option.</p></div><div class="step"><h3>If something changes</h3><p>Clear instructions for late arrival, plate mismatch, outage and refund.</p></div></div>'),'wide-left'),note='Prototype screens use simulated data. RM4 weekday / RM5 peak fees are a proposed pricing test, separate from normal parking charges.',cls='opening')

    add('operator','Product','OPERATOR JOURNEY','One shared event record should explain every admission, capacity change and manual exception.',
        cols('<div class="col"><img class="screenshot" src="assets/op-overview.webp" alt="ParkFlow operator dashboard prototype"><p class="note">Prototype interface, not a live KL East installation.</p></div>',module('Operating responsibilities',bullets(['Reconcile entry/exit counts with observed zone occupancy.','Monitor outstanding promises, no-shows and stale sensor data.','Record overrides with reason, operator identity and timestamp.','Keep assistance and emergency egress available during faults.','Review the daily service, utilisation and cash exceptions.'])),'wide-left'),cls='opening')

    add('admission','Product','ADMISSION CONTROL','Verified current capacity protects a promise; predicted departures alone must not create bookable space.',
        '<div class="equation"><div><b>8</b><span>verified free bays</span></div><i>−</i><div><b>5</b><span>outstanding promises</span></div><i>−</i><div><b>1</b><span>proposed safety buffer</span></div><i>=</i><div><b>2</b><span>additional promises now</span></div></div>'+cols(module('Conservative control layer',bullets(['Accept only when the reconciled capacity guard passes.','Reserve capacity against outstanding promises under the agreed booking horizon.','Freeze new commitments when counts or connectivity become uncertain.'])),module('Forecast advisory layer',bullets(['Advise members on likely general availability.','Support mode planning and staffing decisions.','Test any additional forecast-based utilisation policy separately.']))),['M2'],note='Illustrative operating rule. Buffer, promise horizon and fault handling need validation; simulation evidence uses policies with different admission logic.')

    add('integration','Product','INTEGRATION ARCHITECTURE','Start with reuse and reconciliation; add hardware only where existing coverage and interfaces are insufficient.',
        table(['Layer','Proposed connection','Required validation','Accountable role'],[
            ['Identity & booking','Mall member identity, plate registration, arrival entitlement and payment reference.','API/SSO access, ownership, settlement and duplicate-booking rules.','SDP Digital + operator'],
            ['Vehicle events','Existing entry/exit LPR; additional zone checkpoints where needed.','Zone-specific counts, timestamps, protocol and event replay.','Parking integrator'],
            ['Occupancy & forecasting','Existing CCTV coverage plus annotated local training/test frames.','Blind spots, indoor transfer, data freshness and drift.','AI team + mall ops'],
            ['Control & exceptions','Capacity guard, operator override log, intercom and offline procedure.','Controller fail states, physical boundary and emergency egress.','Operator + facilities'],
            ['Reporting & privacy','Pseudonymous member/vehicle join, restricted access and retention policy.','Approved processing roles, notice, retention and incident response.','SDP privacy + IT']
        ],[17,30,34,19]),['S1','S8'],note='Proposed architecture. Neither integration permission nor incumbent vendor compatibility has been established.')

    add('simulation','Evidence','SIMULATION RESULTS','The recorded forecast policy reduces idle capacity, but the proposed hard gate requires its own validation.',
        table(['Policy tested','Bookings honoured','Idle held bay-hours*','Peak use'],[
            ['No priority control','85.5%','0','98%'],['Fixed VIP section','99.9%','19','91%'],['Fixed rule: 5 safety bays','100.0%','23','87%'],['Forecast rule (recorded ParkFlow simulation)','100.0%','5','95%']
        ],[49,17,20,14],{3:'highlight'})+cols(module('What this establishes','<p>A policy trade-off under shared synthetic demand: reliability, general access and unused protected space must be evaluated together.</p>'),module('What remains open','<p>The forecast rule checks expected future availability. These results do not establish the efficiency of the new conservative current-capacity guard.</p>')),
        ['M2'],note='1,000 simulated busy days; 100-bay zone. *Free protected bay-hours only while walk-ins are refused; not all held capacity. No KL East field result.')

    add('forecast','Evidence','FORECASTING EVIDENCE','The ensemble beats a same-time-last-week baseline; indoor perception and KL East transfer remain separate tests.',
        cols(module('Historical occupancy back-test',chart(forecast_chart(),'48,112 forecasts · 30 Birmingham car parks · six-week test. Lower is better.')+'<div class="legend"><span><i class="grey"></i>Same time last week</span><span><i></i>Ensemble</span></div>'),module('Evidence boundary','<p><strong>60-minute MAE:</strong> 2.07% versus 5.34% of capacity, a 61.2% relative reduction.</p><div class="callout"><strong>Camera test:</strong> 99.05% patch accuracy on 78,270 patches from held-out cameras at one outdoor Italian site.</div><p><strong>Before deployment:</strong> test indoor lighting, pillars, occlusion, plate errors and occupancy drift at KL East.</p><p class="note">New camera views at the same location are not a new-site validation. Forecast and perception scores measure different tasks.</p>'),'wide-left'),['M3','M4','S9','S10'])

    add('member-value','Business','MEMBER VALUE CASE','Frequent visitors report higher baskets; parking must demonstrate that it causes additional valuable visits.',
        cols(module('Observed association',chart(spend_chart(),'Vase.ai 2026 consumer survey; total n=500. Recalled trip spending by visit frequency.')),module('Commercial interpretation',bullets(['Prioritize members whose repeat visits are valuable to the mall.','Separate tenant turnover from the landlord’s effective share.','Measure incremental trips against a comparable group or baseline.','Avoid converting the 68% basket difference directly into a parking-driven uplift.'])),'wide-left')+strip('<strong>Value bridge:</strong> additional visits × spend per visit × effective mall capture, less additional service and support costs.'),['S4'],note='Survey association is not causal and is not a KL East estimate. Effective capture is a finance-calibrated scenario.')

    add('investment','Business','PILOT INVESTMENT','RM92k is an initial scope subtotal; complete the installed scope and support estimate before approving funding.',
        cols(module('Initial planning scope',chart(waterfall([21500,60000,10500,92000],['Hardware &|installation','Production|integration','Year 1|zone running','Initial scope|subtotal'],100000),'Hardware RM21.5k + build RM60.0k + annual zone running RM10.5k.')),module('Complete the approval envelope',bullets(['Survey whether existing LPR/CCTV can be reused.','Price physical zone separation, barriers, controller and intercom interfaces.','Confirm cabling, power, network and commissioning.','Add central support, tax treatment and contingency.','Define warranty, maintenance and ownership at handover.'])),'wide-left')+strip('<strong>Procurement gate:</strong> no final installed-cost claim until scope, incumbent-system access and binding supplier quotes are reconciled.'),['M1','S1','S6','S7'],note='All amounts are planning allowances before unpriced scope, tax and contingency. Retailer listings do not establish installed cost.')

    add('booking-return','Business','BOOKING CASH CONTRIBUTION','The base case produces RM7.8k before central support, tax and capital recovery.',
        cols(module('Annual booking-fee bridge',chart(waterfall([R['gross'],-R['operator'],-R['processing'],-ANNUAL_RUNNING,R['contribution']],['Gross booking|fees','Operator|20% share','Processing|2% allowance','Zone running|allowance','Operating|contribution'],26000),'365-day illustration: 104 peak days and 261 weekday days; public holidays not separately reclassified.')),module('One shared model',table(['Driver','Base planning input'],[['Peak demand','30 bookings/day × RM5'],['Weekday demand','7.5 bookings/day × RM4'],['Operator allocation','20% of booking fees'],['Processing allowance','2% of booking fees'],['Annual zone OPEX','RM10,500']],[45,55])+'<p class="note">Booking fees are additional to ordinary parking charges. Demand, operator share and payment cost are unvalidated inputs.</p>'),'wide-left'),['M1'],note=f'Exact arithmetic: gross {money(R["gross"],2)} less {money(R["operator"],2)}, {money(R["processing"],2)} and RM10,500 = {money(R["contribution"],2)}. Not fully loaded profit.')

    add('booking-sensitivity','Business','BOOKING VOLUME SENSITIVITY','Demand and central support can change the sign of the contribution; a single base case is insufficient.',
        cols(module('Annual contribution before central support',booking_sensitivity()+'<p class="note">RM thousands; 104 peak / 261 weekday days. Same fees, shares and OPEX as the base case.</p>'),module('What changes the decision',table(['Annual support allocation','Base contribution after allocation'],[['RM0','RM7,775'],['RM12,000','−RM4,225'],['RM24,000','−RM16,225']],[50,50])+'<p>Record actual support minutes, incidents and payment costs. A positive zone contribution does not establish a standalone platform return.</p><p class="note">Support rows are sensitivity cases, not staffing estimates.</p>'),'wide-left')+strip('<strong>Pilot measurement:</strong> paid conversion and bookings per eligible member, measured alongside utilisation and member outcomes.'),['M1'])

    add('recovery','Business','CAPITAL RECOVERY','The base case needs additional annual net benefits of RM8.5k for five-year simple recovery.',
        cols(module('Annual contribution hurdle',chart(recovery_chart(),'RM81,500 initial capital; straight-line comparison, no discounting or terminal value.')),module('How to close the gap',bullets(['Verify genuinely incremental visits and the associated landlord capture.','Quantify operational savings only after staff effort is measured.','Treat sponsorship and external contracts as separate, signed upside.','Include central support and any extra capital before testing the final hurdle.'])),'wide-left')+strip('<strong>Decision:</strong> agree SDP’s actual hurdle rate and investment period before presenting an NPV, IRR or claimed payback.'),['M1'],note=f'Base booking-only simple recovery ≈{UPFRONT/R["contribution"]:.1f} years before excluded costs. Five/three years are comparison cases, not SDP-approved thresholds.')

    add('retention','Business','RETENTION SENSITIVITY','The five-year recovery gap requires 7–29 additional weekly visits across the illustrated capture scenarios.',
        cols(module('Weekly visits required to close the gap',retention_table()+'<p class="note">Rounded up. Pale red = more than 20 visits; blue-grey = 12 or fewer. Cells share the RM8,524.60 annual net benefit gap.</p><div class="callout"><strong>Worked case:</strong> RM8,524.60 ÷ (52 × RM260 × 5%) = 12.61, rounded up to <strong>13 additional visits a week</strong>.</div>'),module('Validate the conversion to value',bullets(['RM195 and RM327 are recalled survey baskets, not measured KL East baskets.','RM260 is a midpoint illustration; 3%, 5% and 8% capture rates are scenarios.','Effective capture must reflect actual leases and ancillary net contribution.','Use incremental visits, avoiding double counting normal parking income or existing loyalty visits.'])),'wide-left')+strip('<strong>Formula:</strong> weekly visits = annual contribution gap ÷ (52 × spend per visit × effective mall capture).'),['M1','S4'],note='Capture is an effective net-to-mall scenario, not a verified GTO rental rate. Any incremental support cost raises the required visits.')

    add('commercial','Business','COMMERCIAL OPERATING MODEL','A named sponsor, an operating partner and a signed integration scope are prerequisites to paid deployment.',
        table(['Workstream','SDP / mall role','Partner / team role','Decision evidence'],[
            ['Sponsor & eligibility','Mall management owns the service proposition and member cohort.','Team supports co-design and prototype workflows.','Named sponsor, eligible cohort and published member terms.'],
            ['Parking operations','Operator owns gate routines, exceptions, staffing and normal parking settlement.','Integrator connects approved checkpoints and controller.','Operating agreement, override SOP and end-to-end reconciliation.'],
            ['Technology & privacy','Digital/IT approves interfaces, access, deployment and processing roles.','Team supplies software; vendor confirms integration and warranty.','API/SSO access, data map, security review and acceptance tests.'],
            ['Finance & procurement','Finance verifies capture, full cost and hurdle; procurement approves quotes.','Suppliers submit installed scope and support commitments.','Comparable quotes, support allocation and investment memorandum.']
        ],[17,29,27,27])+strip('<strong>Expansion trigger:</strong> repeatable fulfilment and full-cost economics at KL East, followed by site-specific feasibility and approval.'),['S1','S8'],note='Accountabilities are proposed role assignments; no current contract, supplier selection or commitment is implied.')

    add('pilot-design','Implementation','PILOT DESIGN','Separate service reliability from commercial uplift, with a baseline and a control comparison for each.',
        table(['Test','Baseline / comparison','Measurement','What it resolves'],[
            ['Service promise','Replay the exact admission policy; then supervise live booked arrivals.','Accepted arrivals served, count drift, plate errors, override and fault records.','Whether the deployed gate policy protects commitments in real conditions.'],
            ['Capacity efficiency','Compare matched peak windows; block or randomize safe approved policy days.','Idle protected bay-hours while demand is refused, utilisation and turn-aways.','Whether efficiency gains transfer from simulation without degrading reliability.'],
            ['Member value','Compare eligible participants with a matched/control cohort and pre-period.','Paid uptake, repeat visits, satisfaction and lease-calibrated capture.','Whether the service adds visits/value beyond existing member behaviour.'],
            ['Full delivery cost','Compare actual service effort and spend against the quoted scope.','Support minutes, supplier cost, refunds, payment fees and annualized run rate.','Whether the complete case clears SDP’s agreed investment hurdle.']
        ],[17,29,29,25]),['M2','M1'],note='Proposed design. Eligibility bias, seasonal demand, event mix and day-level clustering must be addressed in analysis; an eight-week trial is not guaranteed to prove retention.')

    add('scorecard','Implementation','PILOT SCORECARD','Agree the baseline, denominator and decision rule before the first paid booking.',
        table(['Decision dimension','Metric / denominator','Proposed decision rule','Owner'],[
            ['Service reliability','Served accepted arrivals ÷ all accepted arrivals; report confidence interval.','Agree target and minimum observation volume; investigate every service failure.','Operator + mall ops'],
            ['Demand','Paid bookings ÷ eligible exposed members; repeat usage by cohort.','Test RM4/RM5 willingness to pay; distinguish trial incentives from recurring demand.','Loyalty + finance'],
            ['Capacity','Idle protected bay-hours while demand is refused; peak occupancy.','Improve against a valid comparator without reducing the service commitment.','Mall ops + analyst'],
            ['Incremental value','Additional visits and net mall capture, adjusted for cohort differences.','Clear the full-cost hurdle with credible evidence; otherwise adapt or stop.','Finance + loyalty'],
            ['Operating readiness','Manual interventions, outages, stale counts and unresolved data exceptions.','Signed SOP, fault drills, privacy review and auditable reconciliation.','IT + privacy + operator']
        ],[20,31,32,17]),note='These are proposed acceptance principles, not agreed numerical SLAs. An observation window must be extended if evidence is insufficient.')

    add('risk','Implementation','OPERATING RISKS & RESPONSES','Translate each failure mode into an immediate response, a responsible role and a pre-launch test.',
        table(['Trigger','Operating response','Evidence before launch','Owner'],[
            ['Plate mismatch / count drift','Route to assisted verification; log exception and reconcile before adding promises.','Local plate test, manual count audit, duplicate event and missed-exit replay.','Operator + integrator'],
            ['Network / controller failure','Pause new commitments; apply agreed offline SOP and preserve emergency egress.','Fail-state drill, reconciliation after restart and contact escalation.','IT + facilities'],
            ['No-show / late arrival / overstay','Apply published grace, cancellation and refund policy; record actual dwell and arrival.','Member terms, entitlement expiry and capacity stress replay.','Operator + loyalty'],
            ['Member / vehicle data incident','Restrict access, retain evidence and activate SDP privacy incident process.','Data map, notice, controller/processor responsibilities and approved retention.','SDP privacy + IT'],
            ['Low demand / negative economics','Review price, cohort and operating scope; do not expand on unproven value.','Conversion funnel, fully allocated cost and signed decision record.','Finance + sponsor']
        ],[22,34,29,15]),['S8'],note='Deployment obligations depend on the actual processing and operator arrangements; this is an implementation workstream, not a legal certification.')

    add('horizons','Implementation','THREE HORIZONS','Prove the service first, standardize the SDP operating system second, commercialize only after repeatability.',
        '<div class="horizons headings">'+''.join(f'<article class="horizon"><p class="period">{p}</p><h3>{t}</h3></article>' for p,t in [('H1 · Months 0–6','Prove at KL East'),('H2 · Months 6–24','Build the SDP system'),('H3 · Months 24–60','Scale a contracted platform')])+'</div><div class="roadmap-matrix">'+table(['Workstream','Horizon 1','Horizon 2','Horizon 3'],[
            ['Service delivery','Survey, baseline, eight-week trial and signed operator SOP.','Qualify Elmina Lakeside and KLGCC; standardize site onboarding.','Replicate through contracted external mall groups.'],
            ['Technology & data','Reconcile entry/exit; validate local camera and forecast performance.','Common interfaces, reporting, incident playbooks and data governance.','Versioned APIs, support tiers and repeatable customer integration.'],
            ['Commercial basis','Bounded pilot budget; settle fee split and full delivery cost.','Site-specific capital approval; allocate shared platform support.','Negotiate fee, zones, hardware ownership, SLA and onboarding charges.'],
            ['Value gate','Service evidence and complete economics clear the agreed hurdle.','Repeatable delivery and sustainable cost across approved SDP sites.','Signed demand and positive margin after onboarding and support.']
        ],[17,27.7,27.7,27.6])+'</div>'+strip('<strong>Portfolio boundary:</strong> three wholly owned malls. JV opportunities require separate approvals and economic treatment.'),['S5'],note='Planning horizons and proposed milestones, not committed deployment or revenue forecasts.')

    add('decision','Implementation','THE PILOT DECISION','Approve preparation and a gated investment review; release deployment funding once the full scope is defined.',
        cols(module('Requested approvals',table(['Decision','Deliverable'],[['Sponsor','Nominate KL East owner and parking operator counterpart.'],['Discovery access','Authorize site survey and technical/vendor feasibility discussions.'],['Measurement','Agree baseline, cohort, data access and decision criteria.'],['Procurement review','Obtain installed quotes and the complete funding envelope.']],[30,70])),module('Return to the committee with',bullets(['A feasible zone boundary and validated integration path.','One reconciled model covering capital, running cost and support.','A signed operator SOP and an approved member proposition.','A baseline/test plan and clear go, adapt or stop criteria.'])+'<div class="callout red"><strong>Planning reference:</strong> RM92k initial scope subtotal. Final funding is subject to unpriced scope, tax, contingency and verified value.</div>')),
        ['M1'],note='The deck requests a bounded pilot process; it does not imply an agreed contract, committed budget or proven commercial return.')

    add('thanks','Overview','','','<h2>Thank You</h2><p>Team Hexa · ParkFlow</p><p class="note">Questions &amp; discussion<br>Supporting appendix follows in the same deck.</p>',cls='thank')

    add('a-cost','Appendix','APPENDIX | COST & SCOPE','Keep planning allowances distinct from validated supplier prices and final installed scope.',
        table(['Cost line','Allowance','Basis / validation status','Before commitment'],[
            ['Entry / exit ANPR','RM6,000','Legacy installed allowance; current AAC listings show multiple price labels.','Confirm reuse, exact model, warranty and installed quote.'],
            ['Compact LED sign','RM4,000','Product option exists; the old RM2,033 price was not revalidated.','Confirm display size, viewing distance, interfaces and installed price.'],
            ['Blind-spot cameras','RM4,000','Coverage-dependent allowance, not a counted site requirement.','Survey existing CCTV before adding cameras.'],
            ['Cabling / electrical','RM7,500','Engineering allowance; installation distance not surveyed.','Quote PoE, conduit, network and power works.'],
            ['Software integration','RM60,000','Prototype-to-production estimate; incumbent access not confirmed.','Define identity, payments, controller scope and acceptance.'],
            ['Annual zone OPEX','RM10,500','Hosting, messaging and upkeep allowance.','Measure usage; allocate support, tax and contingency separately.']
        ],[23,13,33,31])+strip('<strong>Not yet priced:</strong> zone barriers/boundary, controller/intercom changes, additional support, taxes, contingency and any extra privacy/IT deployment requirements.'),['S6','S7','M1'],cls='compact',appendix=True)

    add('a-finance','Appendix','APPENDIX | MODEL RECONCILIATION','Every sensitivity is derived from one fee, share, capital and operating-cost definition.',
        cols(module('Pilot base model',table(['Calculation','Annual RM'],[['104 × 30 × RM5 + 261 × 7.5 × RM4','23,430.00'],['Operator share: 20% of booking fees','(4,686.00)'],['Processing: 2% of booking fees','(468.60)'],['Annual zone OPEX','(10,500.00)'],['Zone operating contribution','7,775.40'],['Capital required / 5 years','16,300.00'],['Additional net benefit required','8,524.60']],[72,28],{4:'total',6:'total'})),module('What must not be mixed',bullets(['RM92k includes Year 1 running cost; RM81.5k is the upfront capital used in recovery comparisons.','The old RM9,360 retention target is replaced with the model-derived RM8,524.60 five-year gap.','Partner margin uses the same annual zone OPEX; cloud-only cost is not a complete contribution margin.','No NPV/IRR from an older four-mall model is carried into this pilot case.','Support, tax, contingency and additional capital remain explicit exclusions.']))),['M1'],cls='compact',appendix=True)

    partner_rows=[]
    for rate in [0,2,4,6]:
        n=6*rate
        partner_rows.append([f'{rate} / year',str(n),money(n*45000),money(n*15750),money(n*29250)])
    add('a-partners','Appendix','APPENDIX | PARTNER PACE','Consistent zone OPEX lowers the illustrated partner contribution to RM29,250 per mall before central costs.',
        table(['Sign-ups from Year 2','Year 7 live malls','Annual fees in Year 7','Annual zone OPEX','Contribution before central costs'],partner_rows,[20,16,21,21,22])+cols(module('Transparent assumptions','<p>Six years of additions, 1.5 zones per partner, RM45,000 annual fee and RM10,500 annual running allowance per zone. Zero churn is assumed for this illustration.</p>'),module('Before using as an investment case','<p>Verify signed pricing, churn, onboarding, support, hardware ownership, taxes and shared-platform allocation. These rows are annual run-rate scenarios, not cumulative cash or NPV.</p>')),
        ['M1'],note='RM45,000 − (1.5 × RM10,500) = RM29,250. No signed external-mall demand is represented.',appendix=True)

    add('a-retention','Appendix','APPENDIX | RETENTION HURDLES','Three-year recovery needs a larger incremental visit base than the five-year comparison.',
        cols(module('Five-year gap: RM8,524.60 / year',retention_table(GAP5)),module('Three-year gap: RM19,391.27 / year',retention_table(GAP3)))+strip('<strong>Both tables:</strong> required additional weekly visits, rounded up; 52 weeks × basket × effective net capture. Add support costs before setting a final hurdle.'),['M1','S4'],note='RM195 / RM327 survey baskets; RM260 illustrative midpoint. 3–8% net capture scenarios are not verified SDP rent terms.',appendix=True)

    add('a-method','Appendix','APPENDIX | TECHNICAL VALIDATION','Back-testing, held-out-camera testing and synthetic policy trials answer different questions.',
        table(['Experiment','Recorded evidence','Boundary','Next validation'],[
            ['Occupancy forecast','48,112 forecasts; six weeks; 30 Birmingham car parks; 60-minute MAE 2.07%.','Historical UK data; no KL East deployment result.','Local holdout by time, peak events and zone; calibrate intervals and drift.'],
            ['Camera perception','78,270 patches; cameras 6–9 held out; accuracy 99.05%.','One outdoor Italian site; 540 occupied patches called free.','Indoor local labels, safety-critical false-free rates and count reconciliation.'],
            ['Booking policy','1,000 synthetic busy days; forecast rule 100.0% baseline fulfilment.','Forecast-based future capacity differs from proposed hard current-capacity guard.','Replay deployed rule; validate queue, faults, no-shows and overstays.'],
            ['Stress policy','Combined scenario: forecast policy 99.62%; fixed VIP 93.44%.','Scenario-specific assumptions; not “everything that can go wrong”.','Test wider conditions and field fault drills; report failures explicitly.']
        ],[18,29,27,26]),['M2','M3','M4','S9','S10'],cls='compact',appendix=True)

    add('a-evidence','Appendix','APPENDIX | EVIDENCE & OPEN GAPS','Close documentary gaps through research; close site and commercial gaps through the pilot.',
        table(['Claim / input','Evidence class','Treatment in this deck','Outstanding deliverable'],[
            ['KL East has LPR parking','Official public fact','Reuse-first integration approach.','Vendor permissions and zone-level interfaces.'],
            ['Higher frequent-visitor basket','Survey association','Context for cohort selection, not causal uplift.','Local incremental visits and net capture.'],
            ['Reliable, efficient policy','Internal simulation','Full comparison with explicit policy boundary.','Exact deployed-rule test and live fulfilment.'],
            ['RM92k planning subtotal','Engineering estimate','Incomplete installed scope, not a final quote.','Supplier scope, support allocation and contingency.'],
            ['Three-mall SDP rollout','Portfolio fact + proposed plan','Three wholly owned assets; each rollout gated.','Site feasibility, authority and business case.'],
            ['External partner value','Illustrative economics','Consistent OPEX; no forecasted NPV claim.','Signed fees, demand, onboarding, churn and support.']
        ],[24,18,29,29]),['S1','S4','S5','M1','M2'],cls='compact',appendix=True)

    public_ids=[k for k in SOURCES if k.startswith('S')]
    sourcehtml='<div class="sources-list">'+''.join(f'<div><b>{key} · <a href="{SOURCES[key][1]}" target="_blank" rel="noopener">{SOURCES[key][0]}</a></b><p class="note">Public source checked 7 November 2026. Scope and limitations are recorded in the evidence register.</p></div>' for key in public_ids)+'</div>'
    add('a-sources','Appendix','APPENDIX | PUBLIC SOURCES','Primary sources support facts; they do not validate ParkFlow’s untested commercial assumptions.',sourcehtml,note='Full research notes: docs/deck-design-analysis/gaps-and-evidence.md. Former AAC 2025 PDF returned 404; legacy list prices were not promoted to live quotes.',cls='compact',appendix=True)

    add('a-audit','Appendix','APPENDIX | ANALYSIS & DESIGN RECORD','The consulting edition is isolated from the original deck and uses a documented, measurable layout system.',
        cols(module('Internal analysis files',bullets([f'<a href="{SOURCES[k][1]}">{k} · {SOURCES[k][0]}</a>' for k in ['M1','M2','M3','M4']])+'<p class="note">Recorded research outputs are not independent audits. Calculation and deployment boundaries remain visible throughout.</p>'),module('Design and evidence record',bullets(['<a href="../guidance.md">guidance.md: measured grid, hierarchy, palette and density ramp.</a>','<a href="../docs/deck-design-analysis/gaps-and-evidence.md">Gap register: corrections, sources and remaining site evidence.</a>','Reference PDFs: 45 pages measured; original deck: 32 slides measured.','Opening remains lighter; business slides use comparative exhibits and explicit decision inputs.'])))+strip('<strong>Preservation:</strong> this edition has its own HTML, CSS, JavaScript and PDF. The current site-vnext deck and its assets remain unchanged.'),appendix=True)


def render():
    sections=['Overview','Product','Evidence','Business','Implementation','Appendix']
    output=[]
    for number,s in enumerate(SLIDES,1):
        source=' · '.join(f'<a href="{SOURCES[k][1]}" target="_blank" rel="noopener">{k}: {SOURCES[k][0]}</a>' for k in s['sources'])
        notes=(('Sources: '+source+'. ') if source else '')+s['note']
        title=f'<h2 class="slide-title">{s["title"]}</h2>' if s['title'] else ''
        takeaway=f'<p class="takeaway">{s["takeaway"]}</p>' if s['takeaway'] else ''
        footer='<span class="brand">'+wordmark()+'</span>'+''.join(f'<span class="{"active" if section==s["section"] else ""}">{section}</span>' for section in sections)+f'<span class="page">{number:02d} / {len(SLIDES):02d}</span>'
        output.append(f'<section class="slide {s["cls"]}" id="{s["id"]}" data-section="{s["section"]}" data-appendix="{str(s["appendix"]).lower()}" aria-label="{escape(s["title"] or ("Thank You" if s["id"]=="thanks" else "ParkFlow cover"))}"><div class="frame">{title}{takeaway}<div class="content">{s["body"]}</div><div class="source">{notes}</div><footer class="footer">{footer}</footer></div></section>')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="ParkFlow: a member parking service and measured pilot case for KL East Mall."><title>ParkFlow | Property &amp; product edition</title><link rel="preload" href="assets/public-sans.ttf" as="font" type="font/ttf" crossorigin><link rel="stylesheet" href="deck.css"><link rel="stylesheet" href="premium.css"></head><body><main>'+''.join(output)+'</main><nav class="controls" aria-label="Presentation controls"><button id="reading" aria-label="Toggle reading mode" aria-pressed="false">Aa</button><button id="previous" aria-label="Previous slide" disabled>←</button><button id="next" aria-label="Next slide">→</button></nav><script src="deck.js"></script></body></html>'


def main():
    before=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest().upper()
    assert sum([6000,4000,4000,7500])==21500
    assert 21500+60000==UPFRONT and UPFRONT+ANNUAL_RUNNING==92000
    assert round(R['gross'],2)==23430 and round(R['contribution'],2)==7775.40
    assert round(GAP5,2)==8524.60 and round(GAP3,2)==19391.27
    assert 45000-1.5*ANNUAL_RUNNING==29250
    assert math.ceil(GAP5/(52*195*.03))==29 and math.ceil(GAP5/(52*327*.08))==7
    # User edits to the original are allowed; the invariant is no change by this build.
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'assets').mkdir(exist_ok=True)
    for filename in ['app-home.webp','app-guidance.webp','op-overview.webp','priority-zone-pilot-concept.png']:
        shutil.copy2(ROOT/'site-vnext'/'assets'/filename,OUT/'assets'/filename)
    build_content()
    apply_direction(SLIDES, globals())
    (OUT/'index.html').write_text(render(),encoding='utf-8')
    model=dict(**R,upfront=UPFRONT,annual_zone_running=ANNUAL_RUNNING,recovery_gap_5y=GAP5,recovery_gap_3y=GAP3,partner_fee_assumed=45000,partner_zones_assumed=1.5,partner_contribution_before_central=45000-1.5*ANNUAL_RUNNING)
    (OUT/'model.json').write_text(json.dumps(model,indent=2),encoding='utf-8')
    assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest().upper()==before
    print(f'Built {OUT / "index.html"}: {len(SLIDES)} slides, {sum(not s["appendix"] for s in SLIDES)} main + {sum(s["appendix"] for s in SLIDES)} appendix.')
    print(f'Original deck unchanged: SHA256 {before} (matches analysis baseline: {before==BASELINE}).')
    print(json.dumps(model,indent=2))


if __name__=='__main__':
    main()

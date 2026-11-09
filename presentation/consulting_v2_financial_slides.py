"""Apply one V2 financial model and traceable commercial evidence to the HTML."""
import math

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

import build_consulting_deck as base
import consulting_v2_finance as f
from consulting_art_direction import detail_list
from consulting_v2_layout import body, export_svg, plot, put

MODEL = '<a href="../presentation/consulting_v2_finance.py">V2 calculation</a>'
RESEARCH = '<a href="financial-sources.md">Sources, scope and unresolved costs</a>'
BOUNDARY = 'Before unpriced zone equipment, central support, project taxes and contingency. Prices and uptake remain tests; no local return is established.'


def source(key):
    label, url = f.SOURCES[key]
    return f'<a href="{url}">{label}</a>'


def money(value, decimals=0):
    return base.money(value, decimals)


def curve():
    r = f.economics()
    unit = r['net'] / r['bookings']
    x = np.linspace(0, 11000, 250)
    fig, ax = plt.subplots(figsize=(14, 4.65))
    ax.axhline(0, color='#a8b7ca', lw=1)
    ax.axhline(f.UPFRONT/5, color='#53647a', lw=1.2, ls=(0, (5, 5)))
    ax.text(10900, f.UPFRONT/5+700, f'{money(f.UPFRONT/5)} / year · five-year capital reference',
            ha='right', color='#53647a', fontsize=12)
    ax.plot(x, x*unit-f.ANNUAL_RUNNING, color='#245bd8', lw=2.8)
    for i, (label, peak, weekday) in enumerate(f.SCENARIOS):
        r = f.economics(peak, weekday)
        ax.scatter([r['bookings']], [r['contribution']], s=65, color='#245bd8', edgecolor='white', zorder=4)
        ax.annotate(f'{label}\n{money(r["contribution"])} / year', (r['bookings'], r['contribution']),
                    xytext=(-16, 24), textcoords='offset points', fontsize=12, color='#102a43', ha='center')
    threshold = f.required_bookings(5)
    ax.scatter([threshold], [f.UPFRONT/5], s=45, color='#102a43', zorder=5)
    ax.annotate(f'Five-year threshold\n{math.ceil(threshold):,} paid bookings / year',
                (threshold, f.UPFRONT/5), xytext=(35, -57), textcoords='offset points',
                fontsize=12, color='#53647a', arrowprops={'arrowstyle':'-', 'color':'#8795a7'})
    ax.set(xlim=(0, 11200), ylim=(-12000, 31000))
    ax.set_xticks([0, 2000, 4000, 6000, 8000, 10000])
    ax.set_yticks([-10000, 0, 10000, 20000, 30000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:,.0f}'))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: ('−' if v<0 else '')+f'RM{abs(v)/1000:g}k'))
    ax.set_xlabel('Paid bookings per year · fixed RM4/RM5 reference mix', labelpad=12)
    ax.set_ylabel('Annual zone contribution', labelpad=12)
    ax.grid(axis='y', color='#d5dde7', lw=.65)
    fig.subplots_adjust(left=.09, right=.98, bottom=.2, top=.94)
    return export_svg(fig, 'v2-financial-thresholds')


def spending_benchmark():
    fig, ax = plt.subplots(figsize=(8.6, 3.7))
    ax.plot([195, 327], [.6, .6], color='#d5dde7', lw=5, zorder=1)
    ax.scatter([195, 327], [.6, .6], color=['#8795a7', '#245bd8'], s=[190, 260], zorder=3)
    for x, label, desc in [(195, 'RM195', '1–2 visits / month'), (327, 'RM327', '5+ visits / month')]:
        ax.text(x, .83, label, ha='center', fontsize=25, fontweight='bold', color='#102a43')
        ax.text(x, .32, desc, ha='center', fontsize=14, color='#53647a')
    ax.axvline(260, ymin=.24, ymax=.72, color='#8795a7', lw=1, ls=(0,(3,3)))
    ax.text(260, .03, '~RM260 national mean', ha='center', fontsize=13, color='#53647a')
    ax.text(261, 1.25, '+68% per trip', ha='center', fontsize=23, color='#245bd8')
    ax.set(xlim=(155, 365), ylim=(-.12, 1.55))
    ax.axis('off')
    fig.tight_layout(pad=1)
    return export_svg(fig, 'v2-spending-benchmark')


def turnover_rent_sensitivity():
    """Comparable gross-rent range; all plotted sales already clear lease floors."""
    rates=np.linspace(f.LEASE_RATE_LOW*100,f.LEASE_RATE_HIGH*100,240)
    sales=np.linspace(50,250,240)
    xx,yy=np.meshgrid(rates,sales)
    rent=xx/100*yy*1000
    fig,ax=plt.subplots(figsize=(14,4.6))
    filled=ax.contourf(xx,yy,rent,levels=[0,2500,5000,10000,15000,20000,25000,30000,40000],cmap='Blues')
    lines=ax.contour(xx,yy,rent,levels=[5000,10000,15000,20000,30000],colors='white',linewidths=.8)
    labels=ax.clabel(lines,inline=True,fontsize=13,fmt=lambda v:f'RM{v/1000:g}k')
    for label in labels:
        label.set_rotation(0)
        label.set_color('#102a43')
        label.set_bbox({'facecolor':'white','edgecolor':'none','alpha':.95,'pad':2})
    gap=f.recovery_gap(5)
    ax.contour(xx,yy,rent,levels=[gap],colors=['#102a43'],linewidths=1.7,linestyles='dashed')
    ax.text(5.3,243,f'Dashed: RM{gap/1000:.1f}k reference booking-only recovery gap',
            fontsize=12,color='#102a43',va='top',bbox={'facecolor':'white','edgecolor':'none','pad':7})
    ax.set_xticks([5,7.5,10,12.5,15],['5%','7.5%','10%','12.5%','15%'])
    ax.set_yticks([50,100,150,200,250],[f'RM{x}k' for x in [50,100,150,200,250]])
    ax.set_xlabel('Gross turnover-rent clause · published comparable range, not an SDP average',labelpad=14)
    ax.set_ylabel('Extra eligible tenant sales / year',labelpad=14)
    bar=fig.colorbar(filled,ax=ax,pad=.035,shrink=.9)
    bar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'RM{v/1000:g}k'))
    bar.set_label('Additional gross rent / year',labelpad=12)
    fig.subplots_adjust(left=.11,right=.96,top=.96,bottom=.17)
    return export_svg(fig,'v2-turnover-rent-sensitivity')


def apply_financial_revision(soup):
    r = f.economics()
    gap5 = f.recovery_gap(5)
    shared = f'Sources: {MODEL}; {RESEARCH}. '
    # Replace inherited finance citations throughout the final V2 only.
    for a in soup.select('a[href="../presentation/booking_economics.py"]'):
        a['href'] = '../presentation/consulting_v2_finance.py'
        a.string = 'V2 financial reference model'

    for selector in ['#executive .budget-reference', '#decision .decision-budget']:
        put(soup.select_one(selector), f'<b>RM{f.FIRST_YEAR/1000:.1f}k +</b><span>Reference new-zone subtotal<br>Two NEW zone LPR cameras included</span>')
    put(soup.select_one('#cover h1'),'Member parking<br>for SDP malls')
    put(soup.select_one('#cover .cover-context'),'ParkFlow · proposed member service')
    put(soup.select_one('#cover .cover-deck'),'Reserved access for members.<br>KL East Mall is a proposed first pilot.')
    put(soup.select_one('#cover .cover-credit>span'),'Universiti Malaya · revision 9 November 2026')
    put(soup.select_one('#executive .slide-title'),'SDP member-parking proposal')
    put(soup.select_one('#executive .recommendation h3'),'One zone pilot.<br>Portfolio pathway.')
    put(soup.select_one('#executive .recommendation>p'),'Start with one suitable SDP mall; KL East is a proposed candidate. Member booking and verified zone admissions create a repeatable service to test.')
    put(soup.select_one('#executive .recommendation-logic article:last-child h3'), 'Booking income, repeat visits and tenant value')
    put(soup.select_one('#executive .recommendation-logic article:last-child p'),
        f'Booking-only five-year recovery needs {f.required_bookings(5)/365:.1f} paid bookings/day at the reference fee mix. The pilot also measures repeat visits and net mall value.')
    put(soup.select_one('#executive .source'), shared+f'One-zone planning reference, not a cost or demand average across SDP malls. KL East remains a pilot candidate. {BOUNDARY}')
    put(soup.select_one('#context .site-brief .detail-list div:last-child dd'), 'Two new zone LPR cameras, a defined boundary, zone counts and vendor interfaces.')
    put(soup.select_one('#context .site-brief .note'), 'Existing mall LPR does not replace the two new zone cameras. Baseline demand, zone works and willingness to pay still need site measurement.')
    put(soup.select_one('#integration .source'), f'Sources: {source("site")}; {RESEARCH}. New-zone scope includes two additional LPR cameras. Confirm controller, power/network, gate safety, local coverage and incumbent interfaces.')
    put(soup.select_one('#integration .capability-diagnosis article:first-of-type p'), 'Can the two NEW zone LPR cameras produce reconciled entry/exit events?')
    put(soup.select_one('#integration .capability-assets figcaption'), 'Existing mall; additional zone equipment required.')
    put(soup.select_one('#integration .capability-assets h3'), 'Connect the new zone to the mall')
    put(soup.select_one('#integration .capability-assets .detail-list div:first-child dd'), 'Two new zone cameras; verify plate support, interfaces and controller handoff.')

    benchmark = spending_benchmark()
    member = base.cols(
        base.module('Why repeat visits matter', plot(benchmark)+'<p class="note">Source: '+source('spend')+'. National survey, N=500; recalled last-trip spend. Association does not establish parking-caused uplift.</p>'),
        base.module('SDP members and repeat visits',
            '<div class="g2-business-fact"><strong>100%</strong><span>KL East + Elmina committed occupancy · end-2025</span></div>'
            '<p class="note">Source: '+source('landlord')+', printed p. 28. Leasing context; not parking utilisation.</p>'
            '<div class="v2-proof-ladder"><article><b>Spend-linked parking credits</b><p>Test tenant-backed benefits tied to purchases. Source: '+source('spend_parking')+'.</p></article>'
            '<article><b>Repeat-visit milestones</b><p>Test a clearly explained reward path. Source: '+source('progress')+'.</p></article>'
            '<article><b>Targeted return offers</b><p>Test relevant offers for eligible members. Source: '+source('targeting')+'.</p></article></div>'), 'wide-left')
    body(soup, 'member-value', member,
         'Sources: '+source('spend')+'; '+source('landlord')+'; proposed mechanisms linked beside each. +68% = 327 / 195 − 1, rounded. National spending association does not establish ParkFlow uplift. No retention cash is assumed in reference returns.')

    put(soup.select_one('#must-be-true .g2-value-paths article:last-child h3'), 'Repeat visits and retention')
    put(soup.select_one('#must-be-true .g2-value-paths article:last-child p'), 'Measure return rate and extra visits<br>against an eligible control cohort')
    put(soup.select_one('#must-be-true .g2-bottom-note'),
        'Tenant sales and customer retention strengthen the business case. Only attributable net mall cash enters project returns; avoid adding the same visit, fee or rent benefit twice.')
    put(soup.select_one('#must-be-true .source'), shared+'Booking income, measured visit value and realized cost savings are separate cash channels. Benchmark scores, gross tenant sales and customer time savings are not added as profit.')

    cost = f'''<div class="g2-cost-map"><figure><img src="assets/priority-zone-pilot-concept.png" alt="Illustrative new Priority Zone; two additional entry and exit LPR cameras are budgeted"><figcaption>Zone hardware + works · <b>RM{f.HARDWARE/1000:.1f}k</b><span>2 NEW LPR × RM3,226 + LED RM2,033 + RM11,500 works/coverage allowances.</span><span>Source: {source('lpr')}; {source('led')}. Listed equipment excludes tax; both show zero stock.</span></figcaption></figure><div class="g2-cost-services"><article><span>Production integration allowance</span><h3>RM60k</h3><p>Identity, bookings, payments, zone control and commissioning. Project quotation still required.</p></article><article><span>Year 1 zone running allowance</span><h3>RM10.5k</h3><p>Hosting, messaging and upkeep. Central support and new equipment servicing need confirmation.</p></article></div></div><div class="g2-cost-envelope"><div><span>Priced-line subtotal · not all-in</span><strong>{money(f.FIRST_YEAR)} +</strong></div><p><b>Obtain prices for:</b> gates/arms, safety loops, intercom, edge controller/licenses, support, project taxes and contingency. Power/network scope sits inside an unquoted RM7,500 works allowance.</p></div>'''
    body(soup, 'investment', cost, shared+'Reference deployment for one new mall zone, with two new LPR cameras. Listed equipment is not an installed quote. Site scope and costs vary across malls; remaining equipment, support and tax need pricing.')
    put(soup.select_one('#investment .slide-title'),'Reference cost per new member zone')

    water = base.waterfall([r['gross'], -r['operator'], -r['processing'], -f.ANNUAL_RUNNING, r['contribution']],
                           ['Gross booking|fees', 'Operator|20% scenario', 'Card fees|1.944% incl. SST', 'Zone running|allowance', 'Operating|contribution'], 26000)
    booking = base.cols(base.module('Annual booking-fee bridge', base.chart(water, 'Reference volume: 104 peak / 261 weekday days; fixed 365-day illustration.')),
                        base.module('Published rate; explicit commercial inputs', detail_list([
                            ('Price-test inputs', 'RM4 weekday / RM5 peak; above ordinary parking'),
                            ('Reference volume', '30 peak / 7.5 weekday bookings per day; unvalidated'),
                            ('Payment reference', 'Billplz Basic MYR cards: 1.8% × 1.08'),
                            ('Operator / running', '20% proposed share; RM10,500 annual allowance')])+
                            f'<p class="note">Source: {source("payments")}; {source("fee_tax")}. All-card route is a comparison, not an agreed payment mix. RM{r["net"]/r["bookings"]:.2f} per booking remains before fixed running cost.</p>'), 'wide-left')
    body(soup, 'booking-return', booking, shared+f'Gross {money(r["gross"],2)} − operator {money(r["operator"],2)} − processing {money(r["processing"],2)} − running RM10,500 = {money(r["contribution"],2)}. {BOUNDARY}')
    put(soup.select_one('#booking-return .slide-title'),'Booking economics per reference zone')

    body(soup, 'booking-sensitivity', plot(curve(), cls='g2-breakeven')+
         f'<div class="g2-result-notes"><p><b>Derived operating threshold:</b> {f.required_bookings()/365:.1f} paid bookings/day covers the RM10,500 running allowance at this fee mix.</p><p><b>Derived recovery thresholds:</b> {f.required_bookings(5)/365:.1f}/day for five years; {f.required_bookings(3)/365:.1f}/day for three years. Add omitted costs before setting a target.</p></div>',
         shared+f'Capital {money(f.UPFRONT)} includes two new LPR cameras. Same proposed fees, 20% operator share and MYR-card route throughout. Thresholds are annual averages at a fixed mix, not every-day requirements or demand forecasts. {BOUNDARY}')
    cases=[]
    for name, peak, weekday in f.SCENARIOS:
        case=f.economics(peak, weekday)
        cases.append([name, f'{peak:g} / {weekday:g}', money(case['contribution']),
                      f'{case["payback"]:.1f} years', f'{case["cash_yield"]:.1%}'])
    body(soup, 'recovery', base.table(['Volume scenario','Peak / weekday bookings','Annual contribution','Simple payback','Annual cash yield*'], cases, [21,24,21,17,17])+
         base.strip(f'<b>Growth scenario:</b> 50 peak / 12.5 weekday bookings produce {money(f.economics(50,12.5)["contribution"])}/year; this is a commercial target, not an observed forecast. *Contribution / upfront capital; cash yield is not IRR or net ROI.'),
         shared+f'{BOUNDARY} Simple payback = {money(f.UPFRONT)} / annual contribution. No tenant-spend uplift, retention benefit or ML preference score is included.')

    body(soup, 'retention',plot(turnover_rent_sensitivity(),cls='g2-rent-sensitivity')+
         '<div class="g2-result-notes"><p><b>Published comparable:</b> Tropicana Gardens disclosed around 5% for specified trades and 5–15% for other categories. Source: '+source('lease_benchmark')+'.</p><p><b>Conditional gross receipts:</b> plotted sales must already earn rent above tenant/month lease floors. Below a floor, extra rent can be RM0. Deduct campaign and operating costs before claiming net value.</p></div>',
         'Sources: '+source('lease_benchmark')+' (3 Dec 2024 circular, printed p. 23); '+source('lease_structure')+'; '+MODEL+'. Sales levels and intermediate rates are sensitivity inputs, not observed uptake. No SDP average, net capture rate or retention cash forecast is asserted; excluded costs raise the recovery gap.')
    put(soup.select_one('#retention .slide-title'),'Tenant-sales and turnover-rent sensitivity')

    costs = [
        ['2 NEW zone LPR cameras', money(f.LPR), '2 × RM3,226 · Viskou DS-TCG406-E; tax extra; zero listed stock.', 'Malaysia plate support, lens, SDK and gate relay; installed quote.'],
        ['1 compact LED', money(f.LED), 'Viskou DS-TVL224, 2 rows; tax extra; zero listed stock.', 'Viewing distance, interfaces, mounting and availability.'],
        ['Coverage cameras', money(f.CAMERA_ALLOWANCE), 'Retained allowance, not a counted equipment quote.', 'Indoor occlusion survey, camera count and recorder/storage.'],
        ['Zone power / network / works', money(f.CABLING_ALLOWANCE), 'Retained allowance for PoE, cabling, electrical and installation.', 'Itemise distances, switch, UPS, mounts and commissioning.'],
        ['Software integration', money(f.INTEGRATION_ALLOWANCE), 'Unquoted production-delivery allowance.', 'Bookings, identity, controller, incumbent settlement and acceptance.'],
        ['Gates / safety / controller', 'Quote needed', 'Arms, loops/radar, intercom, edge PC/licenses not priced.', 'Determine quantities and supplier scope; do not treat as free.'],
        ['Annual zone running', money(f.ANNUAL_RUNNING), 'Unquoted hosting, messaging and upkeep allowance.', 'Confirm support, replacement cover, refunds and incident staffing.'],
    ]
    body(soup, 'a-cost', base.table(['New-zone cost line','Reference RM','Basis / status','Before commitment'], costs, [23,14,32,31])+
         base.strip(f'<b>Priced lines:</b> {money(f.HARDWARE)} hardware/works + RM60,000 integration = {money(f.UPFRONT)} upfront; + RM10,500 Year 1 running = {money(f.FIRST_YEAR)}. Add unpriced equipment, support, taxes and contingency.'),
         'Sources: '+source('lpr')+'; '+source('led')+'; '+RESEARCH+'. No camera-reuse saving is assumed. A generic RM1,000 counter-display listing is recorded as a quote lead, not an equivalent approved substitute.')
    reconciliation = [
        ['Paid bookings: 104 × 30 + 261 × 7.5', f'{r["bookings"]:,.1f} / year'],
        ['Gross: peak × RM5 + weekday × RM4', money(r['gross'],2)],
        ['Operator allocation: 20% commercial scenario', '−'+money(r['operator'],2)],
        ['MYR-card fees: 1.8% + 8% SST on that fee', '−'+money(r['processing'],2)],
        ['Annual running allowance', '−'+money(f.ANNUAL_RUNNING,2)],
        ['Annual contribution before excluded costs', money(r['contribution'],2)],
        ['Five-year capital reference: upfront / 5', money(f.UPFRONT/5,2)],
        ['Additional annual net benefit required', money(gap5,2)],
    ]
    finance_notes = '<ul><li>Two additional zone LPR cameras are purchased; mall entrance LPR is not substituted.</li><li>RM90,485 includes Year 1 running; RM79,985 is the recovery capital. Both exclude unpriced scope.</li><li>Costs and operator share need agreements; RM4/RM5 and volume are scenarios.</li><li>Support, refunds, displaced parking and incentives reduce net benefit. Tax treatment of the booking service needs confirmation.</li><li>No NPV/IRR or guaranteed retention uplift is claimed.</li></ul>'
    body(soup, 'a-finance', base.cols(base.module('Reference annual cash reconciliation', base.table(['Calculation','Result'], reconciliation, [73,27])), base.module('Cost and return boundaries', finance_notes)),
         shared+'Only processing-fee SST is included. Annual calculations aggregate rate × value; gateway rounding, refunds, chargebacks and output taxes must be reconciled in the settlement quote.')

    # The old basket/capture/visits appendix remains removed. The restored main
    # chart uses a sourced gross lease range and eligible sales, not net capture.
    soup.find(id='a-retention').decompose()

    # Make the pilot assess the wider business case, without importing causal uplift.
    measures = [
        ['Paid service','Offer conversion, realized fee and refunds','Randomised price offers; settled net receipts','Member team / Finance'],
        ['Member retention','30/60/90-day return rate; extra visits/member','Eligible control cohort; baseline-adjusted visits','CRM / analytics'],
        ['Tenant and mall value','Attributed tenant sales; marginal rent/parking cash','Lease-by-lease capture; displaced visits and fees deducted','Leasing / Finance'],
        ['Operating efficiency','Incidents, staff minutes, queue and bay use','Observed baseline; actual staff/cost reduction','Parking operator'],
        ['Incremental ML value','Same-controller ML vs strongest simple forecast','Measured operating difference; do not price the preference score','Product / data team'],
        ['Investment decision','Complete installed cost and net annual cash','Quoted scope; no double-counting across value channels','Sponsor / procurement'],
    ]
    body(soup, 'scorecard', base.table(['Value channel','Measure','Attribution / cash boundary','Owner'], measures, [20,29,34,17])+
         base.strip('<b>Total net benefit:</b> booking contribution + attributable marginal mall cash + realized operating savings − extra support, incentives and displaced income. Track tenant-sales and member-experience benefits alongside this cash calculation.'),
         'Proposed measurement plan, not completed field evidence. External programme and spending benchmarks establish relevance, not ParkFlow retention uplift. Measure uncertainty and avoid counting repeat bookers as saved customers.')
    put(soup.select_one('#decision .source'), shared+'Next decision: approve scope discovery and commercial measurement; obtain the complete installed quote before investment approval. Retention, tenant trading and operating savings are additional testable value channels.')
    put(soup.select_one('#decision .decision-deliverables .detail-list div:nth-child(2) dd'), 'Price conversion, 30/60/90-day return rates and extra mall visits against a control.')
    put(soup.select_one('#decision .decision-deliverables .detail-list div:nth-child(3) dd'), 'Two new LPR cameras, complete zone works, support and lease-linked net visit value; no double-counting.')
    # Update benchmark-method finance boundary and public-source appendix in place.
    for row in soup.select('#a-method tbody tr'):
        cells=row.select('td')
        if cells and 'Commercial' in cells[0].get_text():
            put(cells[1], 'Published equipment/payment benchmarks; one reconciled V2 scenario and derived recovery thresholds.')
            put(cells[2], 'No installed quote, local paid demand, controlled retention effect or agreed net capture rate.')
    body(soup, 'a-sources', base.cols(
        base.module('Commercial sources · checked 9 Nov 2026',
            ''.join(f'<article class="g2-source-entry"><b>{source(k)}</b><p>{desc}</p></article>' for k,desc in [
                ('site','Current tariffs, valet comparator and mall LPR. New zone needs two additional cameras.'),
                ('lpr','RM3,226 each; equipment-only, tax extra, zero listed stock.'),
                ('led','RM2,033 display; equipment-only, tax extra, zero listed stock.'),
                ('payments','Basic: MYR cards 1.8%, wallets 1.5%, B2C FPX RM1.25; approval required.'),
                ('fee_tax','8% SST on gateway fees; Basic has no annual plan charge.') ])),
        base.module('Business value and methods',
            ''.join(f'<article class="g2-source-entry"><b>{source(k)}</b><p>{desc}</p></article>' for k,desc in [
                ('landlord','FY2025: KL East and Elmina achieved 100% committed occupancy; recurring-income context.'),
                ('spend','National survey N=500: RM195 / RM327 frequency-group means; ~RM260 mean. Not causal.'),
                ('lease_benchmark','Tropicana Gardens, 2024 valuation: around 5% for specified trades; 5–15% for other categories; above lease floor.'),
                ('lease_structure','Paradigm PJ/JB: higher-of and percentage-only lease structures. Terms apply by tenant and period.') ])+
            '<p class="note">Technical sources: <a href="https://archive.ics.uci.edu/dataset/482/parking%2Bbirmingham">UCI Parking Birmingham</a>; <a href="../analysis/benchmarks/v2/report.md">occupancy / batch report</a>; <a href="../analysis/benchmarks/decision_value/report.md">event-driven report</a>. Other category/privacy references remain on their slides.</p>')),
         shared+'Public list prices and category precedents do not validate installed cost, local retention or willingness to pay. Payment selection must match the actual mix, merchant approval and settlement/refund terms.')

    # Semantic attributes allow cross-slide cash values to be reconciled in review.
    for id in ['executive','investment','booking-return','booking-sensitivity','retention','decision','a-cost','a-finance','recovery']:
        soup.find(id=id)['data-financial-model']='v2-2026-11-09'

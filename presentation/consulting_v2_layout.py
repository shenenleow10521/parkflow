"""Topic-led V2 slides and evidence-linked graphical exhibits.

Final pass after the older content/benchmark builders. Only V2 is written.
"""
import copy
import io
import json
import math
from pathlib import Path
import re

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

import build_consulting_deck as base
import v2_graphics as graphics

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site-consulting'
BENCH=ROOT/'analysis/benchmarks/decision_value'
REPORT='<a href="../analysis/benchmarks/decision_value/report.md">Event-driven benchmark · 8 Nov 2026</a>'
MODEL='<a href="../presentation/booking_economics.py">Shared financial model</a>'
TOPICS={
 'team':'Team Hexa','executive':'KL East Mall pilot proposal','context':'KL East Mall parking',
 'alternatives':'Member parking programmes','service':'ParkFlow priority zone','member':'Member booking journey',
 'operator':'Operator dashboard','admission':'Forecasting and admission control','integration':'Site and system integration','ml-stack':'ML forecasting architecture',
 'simulation':'Parking policy comparison','forecast':'Occupancy forecasting','member-value':'Member visits and spending',
 'must-be-true':'ParkFlow commercial model','investment':'Pilot cost and scope','booking-return':'Annual booking economics',
 'sanity-checks':'Operating and recovery thresholds','booking-sensitivity':'Booking demand and capital recovery',
 'recovery':'Demand scenarios and recovery periods','retention':'Additional visits and mall value',
 'commercial':'Operating roles and ownership','pilot-design':'Eight-week pilot schedule',
 'scorecard':'Pilot measures and responsibilities','risk':'Exceptions and fault handling','horizons':'Three-horizon roadmap',
 'decision':'Pilot scope and next steps','a-cost':'Cost details and exclusions','a-finance':'Financial model reconciliation',
 'a-partners':'External partner scenarios','a-retention':'Visit sensitivity: three and five years',
 'a-historical-policy':'Earlier policy simulation','a-optimizer-study':'Capacity and forecast ablation',
 'a-forecast-results':'Forecast errors and interval coverage','a-stress-results':'Stress tests and count errors',
 'a-method':'Benchmark methods and scope','a-evidence':'Local evidence and remaining questions',
 'a-sources':'Public sources','a-audit':'Analysis and design records','a-decision-study':'Event-driven policy results'}


def put(node,html):
    node.clear()
    for child in list(BeautifulSoup(html,'html.parser').contents):node.append(child)


def body(soup,id,html,note=None):
    slide=soup.find(id=id);put(slide.select_one('.content'),html)
    if note is not None:put(slide.select_one('.source'),note)
    return slide


def plot(svg,caption='',cls=''):
    return f'<figure class="g2-plot {cls}">{svg}'+(f'<figcaption>{caption}</figcaption>' if caption else '')+'</figure>'


def export_svg(fig,stem):
    stream=io.StringIO()
    with plt.rc_context({'svg.hashsalt':stem}):fig.savefig(stream,format='svg',transparent=True,metadata={'Date':None},bbox_inches='tight',pad_inches=.2)
    plt.close(fig);value=stream.getvalue();value=value[value.index('<svg'):]
    for id in re.findall(r'\bid="([^"]+)"',value):
        value=value.replace('id="'+id+'"','id="'+stem+'-'+id+'"').replace('url(#'+id+')','url(#'+stem+'-'+id+')').replace('href="#'+id+'"','href="#'+stem+'-'+id+'"')
    dest=SITE/'assets/v2-charts';dest.mkdir(exist_ok=True)
    (dest/(stem+'.svg')).write_text(value,encoding='utf-8')
    return value


def booking_curve():
    current=base.economics();annual=104*30+261*7.5
    per_booking=current['net']/annual
    x=np.linspace(0,8500,200);y=x*per_booking-base.ANNUAL_RUNNING
    fig,ax=plt.subplots(figsize=(14,4.65))
    ax.axhline(0,color='#a8b7ca',lw=1)
    hurdle=base.UPFRONT/5
    ax.axhline(hurdle,color='#53647a',lw=1.2,ls=(0,(5,5)))
    ax.text(8400,hurdle+550,'RM16,300 / year · five-year capital reference',ha='right',color='#53647a',fontsize=13)
    ax.plot(x,y,color='#245bd8',lw=2.8)
    scenarios=[('Conservative',20,5),('Base',30,7.5),('Higher demand',40,10)]
    for label,peak,weekday in scenarios:
        bookings=104*peak+261*weekday;r=base.economics(peak,weekday)
        ax.scatter([bookings],[r['contribution']],s=80,color='#245bd8',edgecolor='white',zorder=4)
        ax.annotate(f'{label} · {base.money(r["contribution"])}',(bookings,r['contribution']),xytext=(-13,28),textcoords='offset points',fontsize=14,color='#102a43',ha='center')
        ax.annotate(f'{bookings:,.0f} bookings',(bookings,r['contribution']),xytext=(8,-27),textcoords='offset points',fontsize=12,color='#53647a')
    opex=base.ANNUAL_RUNNING/per_booking
    ax.scatter([opex],[0],s=45,color='#8795a7',zorder=4)
    ax.annotate(f'Zone OPEX covered\n{math.ceil(opex):,} bookings / year',(opex,0),xytext=(-150,-48),textcoords='offset points',fontsize=12,color='#53647a',arrowprops={'arrowstyle':'-','color':'#a8b7ca'})
    ax.set_xlim(0,8600);ax.set_ylim(-12000,22000)
    ax.set_xticks([0,2000,4000,6000,8000]);ax.set_yticks([-10000,0,10000,20000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v:,.0f}'))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:('−' if v<0 else '')+f'RM{abs(v)/1000:g}k'))
    ax.set_xlabel('Paid bookings per year · fixed weekday/peak fee mix',labelpad=15)
    ax.set_ylabel('Annual zone contribution',labelpad=14)
    ax.grid(axis='y',color='#d5dde7',lw=.65)
    fig.subplots_adjust(left=.09,right=.98,bottom=.2,top=.94)
    return export_svg(fig,'booking-breakeven')


def admission_timeline():
    return '''<svg class="g2-native" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 360" role="img" aria-label="Illustrative admission timeline: current verified state, accepted commitments, a three-hour forecast and the next executable action">
<g font-family="Public Sans,Arial,sans-serif" fill="#102a43">
<text x="0" y="28" font-size="18" fill="#53647a">Illustrative timeline · the forecast informs the plan; observed capacity controls admission</text>
<path d="M250 75 H1400" stroke="#a8b7ca" fill="none"/><path d="M250 58 V330" stroke="#102a43" stroke-width="2"/>
<text x="250" y="58" text-anchor="middle" font-size="20" font-weight="600">Now</text>
<text x="630" y="58" text-anchor="middle" font-size="18">+60 min</text><text x="1010" y="58" text-anchor="middle" font-size="18">+120 min</text><text x="1400" y="58" text-anchor="end" font-size="18">+180 min</text>
<path d="M630 75 V330 M1010 75 V330 M1400 75 V330" stroke="#d5dde7" stroke-dasharray="3 6"/>
<text x="0" y="137" font-size="21" font-weight="550">Observed state</text><rect x="250" y="107" width="205" height="47" fill="#102a43"/><text x="270" y="137" font-size="18" fill="#fff">Counts + live ledger</text>
<text x="0" y="211" font-size="21" font-weight="550">Accepted bookings</text><rect x="390" y="179" width="350" height="47" fill="#dce7f8"/><text x="410" y="209" font-size="18">Commitments stay protected</text><rect x="820" y="179" width="285" height="47" fill="#dce7f8"/><text x="840" y="209" font-size="18">Later arrival window</text>
<text x="0" y="284" font-size="21" font-weight="550">Planning horizon</text><rect x="250" y="252" width="1150" height="47" fill="#edf3fc" stroke="#a8b7ca" stroke-dasharray="7 5"/><rect x="250" y="252" width="96" height="47" fill="#245bd8"/><text x="365" y="282" font-size="18">Next action first; update the remaining plan as events arrive</text>
<text x="250" y="340" font-size="16" fill="#53647a">15-minute updates in the event-driven study · three-hour look-ahead</text>
</g></svg>'''


def commercial_flow():
    return '''<div class="g2-value-map"><div class="g2-service-node"><span>Member service</span><h3>Reserved access<br>in a shared zone</h3><p>Members book an arrival window and use any eligible bay in the zone.</p></div><div class="g2-value-paths"><article><span class="g2-arrow">→</span><div><h3>Paid bookings</h3><p>RM4 weekday / RM5 peak<br>Proposed price points</p></div><span class="g2-arrow">→</span><div><h3>Booking contribution</h3><p>Fees less operator share,<br>processing and zone OPEX</p></div></article><article><span class="g2-arrow">→</span><div><h3>Potential extra visits</h3><p>Visits attributable to the service,<br>measured against a control</p></div><span class="g2-arrow">→</span><div><h3>Incremental mall value</h3><p>Extra visits × finance-approved<br>marginal net value per visit</p></div></article></div></div><div class="g2-value-equation"><span>Booking contribution</span><b>+</b><span>Attributable visit value</span><b>−</b><span>Additional central cost</span><b>=</b><strong>Annual project benefit</strong></div><p class="g2-bottom-note">The first path is modelled. The visit path still needs local measurement and an agreed net value per visit.</p>'''


def forecast_architecture():
    # The original site-vnext/ml-stack supplies the two-model occupancy concept.
    # Horizons and feature labels here follow the executed V2 benchmark code.
    return '''<svg class="g2-native" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1472 545" role="img" aria-labelledby="ml-architecture-title ml-architecture-desc">
<title id="ml-architecture-title">ParkFlow ML forecasting architecture</title>
<desc id="ml-architecture-desc">Occupancy history and time features feed adjusted weekly patterns and LightGBM in parallel. A weighted blend and a residual-calibrated 80 percent interval produce 30, 60, 120 and 180 minute occupancy forecasts. A separate LightGBM model predicts incoming booking requests from past requests, walk-ins and time. These are separate offline tasks; live site integration and the learning loop remain proposed.</desc>
<defs><marker id="ml-architecture-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#53647a"/></marker></defs>
<g font-family="Public Sans,Arial,sans-serif" fill="#102a43">
<text x="0" y="24" font-size="18" fill="#53647a">Occupancy forecasting · real public-data benchmark</text>
<rect x="0" y="83" width="260" height="220" fill="#edf3fc"/>
<text x="20" y="120" font-size="23" font-weight="550">Occupancy signals</text>
<text x="20" y="164" font-size="19" fill="#53647a">Current + recent levels</text>
<text x="20" y="198" font-size="19" fill="#53647a">Time, weekday, car park</text>
<text x="20" y="232" font-size="19" fill="#53647a">Same time last week</text>
<text x="20" y="279" font-size="16" fill="#53647a">Only data available at the time</text>
<rect x="350" y="65" width="240" height="110" fill="#f2f5f9"/>
<text x="370" y="105" font-size="23" font-weight="550">Weekly pattern</text>
<text x="370" y="143" font-size="19" fill="#53647a">Adjusted to today's level</text>
<rect x="350" y="222" width="240" height="110" fill="#edf3fc"/>
<text x="370" y="262" font-size="23" font-weight="550">LightGBM</text>
<text x="370" y="300" font-size="19" fill="#53647a">Learned patterns</text>
<rect x="645" y="123" width="245" height="177" fill="#dce7f8"/>
<text x="665" y="166" font-size="23" font-weight="550">Weighted blend</text>
<text x="665" y="204" font-size="19">+ 80% calibrated range</text>
<text x="665" y="247" font-size="16" fill="#53647a">Weights and interval errors</text>
<text x="665" y="272" font-size="16" fill="#53647a">fitted on earlier weeks</text>
<rect x="940" y="123" width="292" height="177" fill="#102a43"/>
<text x="960" y="167" font-size="21" fill="#fff" font-weight="550">30 / 60 / 120 / 180 min</text>
<text x="960" y="213" font-size="20" fill="#fff">Expected occupancy</text>
<text x="960" y="248" font-size="19" fill="#d2deee">+ empirical 80% range</text>
<rect x="1282" y="123" width="190" height="177" fill="#edf3fc"/>
<text x="1300" y="163" font-size="23" font-weight="550">Planning</text>
<text x="1300" y="205" font-size="18">Capacity protection</text>
<text x="1300" y="236" font-size="18">+ operator view</text>
<text x="1300" y="276" font-size="15" fill="#53647a">Gate checks actual bays</text>
<g fill="none" stroke="#53647a" stroke-width="1.7" marker-end="url(#ml-architecture-arrow)">
<path d="M260 194 H303 V120 H345"/><path d="M260 194 H303 V277 H345"/>
<path d="M590 120 H616 V211 H640"/><path d="M590 277 H616 V211 H640"/>
<path d="M890 211 H935"/><path d="M1232 211 H1277"/>
</g>
<text x="0" y="365" font-size="18" fill="#53647a">Booking-demand forecasting · separate synthetic event study</text>
<rect x="0" y="388" width="380" height="90" fill="#f2f5f9"/>
<text x="20" y="423" font-size="22" font-weight="550">Request + walk-in history</text>
<text x="20" y="456" font-size="18" fill="#53647a">Past 5 / 15 / 30 / 60 min + time features</text>
<rect x="435" y="388" width="300" height="90" fill="#edf3fc"/>
<text x="455" y="423" font-size="22" font-weight="550">LightGBM request model</text>
<text x="455" y="456" font-size="18" fill="#53647a">No future events supplied as inputs</text>
<rect x="790" y="388" width="442" height="90" fill="#dce7f8"/>
<text x="810" y="423" font-size="22" font-weight="550">Requests per 15-minute bucket</text>
<text x="810" y="456" font-size="18" fill="#53647a">Next 3 hours · common statistical stay model</text>
<g fill="none" stroke="#53647a" stroke-width="1.7" marker-end="url(#ml-architecture-arrow)"><path d="M380 433 H430"/><path d="M735 433 H785"/><path d="M1232 433 H1375 V306"/></g>
<text x="0" y="530" font-size="18" fill="#53647a">Proposed site loop: log actuals → check errors → retrain → validate before deployment</text>
</g></svg>'''


def gantt():
    tasks=[('Member baseline + price offers','Loyalty',1,2),('Controlled reservations','Operator + loyalty',3,6),('Member visit comparison','Loyalty',7,8),
           ('Zone count reconciliation','Operator + IT',1,2),('Assisted service + incident log','Operator',3,8),('Data access + integration','IT + integrator',1,2),
           ('Guard readiness check','Operator + IT',2,2),('Optimizer shadow replay','Team + operator',5,6),
           ('Installed scope + net capture','Finance',1,4),('Cost + investment review','Finance + sponsor',5,8)]
    left,step=340,113
    parts=['<svg class="g2-native" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1472 540" role="img" aria-label="Proposed eight-week pilot Gantt chart with ten tasks, owners and three decision milestones"><g font-family="Public Sans,Arial,sans-serif" fill="#102a43">',
           '<text x="0" y="22" font-size="17" fill="#53647a">Task / workstream</text><text x="1267" y="22" font-size="17" fill="#53647a">Owner</text>']
    for week in range(1,9):
        x=left+(week-.5)*step
        parts.append(f'<text x="{x}" y="22" font-size="17" text-anchor="middle">W{week}</text>')
        parts.append(f'<path d="M{left+(week-1)*step} 38 V455" stroke="#e7edf4"/>')
    for i,(name,owner,start,end) in enumerate(tasks):
        y=46+i*39;x=left+(start-1)*step+3;width=(end-start+1)*step-8
        parts.append(f'<text x="0" y="{y+22}" font-size="19">{name}</text><text x="1267" y="{y+22}" font-size="17" fill="#53647a">{owner}</text>')
        parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="30" fill="{"#245bd8" if i==7 else "#dce7f8"}"/>')
        if i in [2,4,7]:parts.append(f'<path d="M0 {y+36} H1465" stroke="#d5dde7"/>')
    for week,label in [(2,'Reservation readiness'),(6,'Live-AI decision'),(8,'Scale / extend / stop')]:
        x=left+week*step-5;y=472
        parts.append(f'<path d="M{x} {y-6} l6 6 -6 6 -6 -6z" fill="#102a43"/>')
        anchor='end' if week==8 else 'middle'
        parts.append(f'<text x="{x}" y="505" text-anchor="{anchor}" font-size="16">{label}</text>')
    parts.append('</g></svg>')
    return ''.join(parts)


def apply_graphical_revision(soup):
    # Graphs are rebuilt from recorded outputs; no model fitting or PDF export.
    result=json.loads((BENCH/'results.json').read_text())
    assert not result['quick_development_run']
    scatter=graphics.outcomes(result,deck=True);forecast=graphics.forecast_chart(deck=True)
    horizons=graphics.horizon_curves()
    put(soup.select_one('#cover h1'),'Member parking<br>at KL East Mall')
    put(soup.select_one('#cover .cover-context'),'ParkFlow · pilot proposal')
    put(soup.select_one('#cover .cover-deck'),'Reserved access for members.<br>Forecast-led planning for a shared parking zone.')
    put(soup.select_one('#executive .recommendation h3'),'One member zone<br>at KL East Mall')
    put(soup.select_one('#executive .recommendation>p'),'Bookable member access, forecast-led capacity planning and verified admissions within a shared zone.')
    logic=[('Member service','Reservations in the existing journey','Eligibility, a proposed RM4/RM5 booking fee, arrival guidance and one support path.'),
           ('Parking operation','Forecasts and a verified capacity guard','ML anticipates demand. The controller plans protection; observed free capacity governs every accepted promise.'),
           ('Mall economics','Booking fees and potential visit value','The base model leaves RM7.8k annually before central costs and capital recovery. Attributable visits could help close the remaining gap.')]
    put(soup.select_one('#executive .recommendation-logic'),''.join(f'<article><span>{a}</span><h3>{b}</h3><p>{c}</p></article>' for a,b,c in logic))
    put(soup.select_one('#service .service-rule'),'<h3>Shared bays<br>near the lifts</h3><p>ML forecasts booking demand and parking pressure. A rolling controller plans how much capacity to protect across the next three hours.</p><p class="note">Current free capacity and accepted commitments determine admission. The zone layout and live deployment remain proposed.</p>')
    put(soup.select_one('#member .member-story h3'),'Reserve, arrive<br>and get support')
    put(soup.select_one('#operator aside h3'),'Capacity, plans<br>and exceptions')
    for outer in list(soup.select('dl>dl,ul>ul')):outer.unwrap()

    body(soup,'admission',plot(admission_timeline(),cls='g2-timeline')+'<div class="g2-guard"><div><span>Capacity example · illustrative</span><p>100 bays − 82 occupied − 12 accepted claims − 2 safety bays</p></div><strong>= 4 available to promise</strong></div><p class="g2-bottom-note">A forecast departure can change the plan. It does not create an available bay for a new guarantee.</p>',
         'Source: <a href="../analysis/benchmark_decision_value.py">Offline event-driven controller</a>. Timeline and count example are illustrative; local integration, count accuracy and live operation remain unvalidated.')
    basecase=result['settings']['mixed_100'];pairs={v['comparator']:v for v in basecase['paired'] if v['metric']=='weighted_score'}
    body(soup,'simulation','<div class="g2-context-line">Interleaved synthetic requests · 100 bays · 60 held-out days · selected comparators</div>'+plot(scatter,cls='g2-scatter')+
         '<div class="g2-result-notes"><p><b>Member access and walk-ins trade off.</b> The calibrated fixed buffer serves more member arrivals; the learned-forecast controller admits more walk-ins.</p><p><b>ML versus adaptive forecasts:</b> '+f'{pairs["lp_adaptive"]["mean_delta"]:+.2f} preference-score units/day; 95% interval {pairs["lp_adaptive"]["ci95"][0]:+.2f} to {pairs["lp_adaptive"]["ci95"][1]:+.2f}.'+' No clear advantage in this comparison.</p></div>',
         'Source: '+REPORT+'. Score = 5 × members served + walk-ins; this is an operating preference, not money. Demand/cue relationships are synthetic assumptions. Full ten-policy results and earlier batch-study null are in the appendix.')
    body(soup,'forecast',plot(forecast,cls='g2-forecast')+'<div class="g2-result-notes"><p><b>Public occupancy:</b> 18,074 forecasts across 28 UK car parks; six weekly holdouts.</p><p><b>Local scope:</b> request and turnover tests use synthetic data. Birmingham occupancy does not validate KL East booking demand.</p></div>',
         'Source: <a href="../analysis/benchmarks/v2/occupancy.json">Causal occupancy benchmark</a>. MAE is percent of capacity. Strong adjusted baseline retained; 180-minute nominal 80% interval coverage is 79.8%.')
    put(soup.select_one('#member-value .cols>.col:last-child .module-title'),'Customer questions')
    put(soup.select_one('#member-value .v2-proof-ladder'),''.join(f'<article><b>{a}</b><p>{b}</p></article>' for a,b in [('Price acceptance','How many eligible members book at RM0, RM4, RM5 or RM8?'),('Additional visits','Does access change actual mall visits compared with a suitable control cohort?'),('Marginal mall value','What net value does Finance assign to an attributable extra visit?')]))
    body(soup,'must-be-true',commercial_flow(),'Sources: '+MODEL+'; proposed price experiments and pilot design. Arrows show the commercial mechanism, not measured conversion or causality. Extra visits and marginal mall capture remain unvalidated.')

    cost='''<div class="g2-cost-map"><figure><img src="assets/priority-zone-pilot-concept.png" alt="Illustrative Priority Zone concept; not an approved KL East layout"><figcaption>Hardware + installation · <b>RM21.5k</b><span>Illustrative zone; installed scope still needs a survey.</span></figcaption></figure><div class="g2-cost-services"><article><span>Production integration</span><h3>RM60k</h3><p>Member identity, bookings, payment settlement, controller connection and commissioning.</p></article><article><span>Year 1 zone running</span><h3>RM10.5k</h3><p>Hosting, messaging and upkeep allowance. Central support is additional.</p></article></div></div><div class="g2-cost-envelope"><div><span>Current planning subtotal</span><strong>RM92k</strong></div><p><b>Outside the priced scope:</b> final zone separation/barriers, incumbent interfaces, central support, tax and contingency.</p></div>'''
    body(soup,'investment',cost,'Sources: '+MODEL+' and linked supplier/product references in Cost details. All figures are planning allowances; final installed price, reuse and supplier scope are not confirmed.')
    body(soup,'booking-sensitivity',plot(booking_curve(),cls='g2-breakeven')+'<div class="g2-result-notes"><p><b>Model boundary:</b> same RM4/RM5 fee mix, shares and RM10.5k zone running allowance across the line.</p><p><b>Capital recovery:</b> all three volume cases remain below the five-year booking-only reference before central support, tax and omitted scope.</p></div>',
         'Source: '+MODEL+'. Five-year reference is RM81,500 / 5, not an SDP-approved hurdle. These are demand scenarios, not forecasts. Annual support and additional capital raise the required return.')
    # These calculations remain available after Thank You rather than repeating
    # the same recovery gap on three consecutive main slides.
    anchor=soup.find(id='a-finance')
    for id in ['sanity-checks','recovery']:
        slide=soup.find(id=id);slide['data-section']='Appendix';slide['data-appendix']='true'
        slide.extract();anchor.insert_after(slide);anchor=slide
    # Retention is an evidence-linked business mechanism in the final V2 pass.
    # Do not regenerate the former basket/capture visit sensitivity.
    body(soup,'pilot-design',plot(gantt(),cls='g2-gantt')+'<p class="g2-bottom-note">Site access and baseline instrumentation precede Week 1. Live AI activation follows shadow-mode acceptance; visit measurement may need a longer follow-up.</p>',
         'Proposed pilot sequence and owners. Bars show planned work, not completed delivery or agreed SLAs. Reservation readiness includes reconciled counts, entitlement checks and a signed recovery SOP.')
    body(soup,'horizons',plot(horizons,cls='g2-horizons'),
         'Source: <a href="https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/enduring-ideas-the-three-horizons-of-growth">Three-horizons framework</a>, adapted for ParkFlow. Curves indicate broader proposed scope; dates are indicative focus windows, not a linear time axis or revenue/adoption forecast.')

    put(soup.select_one('#decision .decision-ask h3'),'One site survey.<br>One controlled pilot.')
    put(soup.select_one('#decision .decision-deliverables>h3'),'Inputs to the rollout decision')
    put(soup.select_one('#decision .decision-deliverables .detail-list'),''.join(f'<div><dt>{a}</dt><dd>{b}</dd></div>' for a,b in [('Operating performance','Member access, walk-ins, idle capacity and exceptions under the strongest practical baselines.'),('Member behaviour','Price-dependent uptake and actual visits attributable to the service.'),('Complete economics','Installed quotations, support allocation and Finance-approved marginal capture.'),('Site readiness','Verified counts, controller access, ownership and a signed recovery SOP.')]))

    # A full numerical comparison stays attached to the main scatterplot.
    extra=copy.deepcopy(soup.find(id='a-method'));extra['id']='a-decision-study';soup.find(id='a-method').insert_before(extra)
    labels={'guard':'Guard only','fixed5':'Fixed +5','fixed10':'Fixed +10','calibrated_fixed':'Calibrated fixed','reactive':'Reactive adaptive','lp_mean':'LP + means','lp_adaptive':'LP + adaptive','lp_linear':'LP + linear','lp_ml':'LP + learned','request_oracle':'Request oracle'}
    rows=[[labels[k],f'{v["fulfilled"]:.2f}',f'{v["walkins"]:.2f}',f'{v["rejection_rate"]:.1%}',f'{v["weighted_score"]:.2f}'] for k,v in basecase['policies'].items()]
    body(soup,'a-decision-study','<div class="g2-context-line">Minute-resolution arrivals · 15–180-minute booking lead times · 60 paired main days</div>'+base.table(['Policy','Member arrivals / day','Walk-ins / day','Request rejection','Preference score'],rows,[30,19,19,16,16])+base.strip('<b>Interpretation:</b> learned forecasts improve the declared score versus linear forecasts, but do not clearly beat adaptive forecasts. The calibrated fixed buffer has a higher score and a different member/walk-in trade-off.'),
         'Source: '+REPORT+'. 3,000 policy-day runs across all settings; 160 training and 40 calibration days. Synthetic predictive cues are assumptions. Earlier 3,500-run batch-study results remain separate.',)
    methods=[('Public occupancy','18,074 forecasts; 28 UK car parks; 30/60/120/180 minutes.','Same-site historical time holdout, not KL East or booking requests.'),
             ('Camera perception','Earlier 99.05% on 78,270 held-out-camera patches.','One outdoor site; indoor transfer and false-free counts still need testing.'),
             ('Earlier batch controller','3,500 synthetic policy-day runs; seven policies.','At 100 bays, guard only matched LP. Detected and undetected faults differ.'),
             ('Event-driven controller','3,000 synthetic policy-day runs; ten policies; mixed booking lead times.','Forecasts change decisions; learned LP has no clear score advantage over adaptive LP.'),
             ('Commercial model','Fees, costs, capture and visit sensitivities are calculated scenarios.','No local willingness-to-pay, controlled visit uplift or approved capture rate.')]
    body(soup,'a-method',base.table(['Evidence layer','Completed work','Boundary'],methods,[23,39,38]),
         'Sources: '+REPORT+'; <a href="../analysis/benchmarks/v2/report.md">earlier batch and occupancy report</a>; <a href="../analysis/cv_benchmark_results.txt">camera benchmark</a>. No field safety, retention or commercial return is established.')
    for id in ['a-optimizer-study','a-stress-results']:
        content=soup.select_one('#'+id+' .content')
        label=BeautifulSoup('<div class="g2-context-line">Earlier 30-minute-batch study · 3,500 policy-day runs · synthetic demand</div>','html.parser').div
        content.insert(0,label)
    for row in soup.select('#a-evidence tbody tr'):
        cells=row.select('td')
        if cells[0].get_text(strip=True)=='Operating benefit':put(cells[1],'Earlier batch: guard matches LP. Event-driven study: member/walk-in outcomes trade off.')
        if cells[0].get_text(strip=True)=='ML benefit':put(cells[1],'Forecast errors improve; event-driven LP has no clear advantage over adaptive forecasts.')
    put(soup.select_one('#a-audit .decision-strip'),'<b>Current evidence:</b> '+REPORT+' · <a href="../analysis/benchmarks/v2/report.md">Earlier batch + occupancy report</a> · <a href="v2-notes.md">V2 notes</a>. HTML only; no PDF generated.')

    architecture=copy.deepcopy(soup.find(id='forecast'))
    architecture['id']='ml-stack';architecture['data-section']='Product';architecture['data-appendix']='false';architecture['class']=['slide']
    soup.find(id='integration').insert_after(architecture)
    body(soup,'ml-stack',plot(forecast_architecture(),cls='g2-architecture')+'<p class="g2-bottom-note">The occupancy ensemble and request model are separate offline tasks. Site connections, weather/events/cinema inputs and the operating learning loop remain proposed.</p>',
         'Sources: <a href="../site-vnext/index.html#ml-stack">Original forecasting architecture</a>; <a href="../analysis/benchmark_occupancy_v2.py">V2 occupancy code</a>; <a href="../analysis/benchmark_decision_value.py">request model + controller</a>. Native V2 diagram; original deck unchanged.')
    architecture.insert_after(soup.find(id='forecast').extract())
    measures=soup.find(id='scorecard');measures['data-section']='Appendix';measures['data-appendix']='true'
    soup.find(id='a-cost').insert_after(measures.extract())
    for id in ['commercial','sanity-checks','a-partners','a-historical-policy','a-evidence','a-audit']:
        soup.find(id=id).decompose()

    for slide in soup.select('section.slide'):
        id=slide['id']
        if id in TOPICS:put(slide.select_one('.slide-title'),TOPICS[id])
        takeaway=slide.select_one('.takeaway')
        if takeaway:takeaway.decompose()
        if slide['data-section']=='Appendix':
            classes=slide.get('class',[])
            if 'compact' not in classes:classes.append('compact')
            slide['class']=classes
    for controls in soup.select('.controls'):controls.decompose()
    soup.select_one('script[src="deck.js"]')['src']='v2.js'
    soup.title.string='ParkFlow | Member parking pilot · V2'
    soup.find('meta',attrs={'name':'description'})['content']='ParkFlow member parking: product, operating mechanism, offline benchmarks, commercial model, pilot Gantt and three-horizon roadmap.'

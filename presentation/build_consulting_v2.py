"""Revise the existing consulting HTML into an isolated V2, without PDFs.

The deployed three-hour optimizer remains proposed. Executed offline benchmark
results are loaded separately; earlier experiment scores are never relabelled.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path

from bs4 import BeautifulSoup
import build_consulting_deck as base
from consulting_art_direction import detail_list, wordmark
from consulting_v2_benchmarks import apply_completed_benchmarks
from consulting_v2_layout import apply_graphical_revision

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site-consulting'


def fragment(html):
    return BeautifulSoup(html,'html.parser')


def replace_html(node,html):
    node.clear()
    for child in list(fragment(html).contents):
        node.append(child)


def panel(title,body,cls=''):
    return f'<article class="v2-panel {cls}"><h3>{title}</h3>{body}</article>'


def build():
    soup=BeautifulSoup((SITE/'index.html').read_text(encoding='utf-8'),'html.parser')
    soup.title.string='ParkFlow | V2 · three-hour planning and validation'
    soup.find('meta',attrs={'name':'description'})['content']='ParkFlow V2: proposed three-hour rolling-horizon planning, verified gate control and an explicit technical and commercial validation programme.'
    soup.head.append(soup.new_tag('link',rel='stylesheet',href='v2.css'))
    soup.body['class']=['edition-v2']
    def change(id,title=None,takeaway=None,body=None,note=None,cls=None):
        slide=soup.find(id=id)
        if title is not None:replace_html(slide.select_one('.slide-title'),title)
        if takeaway is not None:replace_html(slide.select_one('.takeaway'),takeaway)
        if body is not None:replace_html(slide.select_one('.content'),body)
        if note is not None:replace_html(slide.select_one('.source'),note)
        if cls is not None:slide['class']=['slide',*cls.split()]
        return slide
    def add_slide(id,title,takeaway,body,note,section='Business',appendix=False):
        slide=copy.deepcopy(soup.find(id='scorecard'))
        slide['id']=id;slide['data-section']=section;slide['data-appendix']=str(appendix).lower();slide['class']=['slide'];slide['aria-label']=title
        replace_html(slide.select_one('.slide-title'),title)
        replace_html(slide.select_one('.takeaway'),takeaway)
        replace_html(slide.select_one('.content'),body)
        replace_html(slide.select_one('.source'),note)
        return slide
    source_model='<a href="../presentation/booking_economics.py">Shared booking-fee model</a>'
    source_history='<a href="../analysis/simulate_pooling_results.txt">Earlier policy simulation</a>'
    source_forecast='<a href="../analysis/backtest_ensemble_results.txt">Historical occupancy back-test</a>'
    source_cv='<a href="../analysis/cv_benchmark_results.txt">Held-out-camera benchmark</a>'
    source_vase='<a href="https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026" target="_blank" rel="noopener">Vase.ai mall survey, 2026 (n=500)</a>'

    replace_html(soup.select_one('#cover .cover-context'),'V2 · three-hour planning concept')
    replace_html(soup.select_one('#cover .cover-deck'),'Forecast demand. Optimize protection.<br>Verify every commitment at the gate.')
    replace_html(soup.select_one('#cover .cover-credit span'),'Universiti Malaya · revision 8 November 2026')
    change('executive',takeaway='Prove that the proposed optimizer improves access, that members value the service, and that the mall captures enough net benefit.')
    logic=[('Technical proof','More fulfilled member opportunities, safely.','Compare the actual three-hour rolling policy with fixed rules on identical event streams. Existing forecast accuracy does not prove optimization benefit.'),('Customer proof','Measure preference and attributable visits.','Test price-dependent conversion, local parking pain and subsequent visit behaviour. Separate a paid booking from a genuinely additional mall visit.'),('Commercial proof','Reconcile the complete value case.','Use finance-approved marginal capture, installed quotations and realistic support cost. RM92k and 13 extra weekly visits remain illustrative planning cases.')]
    replace_html(soup.select_one('#executive .recommendation-logic'),''.join(f'<article><span>{a}</span><h3>{b}</h3><p>{c}</p></article>' for a,b,c in logic))
    replace_html(soup.select_one('#executive .recommendation>p'),'Approve the baseline, conservative reservation trial and shadow-mode evaluation before activating the proposed optimizer.')

    change('service',title='A shared zone, planned over the next three hours',takeaway='Forecasts inform a rolling plan; the hard gate still protects accepted commitments.')
    replace_html(soup.select_one('#service .service-rule'),'<h3>Plan ahead.<br>Commit conservatively.</h3><p>The proposed optimizer balances member booking opportunities, walk-in access and unused protection across the next 180 minutes.</p><p class="note">It proposes quotas and protection levels. Existing promises and verified capacity remain binding.</p>')
    replace_html(soup.select_one('#service .journey-ribbon'),''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a,b in [('Forecast','Bookings, departures, occupancy'),('Optimize','A feasible three-hour plan'),('Verify','Current capacity + promises'),('Refresh','New events, revised forecasts')]))
    change('member',note='Existing app prototype, simulated data. Three-hour optimization is proposed. RM4 weekday / RM5 peak are pricing-test inputs, additional to ordinary parking charges.')
    change('operator',takeaway='Show the recommended plan, its uncertainty and the verified state; record the reason for every override.')
    replace_html(soup.select_one('#operator figure figcaption'),'Existing prototype view. Rolling-horizon recommendations and policy comparisons are proposed additions.')
    replace_html(soup.select_one('#operator .detail-list'),detail_list([('Plan','Review the next-three-hour recommendation and its uncertainty.'),('Verify','Check current counts, protected promises and the admission guard.'),('Audit','Log plan changes, overrides, rejected recommendations and recovery.')]))

    timeline='<div class="v2-horizon"><div class="v2-horizon-labels"><b>Now</b><span>+60 min</span><span>+120 min</span><b>+180 min</b></div><div class="v2-buckets">'+''.join(f'<div><b>{i*30}–{(i+1)*30}</b><span>minutes</span></div>' for i in range(6))+'</div><div class="v2-roll"><span>Observe real events</span><b>→</b><span>Update forecasts</span><b>→</b><span>Solve again; apply the next feasible action</span></div></div>'
    workflow='<div class="v2-workflow">'+''.join(panel(a,f'<p>{b}</p><small>{c}</small>') for a,b,c in [('Forecast','Predict member demand, departures and occupancy, with uncertainty.','Demand needs local booking requests; occupancy alone is insufficient.'),('Optimize','Choose protection and acceptance quotas inside a conservative feasible envelope.','Objective and trade-off weights must be fixed before evaluation.'),('Hard gate','Check observed free capacity, existing promises and the approved safety margin.','A predicted departure alone must never authorize a new promise.')])+'</div>'
    change('admission',title='Three-hour planning above a verified hard gate',takeaway='The proposed optimization layer changes the plan; it cannot relax physical capacity or release an existing promise.',body=timeline+workflow,note='Proposed mechanism, not deployed validation. Six 30-minute buckets illustrate the horizon; cadence, bucket width and uncertainty margin require calibration. Pause commitments on stale counts or outages.')

    # Keep older measured policy results, but explicitly relocate them to context.
    historical=copy.deepcopy(soup.find(id='simulation'))
    historical['id']='a-historical-policy';historical['data-section']='Appendix';historical['data-appendix']='true'
    replace_html(historical.select_one('.slide-title'),'Appendix / earlier policy simulation')
    replace_html(historical.select_one('.takeaway'),'Recorded legacy-policy results provide context; they are not results for the proposed three-hour optimizer.')
    replace_html(historical.select_one('.source'),'Source: '+source_history+'. Same synthetic days; 100-bay zone. No rolling-horizon performance or KL East field result is claimed.')
    soup.find(id='a-method').insert_before(historical)
    policies=[('Fixed 5-bay buffer','Simple baseline'),('Fixed 10-bay buffer','More conservative baseline'),('Reactive dynamic buffer','Near-term demand response'),('Three-hour rolling optimizer','Proposed approach to test'),('Perfect-information optimizer','Reference ceiling, same constraints')]
    experiment='<div class="v2-study-layout"><div class="v2-common-tape"><h3>One shared event stream</h3><p>Identical arrivals, stays, requests, no-shows, late arrivals and fault events.</p><div class="v2-policy-list">'+''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a,b in policies)+'</div></div><aside class="v2-outcomes"><h3>Compare outcomes that matter</h3>'+detail_list([('Member access','Requests, accepted bookings and accepted arrivals actually served.'),('Capacity use','Walk-ins admitted and idle protected bay-hours.'),('Safety','Capacity violations, promise failures and recovery behaviour.'),('Robustness','Forecast errors, demand spikes, count drift and outages.')])+'<div class="v2-status">Evaluation pending<br><span>No new optimizer uplift is reported.</span></div></aside></div>'
    change('simulation',title='Validate the actual policy on the same simulated days',takeaway='Forecast accuracy and an earlier forecast-based rule do not establish the benefit of a rolling optimizer.',body=experiment,note='Proposed comparison. Report both fixed baselines, their rejection rates and feasibility. Perfect information is a formal upper bound only with the same constraints and an optimal solution.')

    forecast_body=base.cols(base.module('Existing occupancy result',base.chart(base.forecast_chart(),'Historical 30/60/90-minute occupancy forecasts; this chart does not validate booking demand or 180-minute forecasts.')+'<div class="legend"><span><i class="grey"></i>Same time last week</span><span><i></i>Ensemble</span></div>'),base.module('Three predictions to validate','<div class="v2-validation-streams">'+''.join(f'<article><b>{a}</b><p>{b}</p><span>{c}</span></article>' for a,b,c in [('Booking demand','MAE/WAPE and interval coverage.','Timestamped local requests; synthetic demand only when labelled.'),('Turnover','Departure-count MAE by 15–30-minute interval.','Entry/exit timestamps and consistent event reconciliation.'),('Occupancy','MAE at 30 / 60 / 120 / 180 minutes.','Local time holdout, peak/event slices and interval calibration.')])+'</div>'),'wide-left')
    change('forecast',title='Validate demand, turnover and occupancy separately',takeaway='Historical 60-minute occupancy MAE is 2.07% versus 5.34%; the new demand and long-horizon claims remain untested.',body=forecast_body,note='Sources: '+source_forecast+'; '+source_cv+'. The CNRPark test held out cameras at the same outdoor site, not a new indoor mall. New 120/180-minute and member-demand results are pending.')

    membervalue=base.cols(base.module('Observed spending association',base.chart(base.spend_chart(),'Recalled survey spending by visit frequency. Association, not parking-caused uplift.')),base.module('The direct customer evidence needed','<div class="v2-proof-ladder">'+''.join(f'<article><b>{a}</b><p>{b}</p></article>' for a,b in [('Local pain','Interview eligible members about recent parking-related visit decisions.'),('Revealed preference','Randomize clear RM0 / RM4 / RM5 / RM8 offers and measure conversion among exposed members.'),('Attributable visits','Compare actual visits with a matched or randomized eligible control cohort over time.')])+'</div>'),'wide-left')+base.strip('<strong>Two outcomes:</strong> extra fulfilled bookings are operational opportunities; extra visits caused by the service create incremental commercial value.')
    change('member-value',title='Prove that convenience changes the visit decision',takeaway='Category precedent and a spending correlation support the hypothesis; local willingness to pay and retention still need evidence.',body=membervalue,note='Source: '+source_vase+'. Proposed prices are experiment arms, not validated demand. A stated-preference survey alone does not establish paid conversion or causal retention.')

    hypotheses=[('Members value reserved access','Published comparator programmes','Local interviews and eligible-member demand.'),('Members will pay RM4–RM5','Proposed price points','Randomized offer / conversion experiment.'),('Convenience adds visits','Indirect spending/frequency association','Controlled behaviour test and follow-up.'),('AI improves the operation','Earlier simulation, different policy','Actual optimizer replay + ML ablation.'),('The mall captures enough value','Illustrative financial bridge','Finance-approved marginal capture + full cost.')]
    truths='<div class="v2-truth-intro"><h3>Three proofs must connect</h3><div><span>Technical benefit</span><b>→</b><span>Customer behaviour</span><b>→</b><span>Net mall value</span></div></div><div class="v2-truths">'+''.join(f'<article><h3>{a}</h3><div><b>Evidence today</b><p>{b}</p></div><div><b>Validation needed</b><p>{c}</p></div></article>' for a,b,c in hypotheses)+'</div>'
    must_be_true=add_slide('must-be-true','What must be true for ParkFlow to succeed?','An explicit hypothesis register connects the innovation argument to the business decision.',truths,'Sources: official comparator programmes, '+source_vase+', '+source_history+' and '+source_model+'. All five hypotheses require local validation; no optimizer or retention uplift is claimed.')
    soup.find(id='investment').insert_before(must_be_true)

    # Three demand cases are calculated from the same existing fee/share/OPEX model.
    cases=[]
    for name,peak,weekday in [('Conservative',20,5),('Base',30,7.5),('Higher demand',40,10)]:
        model=base.economics(peak,weekday)
        visits=math.ceil(max(0,base.UPFRONT/5-model['contribution'])/(52*260*.05))
        cases.append((name,peak,weekday,model,visits))
    scenarios='<div class="v2-scenarios">'+''.join(f'<article><span>{name}</span><h3>{base.money(m["contribution"])}<small>annual contribution before central costs</small></h3><dl><div><dt>Peak bookings/day</dt><dd>{peak:g}</dd></div><div><dt>Weekday bookings/day</dt><dd>{weekday:g}</dd></div><div><dt>5-year annual value gap</dt><dd>{base.money(max(0,base.UPFRONT/5-m["contribution"]))}</dd></div><div><dt>Extra visits/week*</dt><dd>{visits}</dd></div></dl></article>' for name,peak,weekday,m,visits in cases)+'</div><div class="v2-cost-pressure"><h3>Full-cost correction</h3><p>Every additional RM12,000 of annual support reduces each contribution by RM12,000. Omitted installation cost, tax or a lower marginal capture rate increases the required visit uplift.</p></div>'
    change('booking-sensitivity',title='Stress paid demand and the full-cost boundary',takeaway='Three transparent volume cases replace a single forecast; the installed scope and annual support still need quotations.',body=scenarios,note='Source: '+source_model+'. Scenarios only; same RM4/RM5 fees, 20% operator + 2% processing shares, RM10,500 OPEX and RM81,500 capital. *RM260 basket × 5% capture are unverified illustrations.')
    change('recovery',title='Capital recovery needs verified incremental value')
    change('sanity-checks',takeaway='The 13-visit bridge is a scenario: both genuinely extra visits and RM13 of net value per visit still need proof.')
    change('retention',takeaway='Under the illustrated five-year model, the gap needs 7–29 extra weekly visits; bookings are not a substitute for causal visit measurement.')
    replace_html(soup.select_one('#retention .cols>.col:last-child ul'),base.bullets(['Validate the marginal net benefit of an extra visit with SDP Finance; tenant spend is not landlord profit.','RM260 × 5% = RM13 is a scenario, not an approved lease capture estimate.','Measure visits attributable to the service, excluding members who would have visited anyway.','Add central support, omitted installation and tax before setting the final investment hurdle.']))

    plan=[('Weeks 1–2','Baseline & price discovery','Record arrivals, occupancy, stays, member visits and parking pain. Test offer conversion across the proposed price arms.'),('Weeks 3–4','Conservative reservations','Launch a fixed-buffer policy after readiness checks. Record fulfilment, no-shows, exceptions and actual delivery effort.'),('Weeks 5–6','Shadow the optimizer','Replay the rolling policy against observed events first. Activate only after safety and operator acceptance criteria pass.'),('Weeks 7–8','Commercial evaluation','Compare member visits with a suitable control cohort, reconcile net capture and cost, and decide whether follow-up is needed.')]
    pilot='<div class="pilot-timeline">'+''.join(f'<article><span>{period}</span><h3>{title}</h3><p>{text}</p></article>' for period,title,text in plan)+'</div><div class="test-design"><div><h3>AI versus fixed rules</h3><p>Predefine comparisons, safety checks and the main operating outcome. Use paired event streams and shadow mode before approved live switching.</p></div><div><h3>Visits versus bookings</h3><p>Separate price-dependent uptake from incremental visits. Eight weeks can test feasibility; convincing retention uplift may require longer follow-up.</p></div></div>'
    change('pilot-design',title='Eight weeks to test the operation and the value case',takeaway='Safety, privacy, member terms and access readiness are prerequisites before this validation window begins.',body=pilot,note='Proposed sequence from the revision brief. A pilot is not a guarantee of statistical power; extend the window when visit or booking samples are insufficient.')
    criteria=[('Safety before activation','Capacity violations; stale-count and outage behaviour.','Zero violations in the specified replay/fault suite; signed recovery SOP.','Operator + IT'),('Optimization benefit','Additional accepted/fulfilled member bookings, walk-ins, idle bay-hours and rejection.','Report both fixed baselines; predeclare the minimum material uplift.','Analyst + operator'),('ML contribution','Optimizer with historical averages versus ML; same constraints and objective.','Show whether ML adds material value beyond optimization alone.','AI + analyst'),('Paid demand','Conversion by randomized offer, eligible exposure and repeat use.','Use observed demand to stress the contribution model, with uncertainty.','Loyalty + finance'),('Commercial return','Attributable visits × approved marginal capture, less full cost.','Clear SDP’s finance-approved hurdle; otherwise adapt, extend or stop.','Finance + sponsor')]
    change('scorecard',title='Agree the technical and commercial gates in advance',takeaway='Protect the hard constraints, then judge incremental operating and business benefit.',body='<div class="v2-scorecard">'+base.table(['Decision gate','Metric / denominator','Proposed decision principle','Owner'],criteria,[18,31,35,16])+'</div>',note='Proposed criteria, not agreed SLAs. Replay success does not establish universal safety; live monitoring and statistical uncertainty remain necessary.')
    change('decision',takeaway='Approve baseline access, an optimizer evaluation protocol and a finance-calibrated commercial test before scaling.')
    replace_html(soup.select_one('#decision .decision-deliverables .detail-list'),detail_list([('Validated mechanism','Exact rolling policy versus fixed rules, plus forecast ablation and failure tests.'),('Customer evidence','Local pain, price-dependent conversion and controlled visit outcomes.'),('Complete value','Approved marginal visit capture, installed scope and support cost.'),('Ready operation','Conservative launch, shadow-mode checks and a signed recovery SOP.')]))
    replace_html(soup.select_one('#horizons .horizon-stages article:first-child ul'),base.bullets(['Local baseline + price experiment','Fixed-rule trial + optimizer shadow test','Full-cost and attributable-visit review']))
    replace_html(soup.select_one('#horizons .horizon-stages article:first-child .value-gate'),'Value gate: technical, customer and commercial proof')

    ablation=[('A · Fixed rules','No optimizer, no ML','Simple operating reference.'),('B · Optimizer + averages','Same solver with historical inputs','Isolate optimization benefit.'),('C · Optimizer + ML','Same solver with learned inputs','Isolate incremental ML benefit versus B.'),('D · Perfect information','Same feasible set, ideal future data','Reference ceiling; do not treat as deployable.')]
    study=add_slide('a-optimizer-study','Appendix / optimizer study and capacity sensitivity','Freeze the policy and evaluation protocol before reporting an AI benefit.',base.cols(base.module('Ablation: keep the optimizer constant',base.table(['Run','Configuration','What it isolates'],ablation,[21,39,40])),base.module('Capacity and stress coverage','<div class="v2-size-strip"><b>50 bays</b><b>100 bays</b><b>150 bays</b></div>'+base.bullets(['Replay identical external demand across sizes to test site sizing; separately run demand-scaled cases to compare utilization pressure.','Stress high member demand, long stays, no-shows, late arrivals, count error and network loss.','Report paired day-level differences, uncertainty, solver latency and infeasible recommendations.','Freeze objective weights, seeds, horizon, cadence and quota semantics. Preserve every accepted promise.']))),'Proposed offline protocol, not a completed run. A perfect-forecast solution is a theoretical upper bound only if globally optimal under identical constraints.',section='Appendix',appendix=True)
    soup.find(id='a-method').insert_before(study)
    methods=[('Occupancy forecasting','48,112 historical forecasts; 30 car parks; six weeks.','30/60/90-minute occupancy benchmark only; demand and 120/180-minute tests remain open.'),('Camera perception','99.05% accuracy on 78,270 held-out-camera patches.','One outdoor Italian site; indoor transfer and false-free reconciliation require local testing.'),('Earlier policy simulation','Legacy forecast-policy comparison on 1,000 synthetic busy days.','Different admission logic; cannot be presented as three-hour optimizer performance.'),('Three-hour optimization','Proposed mechanism and comparison/ablation protocol.','No new optimizer results, deployment claim or demonstrated member-access uplift.')]
    change('a-method',title='Appendix / demonstrated results versus proposed capability',takeaway='Each result supports one bounded claim; proposed capabilities remain explicit.',body=base.table(['Evidence layer','What exists','Boundary / missing validation'],methods,[23,35,42]),note='Sources: '+source_forecast+'; '+source_cv+'; '+source_history+'. Results are internal experiments; no local optimizer, booking-demand or retention validation is claimed.',cls='compact')
    evidence=[('Local parking need','Competitor category precedent; no KL East demand baseline.','Member interviews, observed congestion and price conversion.'),('Booking demand forecast','Not validated by Birmingham occupancy data.','Timestamped local requests or labelled synthetic demand.'),('Rolling optimizer benefit','Protocol specified; actual-policy results pending.','Paired five-policy replay, 50/100/150 bays and failure tests.'),('ML adds value','Historical occupancy improvement only.','Compare the same optimizer with averages, ML and perfect information.'),('Retention and capture','Frequency/spend association and illustrative RM13 per extra visit.','Controlled visits and finance-approved marginal net capture.'),('Full installed economics','RM92k subtotal; important scope/support items unpriced.','Signed installed quotations, zone layout, support, tax and contingency.')]
    change('a-evidence',title='Appendix / validation matrix',takeaway='Technical proof, customer proof and commercial proof must connect before scale.',body=base.table(['Hypothesis / input','Evidence today','Next validation'],evidence,[24,37,39]),note='Sources: earlier internal experiments, official category examples, '+source_vase+' and '+source_model+'. Simulation can test an operating policy; it cannot establish member retention.',cls='compact')
    change('a-audit',takeaway='HTML-only V2 revision. The existing decks, shared styles, data and PDF exports remain intact.')
    replace_html(soup.select_one('#a-audit .decision-strip'),'<strong>V2 build:</strong> <a href="../presentation/build_consulting_v2.py">build_consulting_v2.py</a> · <a href="v2-notes.md">revision and evidence notes</a> · <a href="index.html">open unchanged V1</a>. No PDF is generated.')

    apply_completed_benchmarks(soup)
    apply_graphical_revision(soup)
    # Rebuild section navigation and numbering after the editorial insertions.
    slides=soup.select('section.slide')
    for index,slide in enumerate(slides,1):
        footer=slide.select_one('.footer')
        replace_html(footer,'<span class="brand">'+wordmark()+'</span>'+''.join(f'<span class="{"active" if section==slide["data-section"] else ""}">{section}</span>' for section in ['Overview','Product','Evidence','Business','Implementation','Appendix'])+f'<span class="page">V2 · {index:02d} / {len(slides):02d}</span>')
        heading=slide.select_one('.slide-title')
        if heading:slide['aria-label']=heading.get_text(' ',strip=True)
    # Matplotlib separates SVG path commands with newlines plus trailing spaces.
    # Keep the separators while producing a whitespace-clean committed HTML.
    return '\n'.join(line.rstrip() for line in str(soup).splitlines())+'\n',len(slides)


def main():
    protected=[SITE/'index.html',SITE/'deck.css',SITE/'premium.css',SITE/'deck.js',ROOT/'site-vnext'/'index.html',*sorted((ROOT/'submission').glob('*.pdf'))]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    html,count=build()
    target=SITE/'index-v2.html'
    target.write_text(html,encoding='utf-8')
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest for path,digest in before.items())
    print(f'Built {target}: {count} slides. Existing decks, shared assets and PDFs unchanged. No PDF generated.')


if __name__=='__main__':
    main()

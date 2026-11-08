"""Populate V2 exhibits from executed benchmarks, keeping their limits visible."""
import copy
import json
from pathlib import Path

from bs4 import BeautifulSoup
import build_consulting_deck as base
from consulting_art_direction import detail_list

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/benchmarks/v2'
LABELS={'fixed0':'Guard only · no extra buffer','fixed5':'Fixed +5 buffer','fixed10':'Fixed +10 buffer',
        'reactive':'Reactive forecast buffer','rolling_average':'Rolling LP + averages',
        'rolling_ml':'Rolling LP + learned forecasts','oracle_reference':'Oracle-input LP reference'}


def set_html(node,html):
    node.clear()
    for child in list(BeautifulSoup(html,'html.parser').contents):node.append(child)


def occupancy_chart(metrics):
    parts=[base.txt(25,24,'MAE (% of capacity; lower is better)',19,'#53647a','start')]
    bottom,height,ceiling=335,255,7
    for v in (0,2,4,6):
        y=bottom-v/ceiling*height
        parts.extend([f'<line x1="65" y1="{y}" x2="885" y2="{y}" stroke="#d5dde7"/>',base.txt(52,y+6,f'{v}%',18,'#53647a','end')])
    for i,row in enumerate(metrics):
        center=165+i*210
        for offset,key,color in [(-48,'last_week','#8795a7'),(0,'adjusted','#a8bddd'),(48,'ensemble','#102a43')]:
            value=row['mae_pct_capacity'][key];bar=value/ceiling*height
            parts.append(f'<rect x="{center+offset-18}" y="{bottom-bar}" width="36" height="{bar}" fill="{color}"/>')
            parts.append(base.txt(center+offset,bottom-bar-10,f'{value:.2f}',20,weight=550))
        parts.append(base.txt(center,374,str(row['minutes'])+' min',21))
    return base.svg_wrap(parts,410,'Public UCI occupancy MAE: last week, adjusted last week and ensemble at four horizons')


def apply_completed_benchmarks(soup):
    if not all((OUT/f).exists() for f in ['rolling.json','occupancy.json','report.md']):
        return
    r=json.loads((OUT/'rolling.json').read_text());o=json.loads((OUT/'occupancy.json').read_text())
    b=r['settings']['base_100'];p=b['policies']
    report='<a href="../analysis/benchmarks/v2/report.md">Executed benchmark report · 8 Nov 2026</a>'
    protocol='<a href="../analysis/benchmarks/v2/protocol.md">Protocol and assumptions</a>'
    code='<a href="../analysis/benchmark_rolling_v2.py">Offline optimizer code</a>'
    def change(id,title,takeaway,body,note,compact=False):
        slide=soup.find(id=id)
        for selector,text in [('.slide-title',title),('.takeaway',takeaway),('.content',body),('.source',note)]:set_html(slide.select_one(selector),text)
        if compact:slide['class']=['slide','compact']
        return slide
    def add(id,title,takeaway,body,note):
        slide=copy.deepcopy(soup.find(id='a-method'));slide['id']=id
        soup.find(id='a-method').insert_before(slide)
        change(id,title,takeaway,body,note,True)
    set_html(soup.select_one('#cover .cover-context'),'V2 · offline benchmarks + pilot proposal')
    set_html(soup.select_one('#executive .recommendation-logic article:first-child p'),'Offline tests compare seven policies. At 100 bays, the guard-only baseline matches the optimizer. Extra AI operating value needs stronger evidence.')
    set_html(soup.select_one('#service .service-rule p'),'An offline rolling LP balances planned booking opportunities and walk-in access over 180 minutes. Deployment remains proposed; the tested base case shows no advantage over the hard guard alone.')
    set_html(soup.select_one('#member .source'),'Existing app prototype, simulated data. The offline rolling LP is tested separately; app integration remains proposed. RM4 weekday / RM5 peak are pricing-test inputs, additional to ordinary parking charges.')
    set_html(soup.select_one('#admission .source'),'Offline 30-minute-batch research prototype; '+code+'. Six buckets span 180 minutes. Every real promise reserves current physical capacity; future quotas are plans only. Local integration and continuous-time operation remain untested.')
    comparison=base.table(['Policy','Served / day','Walk-ins / day','Idle bay-h*','Reject %'],
                         [[LABELS[k],f'{v["fulfilled"]:.1f}',f'{v["walkins"]:.1f}',f'{v["idle_protected_bay_hours"]:.1f}',f'{v["rejection_rate"]:.1%}'] for k,v in p.items()],
                         [38,15,18,16,13],{0:'highlight',5:'highlight'})
    result_note=detail_list([('No access uplift','All policies serve '+f'{p["rolling_ml"]["fulfilled"]:.1f}'+' accepted member arrivals/day in this case.'),
                             ('No AI premium','Guard only, averages, learned forecasts and oracle inputs produce identical base outcomes.'),
                             ('Buffer effect','More walk-ins versus +5/+10 buffers comes from releasing discretionary spare capacity.')])
    change('simulation','The hard guard matches the optimizer at 100 bays',
           '60 paired synthetic days: better forecasts do not establish additional AI operating value.',
           base.cols(base.module('Seven policies · identical external events','<div class="v2-result-table">'+comparison+'</div>'),base.module('What the comparison means',result_note),'v2-results-split'),
           'Source: '+report+'. *Idle free bays at bucket starts while walk-ins are rejected, including pending claims/margin. Zero valid-promise capacity failures in this base case; this is not a field guarantee.')
    demand=r['forecast_scores']['booking_demand'][-1];turn=r['forecast_scores']['turnover'][-1]
    last=o['metrics'][-1]
    validation='<div class="v2-validation-streams">'+''.join(f'<article><b>{a}</b><p>{text}</p><span>{note}</span></article>' for a,text,note in [
        ('Public occupancy',f'{o["test_forecasts"]:,} forecasts · {o["car_parks"]} car parks · six weekly tests.',f'180-min ensemble {last["mae_pct_capacity"]["ensemble"]:.2f}%; adjusted last week {last["mae_pct_capacity"]["adjusted"]:.2f}%.'),
        ('Synthetic booking demand',f'180-min count MAE {demand["models"]["ml"]["mae"]:.2f} vs {demand["models"]["average"]["mae"]:.2f} using averages.',f'WAPE {demand["models"]["ml"]["wape"]:.1%}; 80% interval coverage {demand["models"]["ml"]["interval80_coverage"]:.1%}. Local logs still needed.'),
        ('Synthetic turnover',f'30-min departure MAE {turn["models"]["ml"]["departure_count_mae"]:.2f} vs {turn["models"]["average"]["departure_count_mae"]:.2f}.','Currently parked cohort only; no local entry/exit test.')])+'</div>'
    legend='<div class="legend"><span><i style="background:#8795a7"></i>Last week</span><span><i style="background:#a8bddd"></i>Adjusted last week</span><span><i style="background:#102a43"></i>Ensemble</span></div>'
    change('forecast','Three-hour forecasts: public data and synthetic tests',
           'Keep prediction accuracy, operational benefit and local validity as three separate questions.',
           base.cols(base.module('Public occupancy · causal weekly holdout',base.chart(occupancy_chart(o['metrics']),'A stronger baseline matters: ML alone is worse than adjusted last week at all four horizons.')+legend),base.module('Three distinct evidence streams',validation),'wide-left'),
           'Source: '+report+'. New availability-time preprocessing changes the historical sample. Public occupancy is real; booking and turnover logs are synthetic. None establishes KL East performance.')
    # Update the evidence register without converting offline evidence into field proof.
    truth=soup.select_one('#must-be-true .v2-truths article:nth-child(4)')
    set_html(truth.select_one('h3'),'AI adds operating value')
    set_html(truth.select_one('div:nth-child(2) p'),'No uplift over guard only at 100 bays.')
    set_html(truth.select_one('div:nth-child(3) p'),'Local demand, objective and strongest-baseline test.')
    set_html(soup.select_one('#must-be-true .source'),'Sources: public comparator programmes, Vase.ai survey, financial scenarios and '+report+'. Offline results do not validate local demand, customer retention or a commercial AI premium.')

    sizes=[]
    for key,label in [('size_50_same_demand','50 · same demand'),('base_100','100 · same demand'),('size_150_same_demand','150 · same demand'),('size_50_scaled','50 · half demand'),('size_150_scaled','150 · 1.5× demand')]:
        v=r['settings'][key]['policies']['rolling_ml']
        sizes.append((label,f'{v["fulfilled"]:.1f}',f'{v["walkins"]:.1f}',f'{v["rejection_rate"]:.1%}'))
    change('a-optimizer-study','Appendix / capacity and forecast ablation',
           'Test the strongest simple guard before assigning value to optimization or ML.',
           base.cols(base.module('Sizing · rolling learned-forecast LP',base.table(['Bays / demand','Served/day','Walk-ins/day','Reject %'],sizes,[40,20,24,16])),
                     base.module('Ablation and objective sensitivity',detail_list([
                         ('100 bays','Guard only = LP + averages = LP + learned forecasts = oracle reference on base operating outcomes.'),
                         ('50 bays','Tighter capacity changes the trade-off; inspect rejection and walk-ins together. No general optimizer superiority is established.'),
                         ('Weights','Member weights 1 and 10 did not create an ML advantage in the tested settings.'),
                         ('Decision','Choose complexity only when local replay shows material benefit over the shared hard guard.')]))),
           'Source: '+report+'; '+protocol+'. Same-demand and demand-scaled cases are distinct. The forecast ablation changes demand and survival models together; it does not isolate each input.',True)

    occupancy_rows=[[f'{v["minutes"]} min',f'{v["n"]:,}',f'{v["mae_pct_capacity"]["last_week"]:.2f}%',f'{v["mae_pct_capacity"]["adjusted"]:.2f}%',f'{v["mae_pct_capacity"]["ensemble"]:.2f}%',f'{v["interval_80_coverage"]:.1%}'] for v in o['metrics']]
    synthetic_rows=[[f'{v["minutes"]} min',f'{v["models"]["average"]["mae"]:.2f}',f'{v["models"]["ml"]["mae"]:.2f}',f'{v["models"]["ml"]["wape"]:.1%}'] for v in r['forecast_scores']['booking_demand']]
    add('a-forecast-results','Appendix / forecast results and calibration',
        'Public occupancy validates an occupancy task; synthetic requests validate only this generator.',
        base.cols(base.module('Public occupancy · MAE % of capacity',base.table(['Ahead','N','Last week','Adjusted','Ensemble','Coverage*'],occupancy_rows,[16,15,17,17,18,17])+base.strip('Train → blend week → calibration week → test week. No future reading is rounded backwards into a feature.')),
                  base.module('Synthetic cumulative requests',base.table(['Ahead','Average MAE','Learned MAE','Learned WAPE'],synthetic_rows,[24,25,25,26])+base.bullets(['160 training days, 40 calibration days, 60 held-out days.','Intervals are calibrated on earlier days; demand and turnover targets are separate.','No local booking demand, indoor occupancy or causal customer result is claimed.']))),
        'Source: '+report+'. *Empirical coverage of nominal 80% intervals. Test horizons use different sample sizes; dates and preprocessing are recorded in occupancy.json.')
    stress_rows=[]
    names={'spike':'Demand ×1.6','long_stays':'Stays ×1.6','late_arrivals':'More late arrivals','no_shows':'More no-shows','forecast_bias':'Biased forecasts','count_drift':'Detected undercount','outage':'Network pause','undetected_drift':'Undetected undercount'}
    for key,label in names.items():
        v=r['settings'][key]['policies']['rolling_ml']
        stress_rows.append((label,f'{v["fulfilled"]:.1f}',f'{v["rejection_rate"]:.1%}',f'{v["failed"]:.2f}',f'{v["claim_violations"]:.2f}'))
    negative=r['settings']['undetected_drift']['policies']['rolling_ml']
    add('a-stress-results','Appendix / safety depends on verified state',
        'Detected faults can pause new commitments; an undetected undercount breaks the capacity invariant.',
        base.cols(base.module('20 paired days per stress · learned-forecast LP',base.table(['Stress','Served/day','Reject %','Failed/day','Claim breaks/day'],stress_rows,[34,17,14,17,18])),
                  base.module('What the negative control reveals',detail_list([
                      ('Broken ledger',f'An eight-car undercount creates {negative["claim_violations"]:.2f} overcommitted buckets and {negative["physical_entry_denials"]:.1f} physical walk-in denials/day.'),
                      ('Detected faults','Both detected-count drift and network loss use the same four-bucket pause, with a functioning local ledger.'),
                      ('Boundary','No valid accepted arrival fails in this random stress replay. A separate crafted test forces that failure with a wrong ledger.'),
                      ('Pilot priority','Validate reconciliation, stale-data detection and independent recovery before live acceptance.')]))),
        'Source: '+report+'. Guarded-scenario zero failures are conditional on accurate counts and ledger. This is a synthetic control test, not verified sensor or network resilience.')

    methods=[('Public occupancy',f'{o["test_forecasts"]:,} forecasts; {o["car_parks"]} UK car parks; 30/60/120/180 min.','Same-site historical time holdout. No local booking or entry/exit labels.'),
             ('Camera perception','Earlier 99.05% on 78,270 held-out-camera patches.','One outdoor Italian site. Indoor transfer and false-free errors remain untested.'),
             ('Rolling optimizer',f'{r["policy_day_runs"]:,} synthetic policy-day runs; seven policies; sizing, ablation and stress.','No benefit over guard only at 100 bays. Undetected-state error can break promises.'),
             ('Commercial proof','Scenario-based fees, visits, capture and cost model.','No local paid conversion, incremental visits, approved capture or installed quote.')]
    change('a-method','Appendix / what is demonstrated and what remains open',
           'Executed offline results narrow the claims; customer and deployment evidence still need a pilot.',
           base.table(['Evidence layer','Completed evidence','Boundary / missing validation'],methods,[23,39,38]),
           'Sources: '+report+'; <a href="../analysis/cv_benchmark_results.txt">earlier camera benchmark</a>. Offline simulation does not prove local safety, retention or financial return.',True)
    evidence=[('Local parking need','Published category precedent; no KL East demand baseline.','Member interviews and price-dependent booking conversion.'),
              ('Booking forecasts','Synthetic held-out request/count and turnover tests completed.','Local timestamped requests and independently reconciled entry/exit logs.'),
              ('Operating benefit','Guard only matches rolling LP at 100 bays.','Strong-baseline local replay; justify complexity and policy objectives.'),
              ('ML benefit','Synthetic forecast errors improve; base operations do not.','Test whether prediction changes actual decisions and outcomes.'),
              ('State reliability','Guarded runs pass; undetected undercount fails.','Local detection, reconciliation, recovery and independent verification.'),
              ('Commercial value','Financial sensitivity remains illustrative.','Controlled visits, finance-approved capture and complete installed/support scope.')]
    change('a-evidence','Appendix / updated validation matrix',
           'The remaining gaps are local validity, reliable state and attributable commercial value.',
           base.table(['Question','Evidence today','Next validation'],evidence,[23,39,38]),
           'Sources: '+report+' and <a href="../presentation/booking_economics.py">shared financial model</a>. No retention, willingness-to-pay or installed-cost evidence was created by simulation.',True)
    set_html(soup.select_one('#a-audit .takeaway'),'HTML-only V2, now linked to executed offline benchmarks. Existing decks and PDF exports remain unchanged.')
    set_html(soup.select_one('#a-audit .decision-strip'),'<strong>Executed evidence:</strong> '+report+' · '+protocol+' · '+code+' · <a href="v2-notes.md">revision notes</a>. No PDF generated.')

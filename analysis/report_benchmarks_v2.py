"""Build the human-readable report from the completed, checksum-bound runs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'benchmarks/v2'
LABELS={'fixed0':'Guard only (0 extra buffer)','fixed5':'Fixed +5 buffer','fixed10':'Fixed +10 buffer',
        'reactive':'Reactive forecast buffer','rolling_average':'Rolling LP + averages',
        'rolling_ml':'Rolling LP + learned forecasts','oracle_reference':'Oracle-input rolling LP reference'}


def markdown_table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',
                      *['| '+' | '.join(map(str,row))+' |' for row in rows]])


def main():
    r=json.loads((OUT/'rolling.json').read_text());o=json.loads((OUT/'occupancy.json').read_text())
    assert r['code_sha256']==hashlib.sha256((ROOT/'benchmark_rolling_v2.py').read_bytes()).hexdigest()
    assert r['protocol_sha256']==hashlib.sha256((OUT/'protocol.md').read_bytes()).hexdigest()
    assert o['code_sha256']==hashlib.sha256((ROOT/'benchmark_occupancy_v2.py').read_bytes()).hexdigest()
    allrows=json.loads((ROOT/'benchmark_data/rolling-v2-days.json').read_text())
    guarded=[row for row in allrows if row['setting']!='undetected_drift']
    assert all(row[k]==0 for row in guarded for k in ['failed','physical_violations','claim_violations','physical_entry_denials','solver_failures'])
    assert all(row['requests']==row['accepted']+row['rejected'] for row in allrows)
    assert all(row['valid_accepted_arrivals']==row['fulfilled']+row['failed'] for row in allrows)
    assert all(row['accepted']==row['valid_accepted_arrivals']+row['late_expired']+row['no_show_expired'] for row in allrows)
    b=r['settings']['base_100'];p=b['policies']
    assert all(p['rolling_ml'][key]==p['fixed0'][key] for key in ['accepted','fulfilled','walkins','idle_protected_bay_hours'])
    lines=['# ParkFlow V2: completed offline benchmarks','',
           'Run date: 8 November 2026. These are executed offline experiments, not field results. No PDF was produced.',
           '', '## What the results establish', '',
           f'- Public occupancy: {o["test_forecasts"]:,} held-out forecasts from {o["car_parks"]} UK car parks, across six weekly tests. At 180 minutes the ensemble has {o["metrics"][-1]["mae_pct_capacity"]["ensemble"]:.2f}% MAE of capacity versus {o["metrics"][-1]["mae_pct_capacity"]["last_week"]:.2f}% for last week and {o["metrics"][-1]["mae_pct_capacity"]["adjusted"]:.2f}% for adjusted last week.',
           f'- Synthetic policy study: {r["policy_day_runs"]:,} policy-day runs, with 160 separate training days, 40 calibration days and {r["test_days"]} paired main test days. Stress and weight cases use 20 paired days each.',
           '- At 100 bays, the guard-only, average-forecast, ML-forecast and oracle-reference policies produce identical booking and walk-in outcomes. **No incremental optimization or ML benefit is established in this base case.**',
           '- The walk-in gain against +5/+10 buffers is explained by removing discretionary spare buffer in this setting. It must not be marketed as an AI gain.',
           '- Learned synthetic booking forecasts improve prediction error, but that does not translate into a demonstrated base-case operating advantage.',
           '- Verified-state guarded runs show no capacity-denied valid accepted arrivals, over-capacity entry or claim-invariant violations. The negative-control undercount can break promises: exact reconciliation is a condition, not an established local capability.',
           '- Local demand, willingness to pay, incremental visits, landlord capture and installed cost remain unvalidated.',
           '', '## Public-data occupancy', '',
           'Metric: mean absolute error as percent of physical capacity (percentage points). The sample is matched between models within each horizon. Different horizons have different sample sizes. Current observations become available only at the next half-hour boundary; no reading is rounded backwards into a feature.', '',
           markdown_table(['Ahead','N','Last week','Persistence','Adjusted last week','ML alone','Ensemble','80% coverage'],
                          [[f'{v["minutes"]} min',f'{v["n"]:,}',*[f'{v["mae_pct_capacity"][k]:.2f}%' for k in ['last_week','persistence','adjusted','ml','ensemble']],f'{v["interval_80_coverage"]:.1%}'] for v in o['metrics']]),
           '', 'ML alone is worse than adjusted last week at every tested horizon. The blend adds a modest improvement over that stronger baseline. Empirical interval coverage is not a universal calibration guarantee. Earlier 2.07%/5.34% results use different timing/preprocessing and should not be substituted for these values.',
           '', '## Main synthetic operating comparison', '',
           '100 bays; 60 identical external-demand days per policy; two common spare safety bays. Member requests average 63.25/day. Every accepted promise reserves currently free capacity; all policies retain the same acceptance guard.', '',
           markdown_table(['Policy','Accepted/day','Served/day','Walk-ins/day','Idle bay-h/day*','Rejected requests'],
                          [[LABELS[k],f'{v["accepted"]:.2f}',f'{v["fulfilled"]:.2f}',f'{v["walkins"]:.2f}',f'{v["idle_protected_bay_hours"]:.2f}',f'{v["rejection_rate"]:.1%}'] for k,v in p.items()]),
           '', '*Idle bay-hours count bucket-start physically free bays while walk-ins were rejected, including real pending claims and the common safety margin. The 30-minute-batch proxy is not a continuous-time measurement.',
           '', 'Accepted and served differ because of no-shows and arrivals after grace. A booking accepted but not used is not a capacity failure. The oracle-input rolling LP is a reference with fitted future-cohort kernels, not a globally optimal upper bound.',
           '', 'Mechanism boundary: this first harness batches events every 30 minutes, processes requests before the walk-in batch and assumes requests arrive 30 minutes before their due bucket. That ordering and lead time make the current-capacity guard a strong baseline. Longer booking lead times, minute-level interleaving, other objectives and real demand could change the trade-off; this run cannot establish that optimization is generally useless or generally superior.',
           '', '### Paired differences, rolling ML minus comparator', '',
           markdown_table(['Comparator','Outcome','Mean difference/day','Bootstrap 95% interval'],
                          [[LABELS[v['second']],v['metric'],f'{v["mean_delta"]:+.2f}',f'[{v["ci95"][0]:+.2f}, {v["ci95"][1]:+.2f}]'] for v in b['paired']]),
           '', 'Intervals resample paired days, conditional on this synthetic generator. They do not include uncertainty about actual mall demand or model structure.',
           '', '## Synthetic demand and turnover holdouts', '',
           markdown_table(['Request horizon','Examples','Average MAE','Learned MAE','Average WAPE','Learned WAPE','Learned 80% coverage'],
                          [[str(v['minutes'])+' min',v['n'],f'{v["models"]["average"]["mae"]:.2f}',f'{v["models"]["ml"]["mae"]:.2f}',f'{v["models"]["average"]["wape"]:.1%}',f'{v["models"]["ml"]["wape"]:.1%}',f'{v["models"]["ml"]["interval80_coverage"]:.1%}'] for v in r['forecast_scores']['booking_demand']]),
           '', 'Request targets are cumulative requests over the next horizon. WAPE is the sum of absolute errors divided by total requests, not occupancy error.', '',
           markdown_table(['Departure horizon','Snapshots','Mean-duration MAE','Learned survival MAE','Learned 80% coverage'],
                          [[str(v['minutes'])+' min',v['n'],f'{v["models"]["average"]["departure_count_mae"]:.2f}',f'{v["models"]["ml"]["departure_count_mae"]:.2f}',f'{v["models"]["ml"]["interval80_coverage"]:.1%}'] for v in r['forecast_scores']['turnover']]),
           '', 'Turnover is evaluated on the currently parked cohort in fixed-5-policy snapshots. It excludes new entrants after the forecast origin. Training is completed synthetic trip history, not Birmingham occupancy or real local plate logs.',
           '', '## Capacity sensitivity', '',
           markdown_table(['Case','Bays','Demand multiplier','ML served/day','ML walk-ins/day','ML rejection','Guard-only walk-ins/day'],
                          [[name,v['capacity'],v['demand_scale'],f'{v["policies"]["rolling_ml"]["fulfilled"]:.2f}',f'{v["policies"]["rolling_ml"]["walkins"]:.2f}',f'{v["policies"]["rolling_ml"]["rejection_rate"]:.1%}',f'{v["policies"]["fixed0"]["walkins"]:.2f}'] for name,v in r['settings'].items() if name in ['base_100','size_50_same_demand','size_150_same_demand','size_50_scaled','size_150_scaled']]),
           '', 'Capacity must be chosen from observed simultaneous demand, layout and full cost. These synthetic admission totals do not justify a particular installed zone size.',
           '', '## Stress and fault results', '',
           markdown_table(['Scenario','Days','ML served/day','ML request rejection','ML capacity-denied promises/day','ML claim violations/day','ML physical walk-in denials/day'],
                          [[name,v['days'],f'{v["policies"]["rolling_ml"]["fulfilled"]:.2f}',f'{v["policies"]["rolling_ml"]["rejection_rate"]:.1%}',f'{v["policies"]["rolling_ml"]["failed"]:.2f}',f'{v["policies"]["rolling_ml"]["claim_violations"]:.2f}',f'{v["policies"]["rolling_ml"]["physical_entry_denials"]:.2f}'] for name,v in r['settings'].items() if name in ['spike','long_stays','late_arrivals','no_shows','forecast_bias','count_drift','outage','undetected_drift']]),
           '', 'Detected count drift and network outage are two labels for the same four-bucket admission pause with a functioning local verified ledger. They are not independent sensor/network resilience validations. Undetected drift deliberately removes eight occupied records from both sources, revealing the cost of breaking that assumption. Physical entry is capped, but a prior accepted promise can fail.',
           '', 'In these 20 randomly generated undercount days, the learned-forecast policy records zero actually denied valid accepted arrivals, but 2.85 overcommitted buckets and 9.30 physical walk-in denials per day. A separate crafted adversarial test forces a valid accepted arrival to fail when the ledger is wrong. These are different findings; the random replay is not evidence of observed promise failures.',
           '', '## Objective-weight sensitivity', '',
           markdown_table(['Member weight','ML served/day','ML walk-ins/day','Average served/day','Average walk-ins/day'],
                          [[v['member_weight'],*[f'{v["policies"][p][m]:.2f}' for p in ['rolling_ml','rolling_average'] for m in ['fulfilled','walkins']]] for k,v in r['settings'].items() if k in ['weight_1','weight_10']]),
           '', 'The main weight 5 is an explicitly chosen operating preference, not a monetary valuation. Weights 1 and 10 did not create an ML advantage in the tested cases.',
           '', '## Reproduce', '', '```powershell',
           'python -B analysis/benchmark_occupancy_v2.py --download',
           'python -B analysis/test_benchmark_v2.py',
           'python -B analysis/benchmark_rolling_v2.py',
           'python -B analysis/report_benchmarks_v2.py', '```', '',
           'The first command downloads the official UCI CSV to `analysis/benchmark_data/dataset.csv`; omit `--download` to reuse it. Raw forecasts and per-day simulation output remain in that ignored data directory; summary JSON, this report and the frozen/extended protocol are versioned.', '',
           f'CSV SHA256: `{o["csv_sha256"]}`. The rolling report binds the executed code and protocol by SHA256. Environment: {json.dumps(r["environment"])}.', '',
           'Seven adversarial control tests cover current-capacity guarding despite optimistic departure forecasts, long stays, no-show/late expiry, existing promises during a fault, deterministic event replay, future-feature isolation and failure when the verified-count assumption is broken.', '',
           'Sources: [UCI dataset](https://archive.ics.uci.edu/dataset/482/parking+birmingham), [SciPy LP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html), [LightGBM API](https://lightgbm.readthedocs.io/en/stable/Python-API.html). Full settings and limitations: [protocol](protocol.md), [rolling results](rolling.json), [occupancy results](occupancy.json).', '']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Verified all run invariants and checksums; wrote',OUT/'report.md')


if __name__=='__main__':main()

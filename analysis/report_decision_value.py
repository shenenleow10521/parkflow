"""Publish every prespecified result, including nulls and adverse trade-offs."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'benchmarks/decision_value'
LABELS={'guard':'Current-capacity guard','fixed5':'Fixed +5 buffer','fixed10':'Fixed +10 buffer',
        'calibrated_fixed':'Calibration-selected fixed buffer','reactive':'Reactive adaptive buffer',
        'lp_mean':'LP + historical means','lp_adaptive':'LP + adaptive means','lp_linear':'LP + linear forecast',
        'lp_ml':'LP + LightGBM forecast','request_oracle':'Future-request oracle reference'}


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',
                      *['| '+' | '.join(map(str,row))+' |' for row in rows]])


def main():
    result=json.loads((OUT/'results.json').read_text())
    assert not result['quick_development_run']
    assert result['code_sha256']==hashlib.sha256((ROOT/'benchmark_decision_value.py').read_bytes()).hexdigest()
    assert result['protocol_sha256']==hashlib.sha256((OUT/'protocol.md').read_bytes()).hexdigest()
    rows=json.loads((ROOT/'benchmark_data/decision-value-days.json').read_text())
    assert len(rows)==result['policy_day_runs']
    assert all(v[k]==0 for v in rows for k in ['failed','claim_violations','physical_violations','solver_failures'])
    assert all(v['accepted']==v['fulfilled']+v['no_shows']+v['expired_late'] for v in rows)
    base=result['settings']['mixed_100']
    main_pairs={v['comparator']:v for v in base['paired'] if v['metric']=='weighted_score'}
    lines=['# Does forecasting change parking decisions?','',
           'Completed 8 November 2026. This is a synthetic, minute-resolution offline experiment. It is not a local mall validation or a replacement for the earlier V2 results.', '',
           f'{result["policy_day_runs"]:,} policy-day runs; {result["train_days"]} training days; {result["calibration_days"]} calibration days; {base["days"]} paired main test days. All ten policies see the same external events. No test outcomes select model parameters, fixed buffers or scenarios.', '',
           '## Finding', '',
           f'The learned-forecast LP changes protection decisions and improves the declared operating score versus the linear-forecast LP by {main_pairs["lp_linear"]["mean_delta"]:.2f}/day (paired 95% interval {main_pairs["lp_linear"]["ci95"][0]:.2f} to {main_pairs["lp_linear"]["ci95"][1]:.2f}). However, its score difference versus the adaptive-forecast LP is {main_pairs["lp_adaptive"]["mean_delta"]:.2f}/day (interval {main_pairs["lp_adaptive"]["ci95"][0]:.2f} to {main_pairs["lp_adaptive"]["ci95"][1]:.2f}), which does not establish an advantage.', '',
           f'The calibration-selected fixed buffer outperforms the learned-forecast LP on the declared score: ML minus fixed is {main_pairs["calibrated_fixed"]["mean_delta"]:.2f}/day. The fixed policy serves more member arrivals while admitting fewer walk-ins; the full trade-off is reported below. The oracle-request LP also trails the selected fixed buffer on this score, suggesting that controller design, not request-forecast accuracy alone, limits the current mechanism. This is an inference from the comparison, not a demonstrated universal limitation.', '',
           '**Conclusion: this experiment demonstrates that forecast choice can change actions, but it still does not justify a general operational superiority claim for ML against the strongest tested simple alternatives.** The narrower improvement over linear prediction, null comparisons, adverse trade-offs and scenario assumptions must all remain visible.', '',
           '## What changed', '',
           '- Requests and walk-ins interleave at minute resolution; requests no longer all arrive before a 30-minute walk-in batch.',
           '- Booking lead times vary from 15 to 180 minutes. A 180-minute controller updates every 15 minutes and can reserve space for the upcoming request window.',
           '- Only request-demand forecasts change between LP variants. The survival model, future walk-in forecast, objective and physical guard are identical.',
           '- Historical averages, adaptive averages, linear ridge forecasts and LightGBM share the same as-of histories. The oracle sees future request counts only and is not a global optimal bound.',
           '- A fixed buffer is chosen using calibration days for each capacity/weight combination. It is not selected on test outcomes.', '',
           '## Critical assumption', '',
           '**Some synthetic booking surges follow an earlier walk-in wave. That predictive relationship is an assumption introduced to test a possible mechanism, not a sourced fact about KL East.** Quiet, unannounced and shifted-timing settings expose where this mechanism can fail. These runs can establish conditional simulator behaviour, not prove real-world ML value.', '',
           '## Main 100-bay comparison', '',
           'Primary preference score = 5 × member arrivals actually served + walk-ins admitted. This weight is not a monetary valuation. Accepted bookings reserve currently free capacity, including long-lead bookings; predictions never authorize a guarantee.', '',
           table(['Policy','Member served/day','Walk-ins/day','Request rejection','Idle bay-h/day','Preference score'],
                 [[LABELS[k],f'{v["fulfilled"]:.2f}',f'{v["walkins"]:.2f}',f'{v["rejection_rate"]:.1%}',f'{v["idle_protected_bay_hours"]:.2f}',f'{v["weighted_score"]:.2f}'] for k,v in base['policies'].items()]), '',
           f'The calibration-selected fixed additional buffer is {base["fixed_buffer"]} bays, on top of the two common spare safety bays. Idle bay-hours integrate free bays by minute when a walk-in is denied. No-show and expired-late outcomes remain separate from capacity-denied accepted arrivals.', '',
           '## Main paired differences: learned-forecast LP minus comparator', '',
           table(['Comparator','Outcome','Mean difference/day','Bootstrap 95% interval'],
                 [[LABELS[v['comparator']],v['metric'],f'{v["mean_delta"]:+.2f}',f'[{v["ci95"][0]:+.2f}, {v["ci95"][1]:+.2f}]'] for v in base['paired']]), '',
           'Intervals resample paired days 2,000 times. These are exploratory comparisons without multiple-comparison adjustment. They represent Monte Carlo uncertainty for this generator, not uncertainty about local demand or commercial value.', '',
           '## Results across every prespecified setting', '',
           table(['Setting','Days','Weight','ML members/day','ML walk-ins/day','Score delta vs adaptive LP','Score delta vs linear LP','Score delta vs calibrated fixed'],
                 [[name,v['days'],v['member_weight'],f'{v["policies"]["lp_ml"]["fulfilled"]:.2f}',f'{v["policies"]["lp_ml"]["walkins"]:.2f}',
                   *[f'{v["policies"]["lp_ml"]["weighted_score"]-v["policies"][k]["weighted_score"]:+.2f}' for k in ['lp_adaptive','lp_linear','calibrated_fixed']]] for name,v in result['settings'].items()]), '',
           'Quiet cases test a low-value setting. Unannounced pulses remove the preceding cue. Shifted pulses move that cue out of the training relationship. Capacity and lead-time cases keep external demand pairing intact. Weight changes expose the booking/walk-in trade-off.', '',
           '## Forecast error and changed actions', '',
           table(['Horizon','Origins','Mean MAE','Adaptive MAE','Linear MAE','Learned MAE','Learned WAPE'],
                 [[f'{v["minutes"]} min',v['n'],*[f'{v["models"][k]["mae"]:.2f}' for k in ['mean','adaptive','linear','ml']],f'{v["models"]["ml"]["wape"]:.1%}'] for v in base['forecast_errors']]), '',
           'Targets are cumulative incoming requests over the horizon. Forecast origins are restricted so the complete 180-minute target lies before the request cutoff. Histories exclude the current and all future events.', '',
           table(['Comparator','Fraction of control updates with a different protection target from ML'],
                 [[LABELS[k],f'{v:.1%}'] for k,v in base['different_action_fraction'].items()]), '',
           '## Full per-setting policy tables and paired intervals', '']
    for name,setting in result['settings'].items():
        lines += [f'### {name}', '',
                  table(['Policy','Accepted/day','Served/day','Walk-ins/day','Rejected','Score','Capacity failures','Claim violations'],
                        [[LABELS[k],f'{v["accepted"]:.2f}',f'{v["fulfilled"]:.2f}',f'{v["walkins"]:.2f}',f'{v["rejection_rate"]:.1%}',f'{v["weighted_score"]:.2f}',f'{v["failed"]:.2f}',f'{v["claim_violations"]:.2f}'] for k,v in setting['policies'].items()]), '',
                  table(['Comparator','Outcome','Mean delta','95% interval'],
                        [[LABELS[v['comparator']],v['metric'],f'{v["mean_delta"]:+.2f}',f'[{v["ci95"][0]:+.2f}, {v["ci95"][1]:+.2f}]'] for v in setting['paired']]), '']
    lines += ['## Safety and limits', '',
              'All completed runs have zero capacity-denied valid accepted arrivals, physical capacity violations, claim violations and failed solves. This follows the common verified-state guard and must not be sold as proof of camera or network reliability. The earlier V2 undetected-count counterexample still applies.', '',
              'The fixed buffer, request forecasts and artificial cue can alter the balance between member access and ordinary walk-in access. A positive preference-score difference is not Pareto superiority. Report counts and intervals, including costs to walk-ins. No visit-retention, willingness-to-pay, landlord-capture or financial-return claim follows.', '',
              '## Reproduce', '', '```powershell',
              'python -B analysis/test_decision_value.py',
              'python -B analysis/benchmark_decision_value.py',
              'python -B analysis/report_decision_value.py', '```', '',
              f'Environment: `{json.dumps(result["environment"])}`. Executed code SHA256: `{result["code_sha256"]}`. Protocol SHA256: `{result["protocol_sha256"]}`.', '',
              'The protocol is recorded before evaluation. All settings and null/adverse findings are retained. [Structured results](results.json), [protocol](protocol.md), [earlier V2 report](../v2/report.md).', '']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Verified result hashes, accounting and guards. Wrote',OUT/'report.md')


if __name__=='__main__':main()

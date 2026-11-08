# ParkFlow V2: completed offline benchmarks

Run date: 8 November 2026. These are executed offline experiments, not field results. No PDF was produced.

## What the results establish

- Public occupancy: 18,074 held-out forecasts from 28 UK car parks, across six weekly tests. At 180 minutes the ensemble has 4.42% MAE of capacity versus 6.02% for last week and 4.56% for adjusted last week.
- Synthetic policy study: 3,500 policy-day runs, with 160 separate training days, 40 calibration days and 60 paired main test days. Stress and weight cases use 20 paired days each.
- At 100 bays, the guard-only, average-forecast, ML-forecast and oracle-reference policies produce identical booking and walk-in outcomes. **No incremental optimization or ML benefit is established in this base case.**
- The walk-in gain against +5/+10 buffers is explained by removing discretionary spare buffer in this setting. It must not be marketed as an AI gain.
- Learned synthetic booking forecasts improve prediction error, but that does not translate into a demonstrated base-case operating advantage.
- Verified-state guarded runs show no capacity-denied valid accepted arrivals, over-capacity entry or claim-invariant violations. The negative-control undercount can break promises: exact reconciliation is a condition, not an established local capability.
- Local demand, willingness to pay, incremental visits, landlord capture and installed cost remain unvalidated.

## Public-data occupancy

Metric: mean absolute error as percent of physical capacity (percentage points). The sample is matched between models within each horizon. Different horizons have different sample sizes. Current observations become available only at the next half-hour boundary; no reading is rounded backwards into a feature.

| Ahead | N | Last week | Persistence | Adjusted last week | ML alone | Ensemble | 80% coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 30 min | 2,832 | 5.42% | 4.21% | 1.98% | 2.42% | 1.93% | 77.3% |
| 60 min | 5,956 | 5.70% | 7.12% | 2.92% | 3.13% | 2.75% | 78.2% |
| 120 min | 4,932 | 5.90% | 12.96% | 3.91% | 4.20% | 3.80% | 79.1% |
| 180 min | 4,354 | 6.02% | 17.81% | 4.56% | 5.02% | 4.42% | 79.8% |

ML alone is worse than adjusted last week at every tested horizon. The blend adds a modest improvement over that stronger baseline. Empirical interval coverage is not a universal calibration guarantee. Earlier 2.07%/5.34% results use different timing/preprocessing and should not be substituted for these values.

## Main synthetic operating comparison

100 bays; 60 identical external-demand days per policy; two common spare safety bays. Member requests average 63.25/day. Every accepted promise reserves currently free capacity; all policies retain the same acceptance guard.

| Policy | Accepted/day | Served/day | Walk-ins/day | Idle bay-h/day* | Rejected requests |
| --- | --- | --- | --- | --- | --- |
| Guard only (0 extra buffer) | 63.25 | 55.73 | 445.82 | 44.08 | 0.0% |
| Fixed +5 buffer | 63.25 | 55.73 | 425.55 | 84.18 | 0.0% |
| Fixed +10 buffer | 63.25 | 55.73 | 404.60 | 129.53 | 0.0% |
| Reactive forecast buffer | 63.25 | 55.73 | 434.30 | 69.64 | 0.0% |
| Rolling LP + averages | 63.25 | 55.73 | 445.82 | 44.08 | 0.0% |
| Rolling LP + learned forecasts | 63.25 | 55.73 | 445.82 | 44.08 | 0.0% |
| Oracle-input rolling LP reference | 63.25 | 55.73 | 445.82 | 44.08 | 0.0% |

*Idle bay-hours count bucket-start physically free bays while walk-ins were rejected, including real pending claims and the common safety margin. The 30-minute-batch proxy is not a continuous-time measurement.

Accepted and served differ because of no-shows and arrivals after grace. A booking accepted but not used is not a capacity failure. The oracle-input rolling LP is a reference with fitted future-cohort kernels, not a globally optimal upper bound.

Mechanism boundary: this first harness batches events every 30 minutes, processes requests before the walk-in batch and assumes requests arrive 30 minutes before their due bucket. That ordering and lead time make the current-capacity guard a strong baseline. Longer booking lead times, minute-level interleaving, other objectives and real demand could change the trade-off; this run cannot establish that optimization is generally useless or generally superior.

### Paired differences, rolling ML minus comparator

| Comparator | Outcome | Mean difference/day | Bootstrap 95% interval |
| --- | --- | --- | --- |
| Guard only (0 extra buffer) | fulfilled | +0.00 | [+0.00, +0.00] |
| Guard only (0 extra buffer) | walkins | +0.00 | [+0.00, +0.00] |
| Guard only (0 extra buffer) | idle_protected_bay_hours | +0.00 | [+0.00, +0.00] |
| Fixed +5 buffer | fulfilled | +0.00 | [+0.00, +0.00] |
| Fixed +5 buffer | walkins | +20.27 | [+18.28, +22.27] |
| Fixed +5 buffer | idle_protected_bay_hours | -40.10 | [-43.96, -36.25] |
| Fixed +10 buffer | fulfilled | +0.00 | [+0.00, +0.00] |
| Fixed +10 buffer | walkins | +41.22 | [+37.82, +44.62] |
| Fixed +10 buffer | idle_protected_bay_hours | -85.44 | [-92.33, -78.22] |
| Rolling LP + averages | fulfilled | +0.00 | [+0.00, +0.00] |
| Rolling LP + averages | walkins | +0.00 | [+0.00, +0.00] |
| Rolling LP + averages | idle_protected_bay_hours | +0.00 | [+0.00, +0.00] |

Intervals resample paired days, conditional on this synthetic generator. They do not include uncertainty about actual mall demand or model structure.

## Synthetic demand and turnover holdouts

| Request horizon | Examples | Average MAE | Learned MAE | Average WAPE | Learned WAPE | Learned 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| 30 min | 1500 | 1.27 | 1.20 | 51.4% | 48.4% | 77.2% |
| 60 min | 1440 | 2.03 | 1.73 | 40.1% | 34.2% | 78.3% |
| 120 min | 1320 | 3.38 | 2.56 | 32.3% | 24.5% | 81.7% |
| 180 min | 1200 | 4.75 | 3.27 | 29.4% | 20.2% | 82.9% |

Request targets are cumulative requests over the next horizon. WAPE is the sum of absolute errors divided by total requests, not occupancy error.

| Departure horizon | Snapshots | Mean-duration MAE | Learned survival MAE | Learned 80% coverage |
| --- | --- | --- | --- | --- |
| 15 min | 1560 | 2.19 | 2.09 | 79.0% |
| 30 min | 1560 | 2.82 | 2.71 | 82.2% |

Turnover is evaluated on the currently parked cohort in fixed-5-policy snapshots. It excludes new entrants after the forecast origin. Training is completed synthetic trip history, not Birmingham occupancy or real local plate logs.

## Capacity sensitivity

| Case | Bays | Demand multiplier | ML served/day | ML walk-ins/day | ML rejection | Guard-only walk-ins/day |
| --- | --- | --- | --- | --- | --- | --- |
| base_100 | 100 | 1.0 | 55.73 | 445.82 | 0.0% | 445.82 |
| size_50_same_demand | 50 | 1.0 | 54.40 | 208.25 | 2.1% | 208.78 |
| size_150_same_demand | 150 | 1.0 | 55.73 | 594.80 | 0.0% | 594.80 |
| size_50_scaled | 50 | 0.5 | 28.73 | 215.08 | 0.2% | 215.08 |
| size_150_scaled | 150 | 1.5 | 82.05 | 676.08 | 0.0% | 676.08 |

Capacity must be chosen from observed simultaneous demand, layout and full cost. These synthetic admission totals do not justify a particular installed zone size.

## Stress and fault results

| Scenario | Days | ML served/day | ML request rejection | ML capacity-denied promises/day | ML claim violations/day | ML physical walk-in denials/day |
| --- | --- | --- | --- | --- | --- | --- |
| spike | 20 | 93.05 | 0.1% | 0.00 | 0.00 | 0.00 |
| long_stays | 20 | 56.75 | 0.7% | 0.00 | 0.00 | 0.00 |
| late_arrivals | 20 | 40.70 | 0.0% | 0.00 | 0.00 | 0.00 |
| no_shows | 20 | 41.65 | 0.0% | 0.00 | 0.00 | 0.00 |
| forecast_bias | 20 | 57.20 | 0.0% | 0.00 | 0.00 | 0.00 |
| count_drift | 20 | 50.25 | 12.3% | 0.00 | 0.00 | 0.00 |
| outage | 20 | 50.25 | 12.3% | 0.00 | 0.00 | 0.00 |
| undetected_drift | 20 | 57.20 | 0.0% | 0.00 | 2.85 | 9.30 |

Detected count drift and network outage are two labels for the same four-bucket admission pause with a functioning local verified ledger. They are not independent sensor/network resilience validations. Undetected drift deliberately removes eight occupied records from both sources, revealing the cost of breaking that assumption. Physical entry is capped, but a prior accepted promise can fail.

In these 20 randomly generated undercount days, the learned-forecast policy records zero actually denied valid accepted arrivals, but 2.85 overcommitted buckets and 9.30 physical walk-in denials per day. A separate crafted adversarial test forces a valid accepted arrival to fail when the ledger is wrong. These are different findings; the random replay is not evidence of observed promise failures.

## Objective-weight sensitivity

| Member weight | ML served/day | ML walk-ins/day | Average served/day | Average walk-ins/day |
| --- | --- | --- | --- | --- |
| 1.0 | 57.20 | 451.35 | 57.20 | 451.35 |
| 10.0 | 57.20 | 451.35 | 57.20 | 451.35 |

The main weight 5 is an explicitly chosen operating preference, not a monetary valuation. Weights 1 and 10 did not create an ML advantage in the tested cases.

## Reproduce

```powershell
python -B analysis/benchmark_occupancy_v2.py --download
python -B analysis/test_benchmark_v2.py
python -B analysis/benchmark_rolling_v2.py
python -B analysis/report_benchmarks_v2.py
```

The first command downloads the official UCI CSV to `analysis/benchmark_data/dataset.csv`; omit `--download` to reuse it. Raw forecasts and per-day simulation output remain in that ignored data directory; summary JSON, this report and the frozen/extended protocol are versioned.

CSV SHA256: `f1e28b9c697769a1a05cd20148241b60b1a73fee4907611163efc6fd9d12770a`. The rolling report binds the executed code and protocol by SHA256. Environment: {"python": "3.12.10", "numpy": "2.4.6", "scipy": "1.17.1", "lightgbm": "4.6.0"}.

Seven adversarial control tests cover current-capacity guarding despite optimistic departure forecasts, long stays, no-show/late expiry, existing promises during a fault, deterministic event replay, future-feature isolation and failure when the verified-count assumption is broken.

Sources: [UCI dataset](https://archive.ics.uci.edu/dataset/482/parking+birmingham), [SciPy LP](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html), [LightGBM API](https://lightgbm.readthedocs.io/en/stable/Python-API.html). Full settings and limitations: [protocol](protocol.md), [rolling results](rolling.json), [occupancy results](occupancy.json).

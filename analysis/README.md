# ParkFlow analysis: reproduce every number in the pitch deck

Each script runs on its own, writes its results file into this folder, and uses fixed random
seeds, so a rerun gives the same numbers. The simulations are Monte Carlo: each simulated day
draws arrivals, stay lengths and booking show-ups at random from research-based distributions,
repeated over 1,000 days.

## Setup

```
pip install -r requirements.txt
cd analysis
```

Tested with Python 3.12, numpy 2.4, pandas 3.0, scipy 1.17 and lightgbm 4.6.

## Scripts

| Script | What it tests | Writes | Deck |
|---|---|---|---|
| `simulate_pooling.py` | The 100-bay Priority Zone run five ways (no priority, VIP section, two fixed rules, the ParkFlow forecast rule) on the same 1,000 Monte Carlo days, plus stress tests. `python simulate_pooling.py extra` adds the learned-model and day-shock runs | `simulate_pooling_results.txt` | Impact; A1 |
| `simulate_carpark.py` | Every car in a 1,300-bay car park: search time and CO2 today, with level guidance, and with ParkFlow | `simulate_carpark_results.txt` | Impact; A2 |
| `simulate_zone_size.py` | Zone size (2&ndash;25% of the car park) &times; booking cap. `python simulate_zone_size.py layout 6 8 10` compares one block with the zone split into pieces | `simulate_zone_size_results.txt` (the layout run's output is in `layout_log.txt`) | A5 |
| `business_case.py` | Market size, cost sheet, per-mall revenue and the 7-year rollout | `business_case_results.txt` | Feasibility; A3, A4 |
| `backtest_ensemble.py` | The forecast (pattern model + LightGBM, blended, with conformal ranges) against "same time last week" on 30 real car parks | `backtest_ensemble_results.txt`, `backtest_ensemble_day.csv` | How it works; A6 |
| `backtest_birmingham.py` | The earlier single-model version of the backtest | `backtest_results.txt`, `backtest_sample_day.csv` | (superseded by the ensemble) |
| `simulate_saturday.py` | Phase 2 idea: asking just enough drivers to come later to cut entrance queues | `simulate_saturday.csv`, printed summary | (earlier draft) |

## Forecast data

The backtests use the public UCI Parking Birmingham dataset (CC BY 4.0), which is not stored here:

```
curl -LO https://archive.ics.uci.edu/static/public/482/parking+birmingham.zip
unzip parking+birmingham.zip
python backtest_ensemble.py dataset.csv
```

## Naming in the code

The scripts were written when free bookings went to SDP homeowners through PRIME. In the code,
"PRIME" and "members" now mean **free bookings**: booking vouchers for big spenders and, in phase 2,
top-tier rewards members. The model treats them the same way (80% show up, against 95% for paid
bookings), so the results do not change.

`simulate_zone_size.py` also saves the raw per-day results to `simulate_zone_size_days.npz`
(about 4 MB). It is regenerated on each run and not stored in git.

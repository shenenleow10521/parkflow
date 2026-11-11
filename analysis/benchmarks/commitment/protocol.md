# Commitment-ledger + stay-risk admission study

Specified 11 November 2026, before any outcome was computed. Code: `analysis/simulate_commitment.py`.

## Question

The proposed architecture is: advance reservation ledger -> stay-duration forecast -> rolling admission optimizer (15-minute refresh) -> verified-capacity guard. Does it honour more bookings **and/or** admit more walk-ins than simple rules **at the same booking-breach rate**, and does that advantage grow as the environment gets more complex?

A favourable result is not guaranteed. No gain means no gain, and it will be reported.

## What is calibrated to real data, what is assumed

Calibrated (copied from `simulate_pooling.py`, which cites its sources): walk-in stay lognormal fitted to quartiles 44/87/155 min (Mueller et al. 2026, >200,000 plate-camera stays); demand peaks 12:30 and 17:30 (Sun et al. 2025); booked stay = declared duration x noise (sd 0.25); opening 10:00-23:00; 30-minute arrival window.

Assumed (not evidence): the long-stay tail in level L3 (20% of walk-ins, median 240 min, sigma 0.5); the evening booking pulse; 90% show-up; the share of walk-ins whose stay class is observable (70%, e.g. returning plates); day-level stay shock sd 0.15. All are labelled synthetic.

## Policies (all share one physical guard: never admit when no bay is free)

- P0 Strict hold: a booking holds a bay from acceptance. Zero breach by construction.
- P1 Quota + due-soon: the existing fixed rule. Booking accepted if fewer than Q bookings are already pending within +/-60 min; a walk-in is admitted if free bays minus bookings due in the next 60 min minus a margin is at least 1. Q and margin tuned on calibration days.
- P2 Commit, expected stay (z=0), horizon 180 min: projects occupancy from the ledger and stay survival curves; no safety margin.
- P3 Commit, risk-adjusted, horizon H in {60,120,180,300,end of day}: same projection, admits only if mean + z x sd of projected occupancy plus the new car stays at or below capacity at every 15-minute checkpoint within H. z is tuned on calibration days. Bookings of any lead time are accepted on the same projection over their stay window.
- P4 Oracle departures (reference only): knows true departure times, z=0, H=180.

The planner's stay model is **empirical, fitted on 20 separate training days**, not the true distribution. In L3 it is either pooled (no class signal) or class-aware (signal on).

## Hold-out discipline

Tuning seeds (z, Q, margin): 51000-51059 (60 days). Test seeds: 61000-61199 (200 days). Training seeds for the stay model: 70000-70019. Knobs are chosen on calibration days only: maximise score subject to breach <= 1% of shown-up bookings. Test breach rates are reported; any policy above 1% on test is flagged, not retuned.

Score = 5 x bookings honoured + walk-ins admitted (the declared weight from the decision-value study; not RM). Components are always shown separately.

## Complexity ladder (fixed in advance; 100 bays, "busy" demand)

- L0 simple: bookings lead 15-120 min only; one lognormal stay population; no shocks.
- L1 + advance bookings: 30% of bookings placed 2-24 h ahead.
- L2 + evening event pulse: 100 extra bookings arriving 19:00-20:00, placed 3-24 h ahead.
- L3 + heterogeneity: long-stay tail and a day-level stay shock; run with and without the class signal.

## Predeclared claims and how they are judged

1. At each level, report P3 (best horizon, chosen on calibration) minus the better of P0/P1 in score at matched breach, with 95% paired bootstrap intervals (2,000 resamples over test days).
2. The "advantage grows with complexity" claim is supported only if the L0 -> L3 trend in that paired difference is monotone-ish and the L2/L3 intervals exclude zero. Otherwise it is not supported.
3. The horizon claim (3 h vs longer) is judged on the L3 rows only, because the stay tail drives it.
4. The oracle row bounds what a better stay forecast could add.

Synthetic results say what the mechanism can do under stated assumptions. They do not validate KL East demand, and the pilot remains the real test.

## Amendment (v2), written after the v1 run and before the v2 run

v1 (kept as `report_v1.md`, `results_v1.json`) revealed three problems, all in the study design rather than the policies:

1. The 60 calibration days were too few to see rare breach events. The calibration pick `P3_H60` passed at <=1% there but had 5.33% breach on test (level L2). The headline "+38/day" in v1 is therefore **not** a breach-matched result and should not be quoted.
2. The fixed-buffer baseline's best setting sat at the upper edge of its booking-quota grid (Q=40), so the baseline was under-tuned. v2 widens the baseline grids (Q up to 100 = effectively uncapped).
3. The score depends on the declared weight, so v2 reports W=1, 5 and 10 and a break-even weight.

v2 changes only: 150 calibration days (51000-51149), **fresh** test seeds 62000-62199, wider baseline grids, an added horizon of 480 min, and weight-sensitivity columns. The v1 test seeds were used to find these problems and are not reused. Selection rule, breach limit and claims are unchanged. Bug fixes made during smoke tests before v1 (rejected bookings arriving; waiting arrivals missing from the projection; oracle horizon) are not outcome-driven.

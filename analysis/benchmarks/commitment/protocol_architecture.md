# Architecture test v3: ML stay forecast inside the commitment planner

Specified 11 November 2026, before any v3 outcome was computed. Code: `analysis/simulate_architecture.py`. Extends `protocol.md` (v1/v2), which it does not replace.

## Question
How good must the stay-duration forecast be (layer 2) for the commitment planner (layers 1, 3, 4) to beat tuned simple rules at the same booking-failure rate? And what does an ML stay model actually achieve?

## What changes from v2
- Walk-in stays are generated from observable features instead of a hidden "long" class: purpose (shop / dine / cinema / errand; observed for 70% of cars), rain day (25% of days), and evening entry (after 17:00). The marginal stay distribution stays the calibrated lognormal (median 87 min, quartiles 44/155; Mueller et al. 2026), so only the *predictability* changes.
- **Informativeness rho** = share of log-stay variance explained by the features. Sweep rho in {0, 0.15, 0.3, 0.5, 0.75}. The feature effects (cinema +0.7, errand -0.6, dine -0.3 log-units before scaling; rain +0.5; evening +0.4) are **assumptions** with signs a reader can dispute; only the explained-variance share is controlled.
- The planner's stay model is either *pooled* (one lognormal fitted on 20 training days) or *ML* (LightGBM on log-stay with the observable features, 20 training days; residual sd from 10 separate validation days). Achieved out-of-sample R^2 is reported next to rho because the planner cannot see unobserved purposes.
- Level: advance bookings 30%, evening pulse 100, day-level stay shock sd 0.15 (the v2 "L3" without the long-stay class). Horizons {180, 300, end of day}.

## Discipline (unchanged)
Knobs tuned on 150 calibration days (51000-51149) to breach <= 1%; fresh test seeds 63000-63199; training seeds 70000-70019, validation 70020-70029. Score = 5 x bookings honoured + walk-ins; W=1 and W=10 also reported. Baselines: P0 strict hold, P1 quota+due-soon, P1b fixed buffer, each tuned on the wide v2 grids. Reference: full-information oracle.

## Judged claims
1. ML-stay commit minus best simple, by rho, with 95% paired bootstrap intervals; supported only where the interval excludes zero **and** test breach <= 1%.
2. Value of ML = (ML - pooled) / (oracle - pooled), by rho.
3. Weight sensitivity: the sign of claim 1 at W=1, 5, 10.
No gain means no gain. Synthetic results do not validate KL East; the pilot does.

## Amendment v4 (safety guard + horizon), written before any v4 outcome

The v3 commit policies lacked architecture layer 4 (verified-capacity safety guard): nothing stopped walk-ins taking the last free bays as a booking approached, and test breach overshot the 1% tuning limit (1.0-1.7%). v4 adds, as optional knobs on the commit planner only:
- **hold** (minutes, None/60/90): a walk-in is also admitted only if free bays minus bookings due within `hold` minutes minus `swing` spare bays is at least 1 (the same hard rule the quota baseline uses, applied on top of the stay-risk check).
- **swing** (0/2/4 spare bays); **horizon** H in {180, 300, 480}; **z** in {0, 1, 2}.

Selection (on 150 calibration days 51000-51149): for each failure target in {1%, 0.5%, 0.1%}, the highest-score config whose **calibration** breach is at most **half** the target (a margin against the overshoot seen in v3). Test on fresh seeds 64000-64199. Report test breach, breaches/day, honoured, walk-ins, and score minus c x breaches for c in {0, 10, 25} (a failed booking is worse than a lost booking). Baselines re-tuned with the same rule. Settings: rho = 0.5 (ML R^2 0.38) and rho = 0. Frontier (breach vs walk-ins) is drawn from calibration runs, not test. Fallback to another level and refunds are not modelled; a failure counts as a failure.

## Amendment v5 (design variants) and v6 (assumption Monte Carlo), written before any v5/v6 outcome

**v4 result that motivates this:** the hard hold did nothing, and at failure ceilings of 0.5% or lower the tuned quota rule matched or beat the commit planner. Remaining failures come from already-parked cars that overstay, and from the planner treating each confirmed booking as only 90% likely to show (which contradicts "confirmed bookings are hard constraints").

**v5 variants (all with the ML stay model, no hold; fixed list of 173 configs including baselines, none added after seeing results):**
- V0 reference: planned show-up 0.9, one z for bookings and walk-ins; H in {300, 480}, z in {0, 1, 2} (6 configs).
- V1 hard bookings: planned show-up 1.0 (a confirmed booking is a hard constraint); same grid (6).
- V2 separate risk: show-up in {0.9, 1.0}, booking-acceptance z in {0, 1, 2, 3}, walk-in z in {0, 1, 2}, H in {300, 480} (48).
- V3 hybrid: V2 plus the quota rule's selective booking cap (Qcap in {40, 60}), H = 480, booking z in {0, 1, 2} (36).
- Baselines: quota (42) and buffer (35) on the v2 grids.

Selection per failure target in {1%, 0.5%, 0.1%} on the 150 calibration days (51000-51149): highest score with calibration failure rate <= half the target. Test on **fresh** seeds 65000-65199. Report score, failures/day and score minus c per failure for c in {2, 10, 25} (c=2 approximates "fallback to another level plus refund"). Settings rho = 0.5 and 0.

**v6 Monte Carlo over assumptions** (uniform ranges, 60 worlds; the planner refits its stay model on each world's own training days; policy settings are the nominal-world v5 picks and are NOT retuned per world, which is the deployment-relevant test): show-up 0.75-0.95; day stay-shock sd 0.05-0.30; stay log-sd scale 0.8-1.2; booking volume x0.6-1.5; evening pulse 50-150; booked-stay overstay sd 0.15-0.40; stay predictability rho 0-0.75; advance-booking share 0.1-0.5. 30 days per world per policy (seeds 66000+, same days for all policies). Report, per policy pair, the share of worlds where the commit variant scores higher and the share of worlds where failures stay below each target, with medians and 10th-90th percentiles. The ranges are assumptions; they test sensitivity, they do not make the numbers true for KL East.

# Does forecasting change parking decisions?

Completed 8 November 2026. This is a synthetic, minute-resolution offline experiment. It is not a local mall validation or a replacement for the earlier V2 results.

3,000 policy-day runs; 160 training days; 40 calibration days; 60 paired main test days. All ten policies see the same external events. No test outcomes select model parameters, fixed buffers or scenarios.

## Finding

The learned-forecast LP changes protection decisions and improves the declared operating score versus the linear-forecast LP by 2.68/day (paired 95% interval 0.42 to 5.03). However, its score difference versus the adaptive-forecast LP is 0.12/day (interval -2.17 to 2.30), which does not establish an advantage.

The calibration-selected fixed buffer outperforms the learned-forecast LP on the declared score: ML minus fixed is -23.30/day. The fixed policy serves more member arrivals while admitting fewer walk-ins; the full trade-off is reported below. The oracle-request LP also trails the selected fixed buffer on this score, suggesting that controller design, not request-forecast accuracy alone, limits the current mechanism. This is an inference from the comparison, not a demonstrated universal limitation.

**Conclusion: this experiment demonstrates that forecast choice can change actions, but it still does not justify a general operational superiority claim for ML against the strongest tested simple alternatives.** The narrower improvement over linear prediction, null comparisons, adverse trade-offs and scenario assumptions must all remain visible.

## What changed

- Requests and walk-ins interleave at minute resolution; requests no longer all arrive before a 30-minute walk-in batch.
- Booking lead times vary from 15 to 180 minutes. A 180-minute controller updates every 15 minutes and can reserve space for the upcoming request window.
- Only request-demand forecasts change between LP variants. The survival model, future walk-in forecast, objective and physical guard are identical.
- Historical averages, adaptive averages, linear ridge forecasts and LightGBM share the same as-of histories. The oracle sees future request counts only and is not a global optimal bound.
- A fixed buffer is chosen using calibration days for each capacity/weight combination. It is not selected on test outcomes.

## Critical assumption

**Some synthetic booking surges follow an earlier walk-in wave. That predictive relationship is an assumption introduced to test a possible mechanism, not a sourced fact about KL East.** Quiet, unannounced and shifted-timing settings expose where this mechanism can fail. These runs can establish conditional simulator behaviour, not prove real-world ML value.

## Main 100-bay comparison

Primary preference score = 5 × member arrivals actually served + walk-ins admitted. This weight is not a monetary valuation. Accepted bookings reserve currently free capacity, including long-lead bookings; predictions never authorize a guarantee.

| Policy | Member served/day | Walk-ins/day | Request rejection | Idle bay-h/day | Preference score |
| --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 36.68 | 498.20 | 44.7% | 23.17 | 681.62 |
| Fixed +5 buffer | 57.15 | 436.47 | 20.5% | 62.00 | 722.22 |
| Fixed +10 buffer | 58.68 | 412.75 | 19.2% | 82.03 | 706.17 |
| Calibration-selected fixed buffer | 57.15 | 436.47 | 20.5% | 62.00 | 722.22 |
| Reactive adaptive buffer | 55.15 | 448.88 | 22.4% | 57.04 | 724.63 |
| LP + historical means | 44.40 | 477.85 | 33.2% | 34.48 | 699.85 |
| LP + adaptive means | 43.52 | 481.22 | 34.8% | 32.64 | 698.80 |
| LP + linear forecast | 42.55 | 483.48 | 36.1% | 31.10 | 696.23 |
| LP + LightGBM forecast | 43.98 | 479.00 | 34.5% | 34.87 | 698.92 |
| Future-request oracle reference | 47.57 | 469.85 | 32.1% | 43.43 | 707.68 |

The calibration-selected fixed additional buffer is 5 bays, on top of the two common spare safety bays. Idle bay-hours integrate free bays by minute when a walk-in is denied. No-show and expired-late outcomes remain separate from capacity-denied accepted arrivals.

## Main paired differences: learned-forecast LP minus comparator

| Comparator | Outcome | Mean difference/day | Bootstrap 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +7.30 | [+6.15, +8.35] |
| Current-capacity guard | walkins | -19.20 | [-22.82, -15.50] |
| Current-capacity guard | weighted_score | +17.30 | [+13.62, +21.08] |
| Calibration-selected fixed buffer | fulfilled | -13.17 | [-15.90, -10.37] |
| Calibration-selected fixed buffer | walkins | +42.53 | [+35.82, +49.38] |
| Calibration-selected fixed buffer | weighted_score | -23.30 | [-30.92, -15.55] |
| LP + historical means | fulfilled | -0.42 | [-0.92, +0.12] |
| LP + historical means | walkins | +1.15 | [-1.22, +3.38] |
| LP + historical means | weighted_score | -0.93 | [-2.97, +1.13] |
| LP + adaptive means | fulfilled | +0.47 | [-0.05, +1.08] |
| LP + adaptive means | walkins | -2.22 | [-4.55, -0.08] |
| LP + adaptive means | weighted_score | +0.12 | [-2.17, +2.30] |
| LP + linear forecast | fulfilled | +1.43 | [+0.77, +2.12] |
| LP + linear forecast | walkins | -4.48 | [-7.08, -2.07] |
| LP + linear forecast | weighted_score | +2.68 | [+0.42, +5.03] |

Intervals resample paired days 2,000 times. These are exploratory comparisons without multiple-comparison adjustment. They represent Monte Carlo uncertainty for this generator, not uncertainty about local demand or commercial value.

## Results across every prespecified setting

| Setting | Days | Weight | ML members/day | ML walk-ins/day | Score delta vs adaptive LP | Score delta vs linear LP | Score delta vs calibrated fixed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mixed_100 | 60 | 5.0 | 43.98 | 479.00 | +0.12 | +2.68 | -23.30 |
| quiet | 30 | 5.0 | 21.37 | 353.77 | +0.00 | +0.50 | +2.30 |
| unannounced | 30 | 5.0 | 47.57 | 475.37 | -1.20 | +1.93 | -29.90 |
| shifted | 30 | 5.0 | 46.07 | 480.03 | -1.47 | +2.23 | -24.93 |
| size_50 | 30 | 5.0 | 28.23 | 257.87 | -0.13 | +1.03 | -39.63 |
| size_150 | 30 | 5.0 | 57.90 | 626.57 | +3.33 | +4.77 | -22.40 |
| long_lead | 30 | 5.0 | 44.10 | 472.73 | -2.17 | +1.17 | -24.70 |
| weight_1 | 30 | 1.0 | 36.17 | 506.47 | +0.00 | +0.00 | +0.00 |
| weight_10 | 30 | 10.0 | 44.53 | 485.97 | +2.70 | +12.37 | -104.20 |

Quiet cases test a low-value setting. Unannounced pulses remove the preceding cue. Shifted pulses move that cue out of the training relationship. Capacity and lead-time cases keep external demand pairing intact. Weight changes expose the booking/walk-in trade-off.

## Forecast error and changed actions

| Horizon | Origins | Mean MAE | Adaptive MAE | Linear MAE | Learned MAE | Learned WAPE |
| --- | --- | --- | --- | --- | --- | --- |
| 30 min | 1740 | 6.04 | 5.25 | 3.93 | 3.35 | 66.2% |
| 60 min | 1740 | 11.65 | 10.74 | 8.85 | 8.13 | 77.3% |
| 120 min | 1740 | 21.95 | 21.89 | 19.78 | 19.57 | 88.3% |
| 180 min | 1740 | 30.28 | 31.92 | 28.51 | 28.28 | 83.4% |

Targets are cumulative incoming requests over the horizon. Forecast origins are restricted so the complete 180-minute target lies before the request cutoff. Histories exclude the current and all future events.

| Comparator | Fraction of control updates with a different protection target from ML |
| --- | --- |
| LP + historical means | 44.8% |
| LP + adaptive means | 29.8% |
| LP + linear forecast | 47.0% |

## Full per-setting policy tables and paired intervals

### mixed_100

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 41.58 | 36.68 | 498.20 | 44.7% | 681.62 | 0.00 | 0.00 |
| Fixed +5 buffer | 64.77 | 57.15 | 436.47 | 20.5% | 722.22 | 0.00 | 0.00 |
| Fixed +10 buffer | 66.45 | 58.68 | 412.75 | 19.2% | 706.17 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 64.77 | 57.15 | 436.47 | 20.5% | 722.22 | 0.00 | 0.00 |
| Reactive adaptive buffer | 62.53 | 55.15 | 448.88 | 22.4% | 724.63 | 0.00 | 0.00 |
| LP + historical means | 50.33 | 44.40 | 477.85 | 33.2% | 699.85 | 0.00 | 0.00 |
| LP + adaptive means | 49.40 | 43.52 | 481.22 | 34.8% | 698.80 | 0.00 | 0.00 |
| LP + linear forecast | 48.25 | 42.55 | 483.48 | 36.1% | 696.23 | 0.00 | 0.00 |
| LP + LightGBM forecast | 49.85 | 43.98 | 479.00 | 34.5% | 698.92 | 0.00 | 0.00 |
| Future-request oracle reference | 53.90 | 47.57 | 469.85 | 32.1% | 707.68 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +7.30 | [+6.15, +8.35] |
| Current-capacity guard | walkins | -19.20 | [-22.82, -15.50] |
| Current-capacity guard | weighted_score | +17.30 | [+13.62, +21.08] |
| Calibration-selected fixed buffer | fulfilled | -13.17 | [-15.90, -10.37] |
| Calibration-selected fixed buffer | walkins | +42.53 | [+35.82, +49.38] |
| Calibration-selected fixed buffer | weighted_score | -23.30 | [-30.92, -15.55] |
| LP + historical means | fulfilled | -0.42 | [-0.92, +0.12] |
| LP + historical means | walkins | +1.15 | [-1.22, +3.38] |
| LP + historical means | weighted_score | -0.93 | [-2.97, +1.13] |
| LP + adaptive means | fulfilled | +0.47 | [-0.05, +1.08] |
| LP + adaptive means | walkins | -2.22 | [-4.55, -0.08] |
| LP + adaptive means | weighted_score | +0.12 | [-2.17, +2.30] |
| LP + linear forecast | fulfilled | +1.43 | [+0.77, +2.12] |
| LP + linear forecast | walkins | -4.48 | [-7.08, -2.07] |
| LP + linear forecast | weighted_score | +2.68 | [+0.42, +5.03] |

### quiet

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 22.97 | 20.43 | 356.03 | 6.0% | 458.20 | 0.00 | 0.00 |
| Fixed +5 buffer | 25.03 | 22.13 | 347.63 | 0.0% | 458.30 | 0.00 | 0.00 |
| Fixed +10 buffer | 25.03 | 22.13 | 341.40 | 0.0% | 452.07 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 25.03 | 22.13 | 347.63 | 0.0% | 458.30 | 0.00 | 0.00 |
| Reactive adaptive buffer | 24.87 | 22.00 | 350.77 | 0.6% | 460.77 | 0.00 | 0.00 |
| LP + historical means | 24.53 | 21.73 | 352.20 | 1.4% | 460.87 | 0.00 | 0.00 |
| LP + adaptive means | 24.17 | 21.40 | 353.60 | 2.7% | 460.60 | 0.00 | 0.00 |
| LP + linear forecast | 24.10 | 21.37 | 353.27 | 3.0% | 460.10 | 0.00 | 0.00 |
| LP + LightGBM forecast | 24.13 | 21.37 | 353.77 | 2.9% | 460.60 | 0.00 | 0.00 |
| Future-request oracle reference | 24.00 | 21.23 | 354.60 | 3.2% | 460.77 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +0.93 | [+0.30, +1.73] |
| Current-capacity guard | walkins | -2.27 | [-3.80, -1.00] |
| Current-capacity guard | weighted_score | +2.40 | [+0.37, +5.10] |
| Calibration-selected fixed buffer | fulfilled | -0.77 | [-1.30, -0.33] |
| Calibration-selected fixed buffer | walkins | +6.13 | [+3.67, +8.90] |
| Calibration-selected fixed buffer | weighted_score | +2.30 | [+0.87, +3.80] |
| LP + historical means | fulfilled | -0.37 | [-0.60, -0.17] |
| LP + historical means | walkins | +1.57 | [+0.87, +2.27] |
| LP + historical means | weighted_score | -0.27 | [-1.20, +0.57] |
| LP + adaptive means | fulfilled | -0.03 | [-0.17, +0.10] |
| LP + adaptive means | walkins | +0.17 | [-0.23, +0.60] |
| LP + adaptive means | weighted_score | +0.00 | [-0.60, +0.60] |
| LP + linear forecast | fulfilled | +0.00 | [-0.17, +0.17] |
| LP + linear forecast | walkins | +0.50 | [-0.23, +1.33] |
| LP + linear forecast | weighted_score | +0.50 | [-0.27, +1.40] |

### unannounced

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 45.50 | 39.90 | 494.13 | 47.4% | 693.63 | 0.00 | 0.00 |
| Fixed +5 buffer | 70.07 | 62.40 | 431.10 | 24.1% | 743.10 | 0.00 | 0.00 |
| Fixed +10 buffer | 71.83 | 64.00 | 405.27 | 22.9% | 725.27 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 70.07 | 62.40 | 431.10 | 24.1% | 743.10 | 0.00 | 0.00 |
| Reactive adaptive buffer | 68.13 | 60.53 | 442.03 | 25.7% | 744.70 | 0.00 | 0.00 |
| LP + historical means | 54.87 | 48.70 | 473.50 | 35.7% | 717.00 | 0.00 | 0.00 |
| LP + adaptive means | 53.70 | 47.47 | 477.07 | 37.7% | 714.40 | 0.00 | 0.00 |
| LP + linear forecast | 52.70 | 46.47 | 478.93 | 39.1% | 711.27 | 0.00 | 0.00 |
| LP + LightGBM forecast | 53.70 | 47.57 | 475.37 | 37.7% | 713.20 | 0.00 | 0.00 |
| Future-request oracle reference | 58.80 | 52.30 | 462.90 | 35.1% | 724.40 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +7.67 | [+6.13, +9.37] |
| Current-capacity guard | walkins | -18.77 | [-25.33, -13.53] |
| Current-capacity guard | weighted_score | +19.57 | [+12.77, +26.43] |
| Calibration-selected fixed buffer | fulfilled | -14.83 | [-20.30, -10.33] |
| Calibration-selected fixed buffer | walkins | +44.27 | [+34.00, +56.70] |
| Calibration-selected fixed buffer | weighted_score | -29.90 | [-45.63, -16.37] |
| LP + historical means | fulfilled | -1.13 | [-1.83, -0.40] |
| LP + historical means | walkins | +1.87 | [-4.00, +5.90] |
| LP + historical means | weighted_score | -3.80 | [-8.83, +0.20] |
| LP + adaptive means | fulfilled | +0.10 | [-0.50, +0.73] |
| LP + adaptive means | walkins | -1.70 | [-7.03, +1.87] |
| LP + adaptive means | weighted_score | -1.20 | [-6.00, +2.77] |
| LP + linear forecast | fulfilled | +1.10 | [+0.40, +1.77] |
| LP + linear forecast | walkins | -3.57 | [-9.30, +0.47] |
| LP + linear forecast | weighted_score | +1.93 | [-3.63, +6.70] |

### shifted

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 43.67 | 38.47 | 498.90 | 48.0% | 691.23 | 0.00 | 0.00 |
| Fixed +5 buffer | 67.50 | 60.10 | 434.80 | 24.5% | 735.30 | 0.00 | 0.00 |
| Fixed +10 buffer | 69.43 | 61.77 | 410.43 | 23.1% | 719.27 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 67.50 | 60.10 | 434.80 | 24.5% | 735.30 | 0.00 | 0.00 |
| Reactive adaptive buffer | 66.00 | 58.87 | 445.87 | 25.9% | 740.20 | 0.00 | 0.00 |
| LP + historical means | 52.87 | 47.13 | 476.80 | 36.4% | 712.47 | 0.00 | 0.00 |
| LP + adaptive means | 51.97 | 46.17 | 481.00 | 38.3% | 711.83 | 0.00 | 0.00 |
| LP + linear forecast | 50.63 | 44.93 | 483.47 | 39.8% | 708.13 | 0.00 | 0.00 |
| LP + LightGBM forecast | 51.90 | 46.07 | 480.03 | 38.3% | 710.37 | 0.00 | 0.00 |
| Future-request oracle reference | 56.97 | 50.33 | 466.80 | 35.3% | 718.47 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +7.60 | [+6.00, +9.27] |
| Current-capacity guard | walkins | -18.87 | [-23.40, -14.67] |
| Current-capacity guard | weighted_score | +19.13 | [+13.00, +25.37] |
| Calibration-selected fixed buffer | fulfilled | -14.03 | [-18.53, -10.23] |
| Calibration-selected fixed buffer | walkins | +45.23 | [+35.57, +56.00] |
| Calibration-selected fixed buffer | weighted_score | -24.93 | [-38.27, -14.00] |
| LP + historical means | fulfilled | -1.07 | [-1.63, -0.50] |
| LP + historical means | walkins | +3.23 | [+0.60, +5.70] |
| LP + historical means | weighted_score | -2.10 | [-4.70, +0.37] |
| LP + adaptive means | fulfilled | -0.10 | [-0.60, +0.40] |
| LP + adaptive means | walkins | -0.97 | [-3.90, +1.57] |
| LP + adaptive means | weighted_score | -1.47 | [-4.60, +1.27] |
| LP + linear forecast | fulfilled | +1.13 | [+0.57, +1.70] |
| LP + linear forecast | walkins | -3.43 | [-6.43, -0.80] |
| LP + linear forecast | weighted_score | +2.23 | [-0.70, +5.03] |

### size_50

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 21.97 | 19.10 | 277.67 | 73.8% | 373.17 | 0.00 | 0.00 |
| Fixed +5 buffer | 57.10 | 50.07 | 188.33 | 31.6% | 438.67 | 0.00 | 0.00 |
| Fixed +10 buffer | 59.20 | 52.00 | 154.40 | 30.1% | 414.40 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 57.10 | 50.07 | 188.33 | 31.6% | 438.67 | 0.00 | 0.00 |
| Reactive adaptive buffer | 54.77 | 47.87 | 207.67 | 34.5% | 447.00 | 0.00 | 0.00 |
| LP + historical means | 33.70 | 29.57 | 253.47 | 56.7% | 401.30 | 0.00 | 0.00 |
| LP + adaptive means | 31.77 | 27.93 | 259.50 | 59.7% | 399.17 | 0.00 | 0.00 |
| LP + linear forecast | 32.60 | 28.40 | 256.00 | 59.8% | 398.00 | 0.00 | 0.00 |
| LP + LightGBM forecast | 32.30 | 28.23 | 257.87 | 59.5% | 399.03 | 0.00 | 0.00 |
| Future-request oracle reference | 32.30 | 28.10 | 258.70 | 61.4% | 399.20 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +9.13 | [+8.07, +10.20] |
| Current-capacity guard | walkins | -19.80 | [-22.73, -16.67] |
| Current-capacity guard | weighted_score | +25.87 | [+21.10, +30.70] |
| Calibration-selected fixed buffer | fulfilled | -21.83 | [-25.37, -18.63] |
| Calibration-selected fixed buffer | walkins | +69.53 | [+60.90, +78.90] |
| Calibration-selected fixed buffer | weighted_score | -39.63 | [-50.30, -29.97] |
| LP + historical means | fulfilled | -1.33 | [-2.27, -0.37] |
| LP + historical means | walkins | +4.40 | [+1.23, +7.43] |
| LP + historical means | weighted_score | -2.27 | [-5.07, +0.23] |
| LP + adaptive means | fulfilled | +0.30 | [-0.33, +0.97] |
| LP + adaptive means | walkins | -1.63 | [-3.80, +0.10] |
| LP + adaptive means | weighted_score | -0.13 | [-2.67, +2.13] |
| LP + linear forecast | fulfilled | -0.17 | [-1.23, +0.77] |
| LP + linear forecast | walkins | +1.87 | [-0.30, +4.40] |
| LP + linear forecast | weighted_score | +1.03 | [-2.60, +4.50] |

### size_150

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 58.53 | 51.53 | 642.40 | 32.2% | 900.07 | 0.00 | 0.00 |
| Fixed +5 buffer | 77.17 | 68.07 | 598.13 | 18.0% | 938.47 | 0.00 | 0.00 |
| Fixed +10 buffer | 78.80 | 69.57 | 582.03 | 16.9% | 929.87 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 77.17 | 68.07 | 598.13 | 18.0% | 938.47 | 0.00 | 0.00 |
| Reactive adaptive buffer | 73.97 | 65.23 | 602.73 | 20.0% | 928.90 | 0.00 | 0.00 |
| LP + historical means | 64.80 | 57.17 | 627.47 | 26.2% | 913.30 | 0.00 | 0.00 |
| LP + adaptive means | 64.37 | 56.77 | 628.90 | 26.7% | 912.73 | 0.00 | 0.00 |
| LP + linear forecast | 64.07 | 56.37 | 629.47 | 26.7% | 911.30 | 0.00 | 0.00 |
| LP + LightGBM forecast | 65.80 | 57.90 | 626.57 | 25.8% | 916.07 | 0.00 | 0.00 |
| Future-request oracle reference | 73.87 | 65.10 | 604.90 | 20.7% | 930.40 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +6.37 | [+4.67, +8.40] |
| Current-capacity guard | walkins | -15.83 | [-22.10, -10.90] |
| Current-capacity guard | weighted_score | +16.00 | [+11.50, +21.17] |
| Calibration-selected fixed buffer | fulfilled | -10.17 | [-14.03, -6.30] |
| Calibration-selected fixed buffer | walkins | +28.43 | [+19.27, +38.10] |
| Calibration-selected fixed buffer | weighted_score | -22.40 | [-32.97, -12.13] |
| LP + historical means | fulfilled | +0.73 | [-0.33, +2.00] |
| LP + historical means | walkins | -0.90 | [-3.73, +1.57] |
| LP + historical means | weighted_score | +2.77 | [-0.67, +7.03] |
| LP + adaptive means | fulfilled | +1.13 | [+0.10, +2.43] |
| LP + adaptive means | walkins | -2.33 | [-5.13, +0.07] |
| LP + adaptive means | weighted_score | +3.33 | [-0.10, +7.80] |
| LP + linear forecast | fulfilled | +1.53 | [+0.40, +2.93] |
| LP + linear forecast | walkins | -2.90 | [-6.03, -0.30] |
| LP + linear forecast | weighted_score | +4.77 | [+1.03, +9.03] |

### long_lead

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 41.13 | 35.97 | 496.37 | 50.2% | 676.20 | 0.00 | 0.00 |
| Fixed +5 buffer | 67.50 | 59.47 | 420.60 | 25.0% | 717.93 | 0.00 | 0.00 |
| Fixed +10 buffer | 69.63 | 61.43 | 394.03 | 23.4% | 701.20 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 67.50 | 59.47 | 420.60 | 25.0% | 717.93 | 0.00 | 0.00 |
| Reactive adaptive buffer | 65.13 | 57.20 | 435.47 | 26.8% | 721.47 | 0.00 | 0.00 |
| LP + historical means | 50.80 | 44.70 | 472.53 | 38.1% | 696.03 | 0.00 | 0.00 |
| LP + adaptive means | 49.97 | 43.87 | 476.07 | 39.8% | 695.40 | 0.00 | 0.00 |
| LP + linear forecast | 48.40 | 42.40 | 480.07 | 41.6% | 692.07 | 0.00 | 0.00 |
| LP + LightGBM forecast | 50.17 | 44.10 | 472.73 | 39.6% | 693.23 | 0.00 | 0.00 |
| Future-request oracle reference | 55.03 | 48.40 | 460.53 | 37.0% | 702.53 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +8.13 | [+6.70, +9.70] |
| Current-capacity guard | walkins | -23.63 | [-29.70, -18.37] |
| Current-capacity guard | weighted_score | +17.03 | [+11.87, +22.47] |
| Calibration-selected fixed buffer | fulfilled | -15.37 | [-19.90, -11.13] |
| Calibration-selected fixed buffer | walkins | +52.13 | [+41.40, +63.53] |
| Calibration-selected fixed buffer | weighted_score | -24.70 | [-37.03, -12.77] |
| LP + historical means | fulfilled | -0.60 | [-1.40, +0.23] |
| LP + historical means | walkins | +0.20 | [-3.67, +3.43] |
| LP + historical means | weighted_score | -2.80 | [-6.44, +0.57] |
| LP + adaptive means | fulfilled | +0.23 | [-0.60, +1.13] |
| LP + adaptive means | walkins | -3.33 | [-7.20, -0.23] |
| LP + adaptive means | weighted_score | -2.17 | [-6.40, +1.87] |
| LP + linear forecast | fulfilled | +1.70 | [+1.03, +2.50] |
| LP + linear forecast | walkins | -7.33 | [-11.60, -4.03] |
| LP + linear forecast | weighted_score | +1.17 | [-2.43, +4.50] |

### weight_1

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |
| Fixed +5 buffer | 67.87 | 59.63 | 439.17 | 24.7% | 498.80 | 0.00 | 0.00 |
| Fixed +10 buffer | 69.83 | 61.50 | 414.30 | 23.2% | 475.80 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |
| Reactive adaptive buffer | 65.70 | 57.57 | 452.00 | 26.5% | 509.57 | 0.00 | 0.00 |
| LP + historical means | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |
| LP + adaptive means | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |
| LP + linear forecast | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |
| LP + LightGBM forecast | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |
| Future-request oracle reference | 41.60 | 36.17 | 506.47 | 50.0% | 542.63 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +0.00 | [+0.00, +0.00] |
| Current-capacity guard | walkins | +0.00 | [+0.00, +0.00] |
| Current-capacity guard | weighted_score | +0.00 | [+0.00, +0.00] |
| Calibration-selected fixed buffer | fulfilled | +0.00 | [+0.00, +0.00] |
| Calibration-selected fixed buffer | walkins | +0.00 | [+0.00, +0.00] |
| Calibration-selected fixed buffer | weighted_score | +0.00 | [+0.00, +0.00] |
| LP + historical means | fulfilled | +0.00 | [+0.00, +0.00] |
| LP + historical means | walkins | +0.00 | [+0.00, +0.00] |
| LP + historical means | weighted_score | +0.00 | [+0.00, +0.00] |
| LP + adaptive means | fulfilled | +0.00 | [+0.00, +0.00] |
| LP + adaptive means | walkins | +0.00 | [+0.00, +0.00] |
| LP + adaptive means | weighted_score | +0.00 | [+0.00, +0.00] |
| LP + linear forecast | fulfilled | +0.00 | [+0.00, +0.00] |
| LP + linear forecast | walkins | +0.00 | [+0.00, +0.00] |
| LP + linear forecast | weighted_score | +0.00 | [+0.00, +0.00] |

### weight_10

| Policy | Accepted/day | Served/day | Walk-ins/day | Rejected | Score | Capacity failures | Claim violations |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current-capacity guard | 41.60 | 36.17 | 506.47 | 50.0% | 868.13 | 0.00 | 0.00 |
| Fixed +5 buffer | 67.87 | 59.63 | 439.17 | 24.7% | 1035.50 | 0.00 | 0.00 |
| Fixed +10 buffer | 69.83 | 61.50 | 414.30 | 23.2% | 1029.30 | 0.00 | 0.00 |
| Calibration-selected fixed buffer | 67.87 | 59.63 | 439.17 | 24.7% | 1035.50 | 0.00 | 0.00 |
| Reactive adaptive buffer | 65.70 | 57.57 | 452.00 | 26.5% | 1027.67 | 0.00 | 0.00 |
| LP + historical means | 51.67 | 45.23 | 484.17 | 37.6% | 936.50 | 0.00 | 0.00 |
| LP + adaptive means | 50.43 | 44.03 | 488.27 | 39.7% | 928.60 | 0.00 | 0.00 |
| LP + linear forecast | 49.00 | 42.77 | 491.27 | 41.2% | 918.93 | 0.00 | 0.00 |
| LP + LightGBM forecast | 50.90 | 44.53 | 485.97 | 39.3% | 931.30 | 0.00 | 0.00 |
| Future-request oracle reference | 55.90 | 49.10 | 473.53 | 36.3% | 964.53 | 0.00 | 0.00 |

| Comparator | Outcome | Mean delta | 95% interval |
| --- | --- | --- | --- |
| Current-capacity guard | fulfilled | +8.37 | [+6.93, +9.90] |
| Current-capacity guard | walkins | -20.50 | [-26.13, -15.67] |
| Current-capacity guard | weighted_score | +63.17 | [+51.27, +75.44] |
| Calibration-selected fixed buffer | fulfilled | -15.10 | [-19.27, -11.07] |
| Calibration-selected fixed buffer | walkins | +46.80 | [+37.13, +56.74] |
| Calibration-selected fixed buffer | weighted_score | -104.20 | [-136.88, -71.93] |
| LP + historical means | fulfilled | -0.70 | [-1.50, +0.20] |
| LP + historical means | walkins | +1.80 | [-1.60, +4.73] |
| LP + historical means | weighted_score | -5.20 | [-11.40, +1.80] |
| LP + adaptive means | fulfilled | +0.50 | [-0.30, +1.50] |
| LP + adaptive means | walkins | -2.30 | [-5.60, +0.37] |
| LP + adaptive means | weighted_score | +2.70 | [-4.47, +11.33] |
| LP + linear forecast | fulfilled | +1.77 | [+0.93, +2.77] |
| LP + linear forecast | walkins | -5.30 | [-9.13, -2.30] |
| LP + linear forecast | weighted_score | +12.37 | [+5.10, +20.53] |

## Safety and limits

All completed runs have zero capacity-denied valid accepted arrivals, physical capacity violations, claim violations and failed solves. This follows the common verified-state guard and must not be sold as proof of camera or network reliability. The earlier V2 undetected-count counterexample still applies.

The fixed buffer, request forecasts and artificial cue can alter the balance between member access and ordinary walk-in access. A positive preference-score difference is not Pareto superiority. Report counts and intervals, including costs to walk-ins. No visit-retention, willingness-to-pay, landlord-capture or financial-return claim follows.

## Reproduce

```powershell
python -B analysis/test_decision_value.py
python -B analysis/benchmark_decision_value.py
python -B analysis/report_decision_value.py
```

Environment: `{"python": "3.12.10", "numpy": "2.4.6", "scipy": "1.17.1", "lightgbm": "4.6.0"}`. Executed code SHA256: `90f36b3792cd2ed2d36411fb95bc961133c376bf108bb5424c4f290da3dcb35f`. Protocol SHA256: `501382d7b1e317417bcf45b36433e8da3a6182a7eabeb7241606d0988ee5055b`.

The protocol is recorded before evaluation. All settings and null/adverse findings are retained. [Structured results](results.json), [protocol](protocol.md), [earlier V2 report](../v2/report.md).

# Commitment-ledger + stay-risk admission: results

Synthetic, 100 bays. See protocol.md for calibration vs assumptions. Score = 5 x bookings honoured + walk-ins admitted. Breach = shown-up booking with no bay within 30 min. Knobs tuned on calibration days to breach <= 1%; test breach shown (flagged with ! if above 1%).

## L0

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 42.9 | 504.4 | 718.9 | 0.00% | 160.0 |  |
| P2_expected_H180 | 50.8 | 516.0 | 770.0 | 0.00% | 0.0 | z=0.0 |
| P4_fullinfo | 50.8 | 516.0 | 770.0 | 0.00% | 0.0 | z=0.0 |
| P1_quota | 50.8 | 493.7 | 747.7 | 0.00% | 171.5 | Q=25 margin=0 |
| P1b_buffer | 50.8 | 494.9 | 748.9 | 0.00% | 170.4 | Q=40 margin=5 |
| P3_H180 | 50.8 | 516.0 | 770.0 | 0.00% | 0.0 | z=0.0 |
| P3_H9999 | 50.8 | 516.0 | 770.0 | 0.00% | 0.0 | z=0.0 |

Simple comparator (better on calibration): **P1_quota**. Best commit policy on calibration: **P3_H180**.
Paired score difference, best commit minus simple: **+22.3/day** (95% CI +19.1 to +25.3). Fixed 3-hour commit minus simple: +22.3 (+19.1 to +25.3).

End-of-day horizon minus 3-hour horizon: +0.0/day (+0.0 to +0.0).

## L3 no class signal

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 92.8 | 128.5 | 592.5 | 0.00% | 535.3 |  |
| P2_expected_H180 | 116.6 | 307.8 | 890.8 | 4.58% ! | 219.0 | z=0.0 |
| P4_fullinfo | 127.8 | 299.3 | 938.3 | 0.00% | 275.2 | z=0.0 |
| P1_quota | 92.2 | 347.5 | 808.5 | 0.00% | 316.5 | Q=40 margin=0 |
| P1b_buffer | 92.2 | 363.3 | 824.3 | 0.00% | 282.9 | Q=40 margin=5 |
| P3_H180 | 114.0 | 306.6 | 876.6 | 3.14% ! | 234.5 | z=1.5 |
| P3_H9999 | 122.9 | 261.5 | 876.0 | 1.44% ! | 328.8 | z=0.0 |

Simple comparator (better on calibration): **P1b_buffer**. Best commit policy on calibration: **P3_H180**.
Paired score difference, best commit minus simple: **+52.3/day** (95% CI +44.3 to +61.2). Fixed 3-hour commit minus simple: +52.3 (+44.3 to +61.2).

End-of-day horizon minus 3-hour horizon: -0.6/day (-7.4 to +6.8).

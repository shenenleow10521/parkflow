# Commitment-ledger + stay-risk admission: results

Synthetic, 100 bays. See protocol.md for calibration vs assumptions. Score = 5 x bookings honoured + walk-ins admitted. Breach = shown-up booking with no bay within 30 min. Knobs tuned on calibration days to breach <= 1%; test breach shown (flagged with ! if above 1%).

## L0

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 45.3 | 502.2 | 728.8 | 0.00% | 158.7 |  |
| P2_expected_H180 | 53.7 | 512.6 | 781.0 | 0.00% | 0.3 | z=0.0 |
| P4_fullinfo | 53.7 | 512.5 | 780.9 | 0.00% | 0.3 | z=0.0 |
| P1_quota | 53.7 | 491.6 | 760.0 | 0.00% | 168.6 | Q=25 margin=0 |
| P1b_buffer | 53.7 | 512.5 | 780.9 | 0.00% | 0.0 | Q=25 margin=0 |
| P3_H60 | 53.7 | 512.5 | 780.9 | 0.00% | 1.5 | z=0.5 |
| P3_H120 | 53.7 | 512.5 | 780.9 | 0.00% | 1.5 | z=0.5 |
| P3_H180 | 53.7 | 512.5 | 780.9 | 0.00% | 1.5 | z=0.5 |
| P3_H300 | 53.7 | 512.5 | 780.9 | 0.00% | 1.5 | z=0.5 |
| P3_H9999 | 53.7 | 512.5 | 780.9 | 0.00% | 1.5 | z=0.5 |

Simple comparator (better on calibration): **P1b_buffer**. Best commit policy on calibration: **P3_H60**.
Paired score difference, best commit minus simple: **-0.0/day** (95% CI -0.2 to +0.1). Fixed 3-hour commit minus simple: -0.0 (-0.2 to +0.1).

End-of-day horizon minus 3-hour horizon: +0.0/day (+0.0 to +0.0).

## L1

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 46.7 | 481.2 | 714.8 | 0.00% | 180.3 |  |
| P2_expected_H180 | 53.7 | 512.6 | 781.0 | 0.00% | 0.3 | z=0.0 |
| P4_fullinfo | 53.7 | 512.5 | 780.9 | 0.00% | 0.3 | z=0.0 |
| P1_quota | 53.7 | 491.0 | 759.4 | 0.00% | 169.3 | Q=25 margin=0 |
| P1b_buffer | 53.7 | 512.5 | 780.9 | 0.00% | 0.0 | Q=25 margin=0 |
| P3_H60 | 53.7 | 512.5 | 780.9 | 0.00% | 1.6 | z=0.5 |
| P3_H120 | 53.7 | 512.5 | 780.9 | 0.00% | 1.6 | z=0.5 |
| P3_H180 | 53.7 | 512.5 | 780.9 | 0.00% | 1.6 | z=0.5 |
| P3_H300 | 53.7 | 512.5 | 780.9 | 0.00% | 1.6 | z=0.5 |
| P3_H9999 | 53.7 | 512.5 | 780.9 | 0.00% | 1.6 | z=0.5 |

Simple comparator (better on calibration): **P1b_buffer**. Best commit policy on calibration: **P3_H60**.
Paired score difference, best commit minus simple: **-0.0/day** (95% CI -0.1 to +0.1). Fixed 3-hour commit minus simple: -0.0 (-0.1 to +0.1).

End-of-day horizon minus 3-hour horizon: +0.0/day (+0.0 to +0.0).

## L2

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 93.1 | 143.7 | 609.2 | 0.00% | 514.5 |  |
| P2_expected_H180 | 120.2 | 359.8 | 960.7 | 2.36% ! | 213.8 | z=0.0 |
| P4_fullinfo | 127.3 | 359.5 | 995.8 | 0.01% | 241.7 | z=0.0 |
| P1_quota | 91.2 | 416.1 | 872.3 | 0.00% | 243.1 | Q=40 margin=0 |
| P1b_buffer | 91.2 | 459.3 | 915.4 | 0.02% | 0.0 | Q=40 margin=0 |
| P3_H60 | 108.6 | 410.7 | 953.6 | 5.33% ! | 176.9 | z=3.0 |
| P3_H120 | 113.0 | 382.8 | 947.7 | 1.64% ! | 228.9 | z=3.0 |
| P3_H180 | 118.7 | 358.8 | 952.0 | 1.33% ! | 224.2 | z=1.0 |
| P3_H300 | 124.1 | 306.0 | 926.7 | 0.34% | 312.3 | z=0.0 |
| P3_H9999 | 124.3 | 304.0 | 925.7 | 0.29% | 315.4 | z=0.0 |

Simple comparator (better on calibration): **P1b_buffer**. Best commit policy on calibration: **P3_H60**.
Paired score difference, best commit minus simple: **+38.2/day** (95% CI +35.3 to +41.3). Fixed 3-hour commit minus simple: +36.7 (+34.5 to +38.9).

End-of-day horizon minus 3-hour horizon: -26.3/day (-28.6 to -24.1).

## L3 no class signal

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 91.8 | 131.5 | 590.7 | 0.00% | 524.6 |  |
| P2_expected_H180 | 116.8 | 318.5 | 902.6 | 4.32% ! | 216.2 | z=0.0 |
| P4_fullinfo | 126.4 | 311.9 | 943.9 | 0.05% | 262.7 | z=0.0 |
| P1_quota | 90.9 | 360.4 | 814.7 | 0.02% | 295.7 | Q=40 margin=0 |
| P1b_buffer | 90.4 | 395.3 | 847.2 | 0.56% | 0.0 | Q=40 margin=0 |
| P3_H60 | 103.6 | 357.0 | 874.8 | 9.05% ! | 229.3 | z=3.0 |
| P3_H120 | 109.6 | 333.6 | 881.5 | 3.90% ! | 271.1 | z=3.0 |
| P3_H180 | 113.0 | 309.3 | 874.2 | 1.34% ! | 315.7 | z=3.0 |
| P3_H300 | 122.6 | 272.5 | 885.6 | 1.04% ! | 317.4 | z=0.0 |
| P3_H9999 | 122.9 | 269.6 | 884.1 | 0.95% | 323.6 | z=0.0 |

Simple comparator (better on calibration): **P1b_buffer**. Best commit policy on calibration: **P3_H120**.
Paired score difference, best commit minus simple: **+34.3/day** (95% CI +31.1 to +37.7). Fixed 3-hour commit minus simple: +27.0 (+24.0 to +30.1).

End-of-day horizon minus 3-hour horizon: +9.8/day (+7.6 to +12.0).

## L3 with class signal

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Walk-ins denied with a free bay/day | Chosen knob |
|---|---|---|---|---|---|---|
| P0_strict | 91.8 | 131.5 | 590.7 | 0.00% | 524.6 |  |
| P2_expected_H180 | 116.8 | 318.5 | 902.4 | 4.36% ! | 216.3 | z=0.0 |
| P4_fullinfo | 126.4 | 311.9 | 943.9 | 0.05% | 262.7 | z=0.0 |
| P1_quota | 90.9 | 360.4 | 814.7 | 0.02% | 295.7 | Q=40 margin=0 |
| P1b_buffer | 90.4 | 395.3 | 847.2 | 0.56% | 0.0 | Q=40 margin=0 |
| P3_H60 | 103.4 | 357.4 | 874.6 | 9.18% ! | 226.7 | z=3.0 |
| P3_H120 | 109.6 | 334.0 | 882.1 | 3.90% ! | 268.9 | z=3.0 |
| P3_H180 | 113.0 | 309.6 | 874.5 | 1.34% ! | 314.4 | z=3.0 |
| P3_H300 | 122.7 | 273.4 | 886.6 | 1.04% ! | 316.0 | z=0.0 |
| P3_H9999 | 122.9 | 270.7 | 885.5 | 0.97% | 321.8 | z=0.0 |

Simple comparator (better on calibration): **P1b_buffer**. Best commit policy on calibration: **P3_H120**.
Paired score difference, best commit minus simple: **+34.9/day** (95% CI +31.6 to +38.3). Fixed 3-hour commit minus simple: +27.3 (+24.2 to +30.4).

End-of-day horizon minus 3-hour horizon: +11.0/day (+8.8 to +13.2).

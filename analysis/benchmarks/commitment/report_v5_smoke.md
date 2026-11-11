# v5: design variants vs tuned rules (fresh seeds)

Synthetic; protocol_architecture.md Amendment v5. Selected on 150 calibration days (calibration failures <= half the target); test = 200 fresh days. `!` = test failure rate above the target. s2/s10/s25 = score minus 2/10/25 per failed booking (s2 ~ fallback + refund). Diffs are variant minus tuned quota rule, paired, 95% interval.

## rho = 0.5 (ML R^2 0.38); 30 configs searched

### Failure target 1.0%

| Policy | Honoured | Walk-ins | Test failures | Failures/day | Score | s2 | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|---|
| quota | 111.7 | 419.5 | 0.09% | 0.10 | 978.0 | 977.8 | 977.0 | 975.5 | Q=60 m=0 |
| buffer | 110.3 | 410.3 | 1.34% ! | 1.50 | 961.8 | 958.8 | 946.8 | 924.3 | Q=60 m=15 |
| V0_reference | 131.0 | 348.4 | 1.06% ! | 1.40 | 1003.4 | 1000.6 | 989.4 | 968.4 | H=300 z=0 zb=0 ps=0.9 |
| V1_hard_bookings | 126.1 | 305.8 | 0.00% | 0.00 | 936.3 | 936.3 | 936.3 | 936.3 | H=300 z=0 zb=0 ps=1.0 |
| V2_separate_risk | 131.0 | 348.4 | 1.06% ! | 1.40 | 1003.4 | 1000.6 | 989.4 | 968.4 | H=300 z=0 zb=0 ps=0.9 |
| V3_hybrid | 106.6 | 450.9 | 0.37% | 0.40 | 983.9 | 983.1 | 979.9 | 973.9 | H=480 z=0 zb=2 ps=0.9 Qcap=60 |

| Variant minus quota | Score | Failures/day | s2 | s10 |
|---|---|---|---|---|
| V0_reference | +25.4 [+13.5, +39.5] | +1.3 [+0.3, +2.7] | +22.8 [+9.5, +38.1] | +12.4 [-9.9, +33.7] |
| V1_hard_bookings | -41.7 [-57.8, -24.7] | -0.1 [-0.3, +0.0] | -41.5 [-57.8, -24.2] | -40.7 [-57.8, -21.9] |
| V2_separate_risk | +25.4 [+13.5, +39.5] | +1.3 [+0.3, +2.7] | +22.8 [+9.5, +38.1] | +12.4 [-9.9, +33.7] |
| V3_hybrid | +5.9 [-5.0, +16.2] | +0.3 [+0.0, +0.9] | +5.3 [-5.8, +15.8] | +2.9 [-10.2, +14.9] |

### Failure target 0.5%

| Policy | Honoured | Walk-ins | Test failures | Failures/day | Score | s2 | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|---|
| quota | 111.7 | 419.5 | 0.09% | 0.10 | 978.0 | 977.8 | 977.0 | 975.5 | Q=60 m=0 |
| buffer | 110.3 | 410.3 | 1.34% ! | 1.50 | 961.8 | 958.8 | 946.8 | 924.3 | Q=60 m=15 |
| V0_reference | 131.0 | 348.4 | 1.06% ! | 1.40 | 1003.4 | 1000.6 | 989.4 | 968.4 | H=300 z=0 zb=0 ps=0.9 |
| V1_hard_bookings | 126.1 | 305.8 | 0.00% | 0.00 | 936.3 | 936.3 | 936.3 | 936.3 | H=300 z=0 zb=0 ps=1.0 |
| V2_separate_risk | 131.0 | 348.4 | 1.06% ! | 1.40 | 1003.4 | 1000.6 | 989.4 | 968.4 | H=300 z=0 zb=0 ps=0.9 |
| V3_hybrid | 106.6 | 450.9 | 0.37% | 0.40 | 983.9 | 983.1 | 979.9 | 973.9 | H=480 z=0 zb=2 ps=0.9 Qcap=60 |

| Variant minus quota | Score | Failures/day | s2 | s10 |
|---|---|---|---|---|
| V0_reference | +25.4 [+13.5, +39.5] | +1.3 [+0.3, +2.7] | +22.8 [+9.5, +38.1] | +12.4 [-9.9, +33.7] |
| V1_hard_bookings | -41.7 [-57.8, -24.7] | -0.1 [-0.3, +0.0] | -41.5 [-57.8, -24.2] | -40.7 [-57.8, -21.9] |
| V2_separate_risk | +25.4 [+13.5, +39.5] | +1.3 [+0.3, +2.7] | +22.8 [+9.5, +38.1] | +12.4 [-9.9, +33.7] |
| V3_hybrid | +5.9 [-5.0, +16.2] | +0.3 [+0.0, +0.9] | +5.3 [-5.8, +15.8] | +2.9 [-10.2, +14.9] |

### Failure target 0.1%

| Policy | Honoured | Walk-ins | Test failures | Failures/day | Score | s2 | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|---|
| quota | 111.7 | 419.5 | 0.09% | 0.10 | 978.0 | 977.8 | 977.0 | 975.5 | Q=60 m=0 |
| buffer | 110.3 | 410.3 | 1.34% ! | 1.50 | 961.8 | 958.8 | 946.8 | 924.3 | Q=60 m=15 |
| V0_reference | 129.7 | 326.1 | 0.23% ! | 0.30 | 974.6 | 974.0 | 971.6 | 967.1 | H=480 z=1 zb=1 ps=0.9 |
| V1_hard_bookings | 126.1 | 305.8 | 0.00% | 0.00 | 936.3 | 936.3 | 936.3 | 936.3 | H=300 z=0 zb=0 ps=1.0 |
| V2_separate_risk | 125.3 | 365.7 | 0.40% ! | 0.50 | 992.2 | 991.2 | 987.2 | 979.7 | H=300 z=1 zb=2 ps=0.9 |
| V3_hybrid | 106.6 | 450.9 | 0.37% ! | 0.40 | 983.9 | 983.1 | 979.9 | 973.9 | H=480 z=0 zb=2 ps=0.9 Qcap=60 |

| Variant minus quota | Score | Failures/day | s2 | s10 |
|---|---|---|---|---|
| V0_reference | -3.4 [-22.1, +13.5] | +0.2 [-0.3, +0.9] | -3.8 [-22.2, +13.1] | -5.4 [-24.1, +12.9] |
| V1_hard_bookings | -41.7 [-57.8, -24.7] | -0.1 [-0.3, +0.0] | -41.5 [-57.8, -24.2] | -40.7 [-57.8, -21.9] |
| V2_separate_risk | +14.2 [-1.4, +28.4] | +0.4 [-0.3, +1.5] | +13.4 [-1.9, +28.2] | +10.2 [-8.0, +27.5] |
| V3_hybrid | +5.9 [-5.0, +16.2] | +0.3 [+0.0, +0.9] | +5.3 [-5.8, +15.8] | +2.9 [-10.2, +14.9] |

P0_strict: honoured 96.5, walk-ins 133.0, failures 0.00%, score 615.5  
Oracle: honoured 133.3, walk-ins 362.4, failures 0.07%, score 1028.9  
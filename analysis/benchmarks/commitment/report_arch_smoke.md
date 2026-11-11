# Architecture test v3: ML stay forecast in the commitment planner

Synthetic (stay marginal calibrated to Mueller et al. 2026; feature effects assumed). 100 bays, advance bookings 30%, evening pulse 100, stay shock sd 0.15. Knobs tuned on 150 calibration days to breach <= 1%; test = 200 fresh days. `!` = test breach above 1%. Score = W x bookings honoured + walk-ins.

## Summary by informativeness rho (share of log-stay variance explained by features)

| rho | ML out-of-sample R^2 | Pooled commit score | ML commit score | Best simple | Oracle | ML - simple (W=5) | ML - pooled (W=5) | ML - simple W=1 | ML - simple W=10 |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 0.00 | 904.0 | 905.7 | 902.9 (P1_quota) | 955.3 | +2.8 [-11.1, +15.7] | +1.7 [-1.7, +5.2] | -42.4 [-55.5, -32.3] | +59.3 [+35.6, +80.8] |
| 0.5 | 0.38 | 975.0 | 982.3 | 917.6 (P1b_buffer) | 988.0 | +64.7 [+49.0, +80.7] | +7.3 [+2.1, +13.3] | +6.3 [-3.9, +16.6] | +137.7 [+109.4, +165.1] |

## rho = 0.0  (ML R^2 0.00; residual sd 0.92 vs pooled sd 0.92)

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Chosen |
|---|---|---|---|---|---|
| P0_strict | 93.2 | 131.9 | 597.9 | 0.00% |  |
| P1_quota | 110.4 | 350.9 | 902.9 | 0.00% | Q=60 m=4 |
| P1b_buffer | 90.4 | 393.8 | 845.8 | 0.00% | Q=40 m=10 |
| C_pooled | 122.3 | 292.5 | 904.0 | 2.55% ! | H=300 z=0.0 |
| C_ml | 121.7 | 297.2 | 905.7 | 2.80% ! | H=300 z=0.0 |
| Oracle | 126.3 | 323.8 | 955.3 | 0.00% |  |

## rho = 0.5  (ML R^2 0.38; residual sd 0.72 vs pooled sd 0.90)

| Policy | Honoured/day | Walk-ins/day | Score | Test breach | Chosen |
|---|---|---|---|---|---|
| P0_strict | 94.9 | 127.5 | 602.0 | 0.00% |  |
| P1_quota | 110.2 | 380.3 | 931.3 | 0.18% | Q=60 m=4 |
| P1b_buffer | 107.5 | 380.1 | 917.6 | 2.63% ! | Q=60 m=15 |
| C_pooled | 121.3 | 368.5 | 975.0 | 3.19% ! | H=180 z=0.0 |
| C_ml | 122.1 | 371.8 | 982.3 | 4.24% ! | H=180 z=0.0 |
| Oracle | 128.9 | 343.5 | 988.0 | 0.08% |  |
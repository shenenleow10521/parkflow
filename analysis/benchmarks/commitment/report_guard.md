# v4: safety guard and horizon

Synthetic; see protocol_architecture.md (Amendment v4). Selection on 150 calibration days with calibration breach <= half the target; test = 200 fresh days. `!` = test breach above the target. s10/s25 = score minus 10 or 25 per failed booking. A failure counts as a failure; fallback to another level is not modelled.

## rho = 0.5 (ML R^2 0.38)

### Frontier from calibration days: best score at each failure ceiling

| Failure ceiling | quota | buffer | commit_nohold | commit_hold |
|---|---|---|---|---|
| <= 2.00% | 995 (111 bk / 440 wi, 0.10%) | 998 (109 bk / 453 wi, 1.99%) | 1036 (127 bk / 399 wi, 1.50%) | 1031 (128 bk / 392 wi, 1.35%) |
| <= 1.00% | 995 (111 bk / 440 wi, 0.10%) | 967 (110 bk / 415 wi, 0.71%) | 1025 (126 bk / 397 wi, 0.96%) | 1020 (126 bk / 391 wi, 0.89%) |
| <= 0.50% | 995 (111 bk / 440 wi, 0.10%) | 963 (92 bk / 504 wi, 0.40%) | 1018 (130 bk / 369 wi, 0.49%) | 1014 (130 bk / 365 wi, 0.45%) |
| <= 0.25% | 995 (111 bk / 440 wi, 0.10%) | 949 (92 bk / 488 wi, 0.17%) | 987 (128 bk / 347 wi, 0.16%) | 984 (128 bk / 344 wi, 0.18%) |
| <= 0.10% | 989 (111 bk / 434 wi, 0.07%) | 933 (92 bk / 472 wi, 0.04%) | 958 (126 bk / 330 wi, 0.06%) | 956 (126 bk / 327 wi, 0.08%) |
| <= 0.05% | 983 (111 bk / 427 wi, 0.05%) | 933 (92 bk / 472 wi, 0.04%) | none | none |

### Target 1.0% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 109.1 | 437.2 | 0.18% | 0.20 | 982.7 | 980.7 | 977.8 | Q=60 m=0 |
| buffer | 90.2 | 499.6 | 0.47% | 0.43 | 950.6 | 946.3 | 939.8 | Q=40 m=0 |
| commit_nohold | 127.7 | 365.1 | 0.75% | 0.96 | 1003.7 | 994.1 | 979.7 | H=300 z=0.0 no hold |
| commit_hold | 127.9 | 361.4 | 0.70% | 0.90 | 1001.1 | 992.1 | 978.6 | H=480 z=0.0 hold=60 swing=0 |

### Target 0.5% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 109.1 | 437.2 | 0.18% | 0.20 | 982.7 | 980.7 | 977.8 | Q=60 m=0 |
| buffer | 90.4 | 484.7 | 0.20% | 0.18 | 936.9 | 935.1 | 932.3 | Q=40 m=5 |
| commit_nohold | 126.0 | 345.8 | 0.27% | 0.34 | 975.6 | 972.2 | 967.0 | H=300 z=1.0 no hold |
| commit_hold | 126.1 | 342.3 | 0.30% | 0.39 | 972.8 | 969.0 | 963.2 | H=300 z=1.0 hold=60 swing=0 |

### Target 0.1% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 109.1 | 425.2 | 0.13% ! | 0.14 | 970.9 | 969.5 | 967.4 | Q=60 m=4 |
| buffer | 90.5 | 468.0 | 0.11% ! | 0.10 | 920.6 | 919.6 | 918.1 | Q=40 m=10 |
| commit_nohold | 124.0 | 323.5 | 0.09% | 0.12 | 943.6 | 942.5 | 940.8 | H=480 z=2.0 no hold (infeasible) |
| commit_hold | 124.1 | 318.4 | 0.10% | 0.12 | 939.0 | 937.8 | 936.0 | H=480 z=2.0 hold=60 swing=2 (infeasible) |

P0_strict: honoured 95.3, walk-ins 144.7, breach 0.00%, score 621.0

Oracle: honoured 130.6, walk-ins 410.3, breach 0.03%, score 1063.3
## rho = 0.0 (ML R^2 0.00)

### Frontier from calibration days: best score at each failure ceiling

| Failure ceiling | quota | buffer | commit_nohold | commit_hold |
|---|---|---|---|---|
| <= 2.00% | 955 (111 bk / 400 wi, 0.06%) | 978 (109 bk / 433 wi, 1.96%) | 971 (121 bk / 365 wi, 1.37%) | 972 (123 bk / 357 wi, 1.98%) |
| <= 1.00% | 955 (111 bk / 400 wi, 0.06%) | 942 (110 bk / 390 wi, 0.67%) | 960 (119 bk / 363 wi, 0.75%) | 953 (120 bk / 356 wi, 0.69%) |
| <= 0.50% | 955 (111 bk / 400 wi, 0.06%) | 936 (92 bk / 475 wi, 0.04%) | 948 (127 bk / 315 wi, 0.40%) | 944 (127 bk / 310 wi, 0.37%) |
| <= 0.25% | 955 (111 bk / 400 wi, 0.06%) | 936 (92 bk / 475 wi, 0.04%) | 926 (125 bk / 303 wi, 0.16%) | 922 (125 bk / 298 wi, 0.13%) |
| <= 0.10% | 955 (111 bk / 400 wi, 0.06%) | 936 (92 bk / 475 wi, 0.04%) | 907 (122 bk / 296 wi, 0.10%) | 904 (122 bk / 292 wi, 0.07%) |
| <= 0.05% | 948 (111 bk / 392 wi, 0.05%) | 936 (92 bk / 475 wi, 0.04%) | none | none |

### Target 1.0% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 109.1 | 393.6 | 0.18% | 0.20 | 939.0 | 937.0 | 934.0 | Q=60 m=0 |
| buffer | 90.5 | 467.0 | 0.18% | 0.17 | 919.3 | 917.7 | 915.2 | Q=40 m=0 |
| commit_nohold | 124.1 | 312.9 | 0.78% | 0.97 | 933.2 | 923.5 | 908.8 | H=300 z=0.0 no hold |
| commit_hold | 124.3 | 307.4 | 0.71% | 0.90 | 929.1 | 920.2 | 906.7 | H=300 z=0.0 hold=60 swing=0 |

### Target 0.5% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 109.1 | 393.6 | 0.18% | 0.20 | 939.0 | 937.0 | 934.0 | Q=60 m=0 |
| buffer | 90.5 | 467.0 | 0.18% | 0.17 | 919.3 | 917.7 | 915.2 | Q=40 m=0 |
| commit_nohold | 122.3 | 301.1 | 0.26% | 0.32 | 912.6 | 909.4 | 904.6 | H=300 z=1.0 no hold |
| commit_hold | 122.4 | 296.4 | 0.26% | 0.32 | 908.6 | 905.4 | 900.6 | H=300 z=1.0 hold=60 swing=0 |

### Target 0.1% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 109.1 | 386.1 | 0.16% ! | 0.18 | 931.6 | 929.8 | 927.1 | Q=60 m=2 |
| buffer | 90.5 | 467.0 | 0.18% ! | 0.17 | 919.3 | 917.7 | 915.2 | Q=40 m=0 |
| commit_nohold | 120.7 | 276.6 | 0.06% | 0.07 | 880.2 | 879.4 | 878.3 | H=480 z=2.0 no hold (infeasible) |
| commit_hold | 120.8 | 269.0 | 0.09% | 0.11 | 873.2 | 872.1 | 870.5 | H=480 z=2.0 hold=60 swing=2 (infeasible) |

P0_strict: honoured 93.6, walk-ins 143.9, breach 0.00%, score 611.7

Oracle: honoured 127.5, walk-ins 364.4, breach 0.04%, score 1001.9
# v4: safety guard and horizon

Synthetic; see protocol_architecture.md (Amendment v4). Selection on 150 calibration days with calibration breach <= half the target; test = 200 fresh days. `!` = test breach above the target. s10/s25 = score minus 10 or 25 per failed booking. A failure counts as a failure; fallback to another level is not modelled.

## rho = 0.5 (ML R^2 0.38)

### Frontier from calibration days: best score at each failure ceiling

| Failure ceiling | quota | buffer | commit_nohold | commit_hold |
|---|---|---|---|---|
| <= 2.00% | 989 (109 bk / 442 wi, 0.00%) | 856 (75 bk / 483 wi, 0.00%) | 1030 (128 bk / 392 wi, 0.26%) | 1025 (128 bk / 386 wi, 0.39%) |
| <= 1.00% | 989 (109 bk / 442 wi, 0.00%) | 856 (75 bk / 483 wi, 0.00%) | 1030 (128 bk / 392 wi, 0.26%) | 1025 (128 bk / 386 wi, 0.39%) |
| <= 0.50% | 989 (109 bk / 442 wi, 0.00%) | 856 (75 bk / 483 wi, 0.00%) | 1030 (128 bk / 392 wi, 0.26%) | 1025 (128 bk / 386 wi, 0.39%) |
| <= 0.25% | 989 (109 bk / 442 wi, 0.00%) | 856 (75 bk / 483 wi, 0.00%) | 996 (127 bk / 363 wi, 0.00%) | 1021 (129 bk / 378 wi, 0.00%) |
| <= 0.10% | 989 (109 bk / 442 wi, 0.00%) | 856 (75 bk / 483 wi, 0.00%) | 996 (127 bk / 363 wi, 0.00%) | 1021 (129 bk / 378 wi, 0.00%) |
| <= 0.05% | 989 (109 bk / 442 wi, 0.00%) | 856 (75 bk / 483 wi, 0.00%) | 996 (127 bk / 363 wi, 0.00%) | 1021 (129 bk / 378 wi, 0.00%) |

### Target 1.0% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 106.8 | 439.5 | 0.00% | 0.00 | 973.5 | 973.5 | 973.5 | Q=60 m=0 |
| buffer | 71.7 | 472.9 | 0.00% | 0.00 | 831.4 | 831.4 | 831.4 | Q=25 m=15 |
| commit_nohold | 123.0 | 399.3 | 1.76% ! | 2.20 | 1014.3 | 992.3 | 959.3 | H=180 z=0.0 no hold |
| commit_hold | 123.6 | 392.7 | 1.51% ! | 1.90 | 1010.7 | 991.7 | 963.2 | H=180 z=0.0 hold=60 swing=0 |

### Target 0.5% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 106.8 | 439.5 | 0.00% | 0.00 | 973.5 | 973.5 | 973.5 | Q=60 m=0 |
| buffer | 71.7 | 472.9 | 0.00% | 0.00 | 831.4 | 831.4 | 831.4 | Q=25 m=15 |
| commit_nohold | 124.1 | 346.4 | 0.00% | 0.00 | 966.9 | 966.9 | 966.9 | H=300 z=1.0 no hold |
| commit_hold | 125.9 | 360.7 | 0.24% | 0.30 | 990.2 | 987.2 | 982.7 | H=300 z=0.0 hold=60 swing=0 |

### Target 0.1% failures (test)

| Policy | Honoured | Walk-ins | Test breach | Failures/day | Score | s10 | s25 | Chosen |
|---|---|---|---|---|---|---|---|---|
| quota | 106.8 | 439.5 | 0.00% | 0.00 | 973.5 | 973.5 | 973.5 | Q=60 m=0 |
| buffer | 71.7 | 472.9 | 0.00% | 0.00 | 831.4 | 831.4 | 831.4 | Q=25 m=15 |
| commit_nohold | 124.1 | 346.4 | 0.00% | 0.00 | 966.9 | 966.9 | 966.9 | H=300 z=1.0 no hold |
| commit_hold | 125.9 | 360.7 | 0.24% ! | 0.30 | 990.2 | 987.2 | 982.7 | H=300 z=0.0 hold=60 swing=0 |

P0_strict: honoured 92.0, walk-ins 151.7, breach 0.00%, score 611.7

Oracle: honoured 127.9, walk-ins 422.1, breach 0.00%, score 1061.6
# Backtest Results — Batch 0001

Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.
Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).
Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.
Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).

## Per-expression gate + metrics table

| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| r1_e1_volspread_20d | ✓ | ✓ | ✗ | ✓ | 0.141 | 1.056 | 26.44 | 28.17 | -27.25% | -8.45% | +59.71% |
| r1_e2_volratio_20d | ✓ | ✓ | ✗ | ✗ | -0.273 | 1.451 | 23.85 | 24.00 | -34.61% | -9.78% | +57.35% |
| r1_e3_logvolratio_20d | ✓ | ✓ | ✗ | ✗ | -0.120 | 1.538 | 26.44 | 27.13 | -32.20% | -9.29% | +59.20% |
| r1_e4_volspread_10d | ✓ | ✓ | ✗ | ✗ | 0.317 | 0.690 | 46.15 | 27.65 | -25.22% | -11.75% | +55.81% |
| r1_e5_volspread_20d_z504 | ✓ | ✓ | ✗ | ✗ | -0.474 | 0.758 | 26.44 | 24.00 | -35.64% | -10.06% | +53.03% |
| r1_e6_downvolspread_20d | ✓ | ✓ | ✗ | ✗ | -0.246 | -0.271 | 23.59 | 25.04 | -34.81% | -17.14% | +58.27% |
| r1_e7_vol_accel_spread | ✓ | ✓ | ✗ | ✗ | -1.304 | -0.959 | 87.11 | 74.61 | -46.58% | -21.87% | +52.31% |
| r1_e8_volspread_longbaseline | ✓ | ✓ | ✗ | ✗ | -0.007 | 0.545 | 27.48 | 18.78 | -23.61% | -8.45% | +53.03% |

## G5 — Batch horizon consistency

- Declared primary horizon: **5d**
- Surviving (G1-G4 pass) expressions: 0
- Peak |IC| horizons across survivors: []
- N at declared horizon: 0 (need ≥ 4)
- G5 result: **FAIL** → escalate to Agent 2 (revise horizon)

## Per-expression detail

### r1_e1_volspread_20d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5971223021582733, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 26.444444444444443, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1064522461030704, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.140841092753568, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.06423831104563389, "t_stat": 1.9300647766864307, "n": 901}, "ic_sign_match_thesis": "True", "quintile_means": [-0.001667366640982685, 0.0009703039967493067, -0.0012515002187261587, 0.00016661185108764342, 0.003519569541799511], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.019553333613793203, "t_stat": 0.5876892189163695, "n": 905}, "5": {"horizon": 5, "ic": 0.06423831104563389, "t_stat": 1.9300647766864307, "n": 901}, "10": {"horizon": 10, "ic": 0.06284884149108398, "t_stat": 1.8828922205363101, "n": 896}, "20": {"horizon": 20, "ic": 0.011460483119441563, "t_stat": 0.34076703922402585, "n": 886}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": -0.02817064522508583, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0159
    - ann_vol: 0.1126
    - sharpe: 0.1408
    - max_dd: -0.2725
    - calmar: 0.0582
    - ann_turnover: 26.4444
    - non_zero_frac: 0.5971
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0969
    - ann_vol: 0.0918
    - sharpe: 1.0561
    - max_dd: -0.0845
    - calmar: 1.1474
    - ann_turnover: 28.1739
    - non_zero_frac: 0.5227
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e2_volratio_20d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5734840698869476, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 23.85185185185185, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1188229833946324, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.27250998909015395, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.0072836260875101255, "t_stat": 0.21839314820504732, "n": 901}, "ic_sign_match_thesis": "True", "quintile_means": [-0.0008660608494426684, 0.0005560416694516568, -0.0010079528542640567, 0.0036699710063138246, -0.0006188321409730277], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.011995020271196819, "t_stat": -0.36047579384184547, "n": 905}, "5": {"horizon": 5, "ic": 0.0072836260875101255, "t_stat": 0.21839314820504732, "n": 901}, "10": {"horizon": 10, "ic": 0.0114584379771654, "t_stat": 0.34262787292397534, "n": 896}, "20": {"horizon": 20, "ic": 0.008309424773547958, "t_stat": 0.2470654895243201, "n": 886}}, "peak_horizon": 1, "horizon_match_declared": false, "corr_with_mom20": -0.08921892658684666, "classic_clone_check_pass": t...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0304
    - ann_vol: 0.1116
    - sharpe: -0.2725
    - max_dd: -0.3461
    - calmar: -0.0879
    - ann_turnover: 23.8519
    - non_zero_frac: 0.5735
- VAL metrics:
    - n_days: 483
    - ann_return: 0.1379
    - ann_vol: 0.0950
    - sharpe: 1.4511
    - max_dd: -0.0978
    - calmar: 1.4104
    - ann_turnover: 24.0000
    - non_zero_frac: 0.5455
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e3_logvolratio_20d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.591983556012333, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 26.444444444444443, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1246123625090294, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.11954147788445008, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.017113611984195636, "t_stat": 0.5131982105355236, "n": 901}, "ic_sign_match_thesis": "True", "quintile_means": [-0.0007815222365907085, -0.0002527295555490848, -0.000292884935044812, 0.0016247319149549572, 0.001435101984355088], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.00392374739529139, "t_stat": -0.11790935366847871, "n": 905}, "5": {"horizon": 5, "ic": 0.017113611984195636, "t_stat": 0.5131982105355236, "n": 901}, "10": {"horizon": 10, "ic": 0.01839169845870512, "t_stat": 0.5500017365403398, "n": 896}, "20": {"horizon": 20, "ic": -0.0012730713024600411, "t_stat": -0.037851161678119354, "n": 886}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": -0.06818865940789376, "classic_clone_check_pass": tr...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0132
    - ann_vol: 0.1107
    - sharpe: -0.1195
    - max_dd: -0.3220
    - calmar: -0.0411
    - ann_turnover: 26.4444
    - non_zero_frac: 0.5920
- VAL metrics:
    - n_days: 483
    - ann_return: 0.1498
    - ann_vol: 0.0974
    - sharpe: 1.5381
    - max_dd: -0.0929
    - calmar: 1.6125
    - ann_turnover: 27.1304
    - non_zero_frac: 0.5434
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e4_volspread_10d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5580678314491264, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 46.148148148148145, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.030176280752434, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.31689333595227887, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.06946445215408625, "t_stat": 2.0878187797175274, "n": 901}, "ic_sign_match_thesis": "True", "quintile_means": [-0.004810263303815611, 0.003029128454164515, 0.0016842510439552675, 0.0015767313458394537, 0.00027523152679973087], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.041863582898595535, "t_stat": 1.259102734799016, "n": 905}, "5": {"horizon": 5, "ic": 0.06946445215408625, "t_stat": 2.0878187797175274, "n": 901}, "10": {"horizon": 10, "ic": 0.05802828282726182, "t_stat": 1.7379645281906286, "n": 896}, "20": {"horizon": 20, "ic": 0.005404154456079357, "t_stat": 0.16067940965940936, "n": 886}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": -0.004888628338743925, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0355
    - ann_vol: 0.1121
    - sharpe: 0.3169
    - max_dd: -0.2522
    - calmar: 0.1409
    - ann_turnover: 46.1481
    - non_zero_frac: 0.5581
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0645
    - ann_vol: 0.0936
    - sharpe: 0.6896
    - max_dd: -0.1175
    - calmar: 0.5493
    - ann_turnover: 27.6522
    - non_zero_frac: 0.4421
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e5_volspread_20d_z504

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5303186022610483, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 26.444444444444443, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.0827997106508105, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.4735847298138188, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.005367480576448195, "t_stat": 0.15519576867796084, "n": 838}, "ic_sign_match_thesis": "True", "quintile_means": [-2.051067123597689e-05, -0.0007298380880990613, -8.12453097216666e-05, -0.001183417368119316, 0.0012035020527944394], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.010416224025354805, "t_stat": -0.30190723181612067, "n": 842}, "5": {"horizon": 5, "ic": 0.005367480576448195, "t_stat": 0.15519576867796084, "n": 838}, "10": {"horizon": 10, "ic": -0.008749039516121769, "t_stat": -0.2522188332252674, "n": 833}, "20": {"horizon": 20, "ic": -0.0760055417061192, "t_stat": -2.1841119746016715, "n": 823}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": -0.066580553217062, "classic_clone_check_pass": tr...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0520
    - ann_vol: 0.1098
    - sharpe: -0.4736
    - max_dd: -0.3564
    - calmar: -0.1459
    - ann_turnover: 26.4444
    - non_zero_frac: 0.5303
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0558
    - ann_vol: 0.0735
    - sharpe: 0.7582
    - max_dd: -0.1006
    - calmar: 0.5545
    - ann_turnover: 24.0000
    - non_zero_frac: 0.3802
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e6_downvolspread_20d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5827338129496403, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 23.592592592592595, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.0543618564810873, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.24600751771487867, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.008850703894125775, "t_stat": 0.2653839587183318, "n": 901}, "ic_sign_match_thesis": "True", "quintile_means": [-0.0016588876828768527, 0.002181271104751022, 0.0012866193351808689, 0.0010155652576639795, -0.0010869965901142105], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.003637315902906917, "t_stat": -0.109301914617807, "n": 905}, "5": {"horizon": 5, "ic": 0.008850703894125775, "t_stat": 0.2653839587183318, "n": 901}, "10": {"horizon": 10, "ic": -0.011635111854162144, "t_stat": -0.3479114489603997, "n": 896}, "20": {"horizon": 20, "ic": -0.08929491209035795, "t_stat": -2.665576970102668, "n": 886}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": -0.32002495464029307, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0275
    - ann_vol: 0.1120
    - sharpe: -0.2460
    - max_dd: -0.3481
    - calmar: -0.0791
    - ann_turnover: 23.5926
    - non_zero_frac: 0.5827
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0261
    - ann_vol: 0.0963
    - sharpe: -0.2708
    - max_dd: -0.1714
    - calmar: -0.1521
    - ann_turnover: 25.0435
    - non_zero_frac: 0.4793
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e7_vol_accel_spread

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5231243576567317, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 87.1111111111111, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9742730779861206, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.304354904449428, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.05952055033585866, "t_stat": 1.7877938398924726, "n": 901}, "ic_sign_match_thesis": "True", "quintile_means": [-0.005898623734010323, 0.003784330155034448, 0.003674251579724039, 0.0021567890604721382, -0.0019556215474425312], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.05075652861451856, "t_stat": -1.527200047776157, "n": 905}, "5": {"horizon": 5, "ic": 0.05952055033585866, "t_stat": 1.7877938398924726, "n": 901}, "10": {"horizon": 10, "ic": 0.022030469866795372, "t_stat": 0.6588672722354715, "n": 896}, "20": {"horizon": 20, "ic": -0.0053472174396017634, "t_stat": -0.15898647707325989, "n": 886}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": 0.04943229158781634, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.1438
    - ann_vol: 0.1102
    - sharpe: -1.3044
    - max_dd: -0.4658
    - calmar: -0.3086
    - ann_turnover: 87.1111
    - non_zero_frac: 0.5231
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0933
    - ann_vol: 0.0974
    - sharpe: -0.9587
    - max_dd: -0.2187
    - calmar: -0.4268
    - ann_turnover: 74.6087
    - non_zero_frac: 0.4587
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r1_e8_volspread_longbaseline

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5303186022610483, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 27.48148148148148, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.095606055498029, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.006652959118133765, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.037174145507851, "t_stat": 1.078154313027772, "n": 842}, "ic_sign_match_thesis": "True", "quintile_means": [-0.0018618066169756758, 2.839712828726452e-07, 0.0001061563512232728, -0.000674731859337784, 0.0015838727612194727], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.009823663724359697, "t_stat": 0.2854076880874055, "n": 846}, "5": {"horizon": 5, "ic": 0.037174145507851, "t_stat": 1.078154313027772, "n": 842}, "10": {"horizon": 10, "ic": 0.03979147830819204, "t_stat": 1.150740523069043, "n": 837}, "20": {"horizon": 20, "ic": -0.006335277357191887, "t_stat": -0.18197064010763167, "n": 827}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.006352777059437821, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0007
    - ann_vol: 0.1069
    - sharpe: -0.0067
    - max_dd: -0.2361
    - calmar: -0.0030
    - ann_turnover: 27.4815
    - non_zero_frac: 0.5303
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0441
    - ann_vol: 0.0809
    - sharpe: 0.5455
    - max_dd: -0.0845
    - calmar: 0.5224
    - ann_turnover: 18.7826
    - non_zero_frac: 0.4649
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}


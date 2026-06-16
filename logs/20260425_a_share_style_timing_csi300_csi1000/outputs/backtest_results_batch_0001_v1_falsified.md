# Backtest Results — Batch 0001

Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.
Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).
Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.
Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).

## Per-expression gate + metrics table

| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| r1_e1_volspread_20d | ✓ | ✓ | ✗ | ✗ | -0.612 | -1.685 | 26.44 | 28.17 | -33.67% | -27.72% | +59.71% |
| r1_e2_volratio_20d | ✓ | ✓ | ✗ | ✗ | -0.155 | -1.962 | 23.85 | 24.00 | -22.99% | -33.11% | +57.35% |
| r1_e3_logvolratio_20d | ✓ | ✓ | ✗ | ✗ | -0.359 | -2.105 | 26.44 | 27.13 | -24.44% | -35.42% | +59.20% |
| r1_e4_volspread_10d | ✓ | ✓ | ✗ | ✗ | -1.141 | -1.290 | 46.15 | 27.65 | -41.07% | -26.40% | +55.81% |
| r1_e5_volspread_20d_z504 | ✓ | ✓ | ✗ | ✗ | -0.008 | -1.407 | 26.44 | 24.00 | -23.78% | -19.18% | +53.03% |
| r1_e6_downvolspread_20d | ✓ | ✓ | ✗ | ✗ | -0.176 | -0.251 | 23.59 | 25.04 | -31.18% | -14.89% | +58.27% |
| r1_e7_vol_accel_spread | ✓ | ✓ | ✗ | ✗ | -0.278 | -0.572 | 87.11 | 74.61 | -28.18% | -19.37% | +52.31% |
| r1_e8_volspread_longbaseline | ✓ | ✓ | ✗ | ✗ | -0.508 | -1.010 | 27.48 | 18.78 | -28.66% | -22.57% | +53.03% |

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
        - detail: `{"non_zero_frac": {"observed": 0.5971223021582733, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 26.444444444444443, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1064522461030704, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.6122021404022056, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.06423831104563389, "t_stat": -1.9300647766864307, "n": 901}, "ic_sign_match_thesis": "False", "quintile_means": [0.0035113155273673296, 0.00015632865427112804, -0.0011249207544632039, 0.0010429353492546324, -0.0018768107029931023], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.019553333613793203, "t_stat": -0.5876892189163695, "n": 905}, "5": {"horizon": 5, "ic": -0.06423831104563389, "t_stat": -1.9300647766864307, "n": 901}, "10": {"horizon": 10, "ic": -0.06284884149108398, "t_stat": -1.8828922205363101, "n": 896}, "20": {"horizon": 20, "ic": -0.011460483119441563, "t_stat": -0.34076703922402585, "n": 886}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": 0.02817064522508583, "classic_clone_check_pass": ...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0687
    - ann_vol: 0.1123
    - sharpe: -0.6122
    - max_dd: -0.3367
    - calmar: -0.2042
    - ann_turnover: 26.4444
    - non_zero_frac: 0.5971
- VAL metrics:
    - n_days: 483
    - ann_return: -0.1533
    - ann_vol: 0.0909
    - sharpe: -1.6852
    - max_dd: -0.2772
    - calmar: -0.5530
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
        - detail: `{"non_zero_frac": {"observed": 0.5734840698869476, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 23.85185185185185, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1188229833946324, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.15506864082971175, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.0072836260875101255, "t_stat": -0.21839314820504732, "n": 901}, "ic_sign_match_thesis": "False", "quintile_means": [-0.000541998049019169, 0.003701495949456592, -0.0011953841664085615, 0.0005341343696610292, -0.000766881621495404], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.011995020271196819, "t_stat": 0.36047579384184547, "n": 905}, "5": {"horizon": 5, "ic": -0.0072836260875101255, "t_stat": -0.21839314820504732, "n": 901}, "10": {"horizon": 10, "ic": -0.0114584379771654, "t_stat": -0.34262787292397534, "n": 896}, "20": {"horizon": 20, "ic": -0.008309424773547958, "t_stat": -0.2470654895243201, "n": 886}}, "peak_horizon": 1, "horizon_match_declared": false, "corr_with_mom20": 0.08921892658684666, "classic_clone_check_pass"...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0173
    - ann_vol: 0.1115
    - sharpe: -0.1551
    - max_dd: -0.2299
    - calmar: -0.0752
    - ann_turnover: 23.8519
    - non_zero_frac: 0.5735
- VAL metrics:
    - n_days: 483
    - ann_return: -0.1859
    - ann_vol: 0.0948
    - sharpe: -1.9617
    - max_dd: -0.3311
    - calmar: -0.5616
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
        - detail: `{"non_zero_frac": {"observed": 0.591983556012333, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 26.444444444444443, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1246123625090294, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.35946687306811886, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.017113611984195636, "t_stat": -0.5131982105355236, "n": 901}, "ic_sign_match_thesis": "False", "quintile_means": [0.001597940376080458, 0.0012994030623572326, -4.691689938126754e-05, -0.0003640669821726413, -0.000766881621495404], "monotonic_inversions": 4, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.00392374739529139, "t_stat": 0.11790935366847871, "n": 905}, "5": {"horizon": 5, "ic": -0.017113611984195636, "t_stat": -0.5131982105355236, "n": 901}, "10": {"horizon": 10, "ic": -0.01839169845870512, "t_stat": -0.5500017365403398, "n": 896}, "20": {"horizon": 20, "ic": 0.0012730713024600411, "t_stat": 0.037851161678119354, "n": 886}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.06818865940789376, "classic_clone_check_pass": ...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0397
    - ann_vol: 0.1103
    - sharpe: -0.3595
    - max_dd: -0.2444
    - calmar: -0.1622
    - ann_turnover: 26.4444
    - non_zero_frac: 0.5920
- VAL metrics:
    - n_days: 483
    - ann_return: -0.2041
    - ann_vol: 0.0969
    - sharpe: -2.1053
    - max_dd: -0.3542
    - calmar: -0.5761
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
        - detail: `{"non_zero_frac": {"observed": 0.5580678314491264, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 46.148148148148145, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.030176280752434, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.1409476933571836, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.06946445215408625, "t_stat": -2.0878187797175274, "n": 901}, "ic_sign_match_thesis": "False", "quintile_means": [0.00033336581571739464, 0.0015342131305730816, 0.0016227030686605513, 0.0030110381011996313, -0.004774816766538042], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.041863582898595535, "t_stat": -1.259102734799016, "n": 905}, "5": {"horizon": 5, "ic": -0.06946445215408625, "t_stat": -2.0878187797175274, "n": 901}, "10": {"horizon": 10, "ic": -0.05802828282726182, "t_stat": -1.7379645281906286, "n": 896}, "20": {"horizon": 20, "ic": -0.005404154456079357, "t_stat": -0.16067940965940936, "n": 886}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": 0.004888628338743925, "classic_clone_check_pass": tr...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.1278
    - ann_vol: 0.1120
    - sharpe: -1.1409
    - max_dd: -0.4107
    - calmar: -0.3112
    - ann_turnover: 46.1481
    - non_zero_frac: 0.5581
- VAL metrics:
    - n_days: 483
    - ann_return: -0.1198
    - ann_vol: 0.0929
    - sharpe: -1.2903
    - max_dd: -0.2640
    - calmar: -0.4539
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
        - detail: `{"non_zero_frac": {"observed": 0.5303186022610483, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 26.444444444444443, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.0827997106508105, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.008172377367590862, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.005367480576448195, "t_stat": -0.15519576867796084, "n": 838}, "ic_sign_match_thesis": "False", "quintile_means": [0.0012035020527944394, -0.001183417368119316, -8.12453097216666e-05, -0.0007298380880990613, -2.051067123597689e-05], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.010416224025354805, "t_stat": 0.30190723181612067, "n": 842}, "5": {"horizon": 5, "ic": -0.005367480576448195, "t_stat": -0.15519576867796084, "n": 838}, "10": {"horizon": 10, "ic": 0.008749039516121769, "t_stat": 0.2522188332252674, "n": 833}, "20": {"horizon": 20, "ic": 0.0760055417061192, "t_stat": 2.1841119746016715, "n": 823}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.066580553217062, "classic_clone_check_pass": true...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0009
    - ann_vol: 0.1096
    - sharpe: -0.0082
    - max_dd: -0.2378
    - calmar: -0.0038
    - ann_turnover: 26.4444
    - non_zero_frac: 0.5303
- VAL metrics:
    - n_days: 483
    - ann_return: -0.1038
    - ann_vol: 0.0738
    - sharpe: -1.4066
    - max_dd: -0.1918
    - calmar: -0.5411
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
        - detail: `{"non_zero_frac": {"observed": 0.5827338129496403, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 23.592592592592595, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.0543618564810873, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.17563844849937202, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.008850703894125775, "t_stat": -0.2653839587183318, "n": 901}, "ic_sign_match_thesis": "False", "quintile_means": [-0.001030245641291261, 0.0009111129780764492, 0.0012289152725535786, 0.002247210896625239, -0.0016229145371457854], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.003637315902906917, "t_stat": 0.109301914617807, "n": 905}, "5": {"horizon": 5, "ic": -0.008850703894125775, "t_stat": -0.2653839587183318, "n": 901}, "10": {"horizon": 10, "ic": 0.011635111854162144, "t_stat": 0.3479114489603997, "n": 896}, "20": {"horizon": 20, "ic": 0.08929491209035795, "t_stat": 2.665576970102668, "n": 886}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.32002495464029307, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0196
    - ann_vol: 0.1118
    - sharpe: -0.1756
    - max_dd: -0.3118
    - calmar: -0.0630
    - ann_turnover: 23.5926
    - non_zero_frac: 0.5827
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0240
    - ann_vol: 0.0958
    - sharpe: -0.2508
    - max_dd: -0.1489
    - calmar: -0.1613
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
        - detail: `{"non_zero_frac": {"observed": 0.5231243576567317, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 87.1111111111111, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9742730779861206, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.27788048165468177, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.05952055033585866, "t_stat": -1.7877938398924726, "n": 901}, "ic_sign_match_thesis": "False", "quintile_means": [-0.0020634041034179426, 0.002134360062012956, 0.003913024716144623, 0.0036891577764309176, -0.0059333197131182965], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.05075652861451856, "t_stat": 1.527200047776157, "n": 905}, "5": {"horizon": 5, "ic": -0.05952055033585866, "t_stat": -1.7877938398924726, "n": 901}, "10": {"horizon": 10, "ic": -0.022030469866795372, "t_stat": -0.6588672722354715, "n": 896}, "20": {"horizon": 20, "ic": 0.0053472174396017634, "t_stat": 0.15898647707325989, "n": 886}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": -0.04943229158781634, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0305
    - ann_vol: 0.1096
    - sharpe: -0.2779
    - max_dd: -0.2818
    - calmar: -0.1081
    - ann_turnover: 87.1111
    - non_zero_frac: 0.5231
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0559
    - ann_vol: 0.0977
    - sharpe: -0.5722
    - max_dd: -0.1937
    - calmar: -0.2886
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
        - detail: `{"non_zero_frac": {"observed": 0.5303186022610483, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 27.48148148148148, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.095606055498029, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.5083952359415904, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.037174145507851, "t_stat": -1.078154313027772, "n": 842}, "ic_sign_match_thesis": "False", "quintile_means": [0.0015838727612194727, -0.000674731859337784, 0.0001061563512232728, 2.839712828726452e-07, -0.0018618066169756758], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.009823663724359697, "t_stat": -0.2854076880874055, "n": 846}, "5": {"horizon": 5, "ic": -0.037174145507851, "t_stat": -1.078154313027772, "n": 842}, "10": {"horizon": 10, "ic": -0.03979147830819204, "t_stat": -1.150740523069043, "n": 837}, "20": {"horizon": 20, "ic": 0.006335277357191887, "t_stat": 0.18197064010763167, "n": 827}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": -0.006352777059437821, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0543
    - ann_vol: 0.1067
    - sharpe: -0.5084
    - max_dd: -0.2866
    - calmar: -0.1893
    - ann_turnover: 27.4815
    - non_zero_frac: 0.5303
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0817
    - ann_vol: 0.0809
    - sharpe: -1.0099
    - max_dd: -0.2257
    - calmar: -0.3619
    - ann_turnover: 18.7826
    - non_zero_frac: 0.4649
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}


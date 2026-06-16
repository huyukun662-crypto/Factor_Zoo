# Backtest Results — Batch 0001

Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.
Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).
Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.
Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).

## Per-expression gate + metrics table

| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| r4_e1_e4_x_volgate_tanh_t1 | ✓ | ✓ | ✗ | ✗ | -1.170 | -0.544 | 24.89 | 27.13 | -32.28% | -16.77% | +31.55% |
| r4_e2_e4_x_volgate_tanh_t2 | ✓ | ✓ | ✗ | ✗ | -1.718 | -0.834 | 15.56 | 17.74 | -35.71% | -10.74% | +20.66% |
| r4_e3_e4_x_turnoverlevel_tanh | ✓ | ✓ | ✗ | ✗ | -0.111 | 0.065 | 14.78 | 19.83 | -26.14% | -9.49% | +29.29% |
| r4_e4_e4_x_volgate_oneside | ✓ | ✓ | ✗ | ✗ | -0.262 | 0.573 | 11.93 | 5.22 | -7.58% | -6.68% | +13.67% |
| r4_e5_e4_x_composite_regime | ✓ | ✓ | ✗ | ✗ | -1.044 | 0.155 | 18.15 | 18.78 | -28.88% | -10.05% | +23.33% |
| r4_e6_e2_x_volgate_tanh_t1 | ✓ | ✓ | ✗ | ✗ | -1.394 | 0.427 | 24.37 | 25.04 | -40.46% | -6.11% | +33.71% |
| r4_e7_e4_monthly_rebalance | ✓ | ✓ | ✓ | ✗ | 1.245 | -0.009 | 6.22 | 6.78 | -14.45% | -16.15% | +55.50% |
| r4_e8_e4_x_market_60d_gate | ✓ | ✓ | ✓ | ✗ | -0.082 | 0.052 | 15.04 | 25.04 | -20.60% | -12.52% | +36.07% |

## G5 — Batch horizon consistency

- Declared primary horizon: **20d**
- Surviving (G1-G4 pass) expressions: 0
- Peak |IC| horizons across survivors: []
- N at declared horizon: 0 (need ≥ 4)
- G5 result: **FAIL** → escalate to Agent 2 (revise horizon)

## Per-expression detail

### r4_e1_e4_x_volgate_tanh_t1

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.31551901336073995, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 24.888888888888886, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.6986804334387602, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.16998479221232, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": -0.20576232530571503, "t_stat": -6.130123514034698, "n": 852}, "ic_sign_match_thesis": "False", "quintile_means": [0.018060901131844737, -0.006617540066513451, 0.0028078804830079934, -0.00773792458968203, -0.009548771671580195], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.10251952369838077, "t_stat": -3.0381612394081516, "n": 871}, "5": {"horizon": 5, "ic": -0.1342507633352889, "t_stat": -3.9845035555807304, "n": 867}, "10": {"horizon": 10, "ic": -0.13254116794910792, "t_stat": -3.921467169960277, "n": 862}, "20": {"horizon": 20, "ic": -0.20576232530571503, "t_stat": -6.130123514034698, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.0374429162975516, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0959
    - ann_vol: 0.0819
    - sharpe: -1.1700
    - max_dd: -0.3228
    - calmar: -0.2970
    - ann_turnover: 24.8889
    - non_zero_frac: 0.3155
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0364
    - ann_vol: 0.0669
    - sharpe: -0.5444
    - max_dd: -0.1677
    - calmar: -0.2173
    - ann_turnover: 27.1304
    - non_zero_frac: 0.3202
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e2_e4_x_volgate_tanh_t2

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.2065775950668037, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 15.555555555555555, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.4596798334439319, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.7184365430445305, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": -0.2167865685616394, "t_stat": -6.4743260532553855, "n": 852}, "ic_sign_match_thesis": "False", "quintile_means": [0.01696598102769648, -0.004985842490969181, 0.0025979283258531364, -0.008858778859149102, -0.008752983118992157], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.10182160949495697, "t_stat": -3.0172611578146507, "n": 871}, "5": {"horizon": 5, "ic": -0.13028192981521233, "t_stat": -3.8646449218218635, "n": 867}, "10": {"horizon": 10, "ic": -0.1321645182041468, "t_stat": -3.910124911812301, "n": 862}, "20": {"horizon": 20, "ic": -0.2167865685616394, "t_stat": -6.4743260532553855, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.05575793431029153, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.1106
    - ann_vol: 0.0644
    - sharpe: -1.7184
    - max_dd: -0.3571
    - calmar: -0.3098
    - ann_turnover: 15.5556
    - non_zero_frac: 0.2066
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0403
    - ann_vol: 0.0483
    - sharpe: -0.8342
    - max_dd: -0.1074
    - calmar: -0.3752
    - ann_turnover: 17.7391
    - non_zero_frac: 0.1612
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e3_e4_x_turnoverlevel_tanh

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.29290853031860226, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 14.777777777777777, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.5192026907748987, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.11139274339125728, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": -0.05602031970664885, "t_stat": -1.6358278034937828, "n": 852}, "ic_sign_match_thesis": "False", "quintile_means": [0.014885028397494506, -0.018171126092078403, -0.004144154015476903, 0.0009895666086856265, 0.0033480483456119797], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.017556715501907523, "t_stat": -0.5176307922849673, "n": 871}, "5": {"horizon": 5, "ic": -0.019158538591462406, "t_stat": -0.5635729634225679, "n": 867}, "10": {"horizon": 10, "ic": -0.01784079105856188, "t_stat": -0.523277980788386, "n": 862}, "20": {"horizon": 20, "ic": -0.05602031970664885, "t_stat": -1.6358278034937828, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.2558231958567141, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0094
    - ann_vol: 0.0847
    - sharpe: -0.1114
    - max_dd: -0.2614
    - calmar: -0.0361
    - ann_turnover: 14.7778
    - non_zero_frac: 0.2929
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0043
    - ann_vol: 0.0665
    - sharpe: 0.0650
    - max_dd: -0.0949
    - calmar: 0.0456
    - ann_turnover: 19.8261
    - non_zero_frac: 0.3140
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e4_e4_x_volgate_oneside

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.1366906474820144, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 11.925925925925926, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.429640725790483, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.2622709111833245, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.04379179650583195, "t_stat": 1.2779652728277162, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [-0.0063513992781050535, -0.0005941975571656109, 0.0009512895317925895, 0.0045501007252256725], "monotonic_inversions": 0, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.024820980001904223, "t_stat": -0.7319183481126302, "n": 871}, "5": {"horizon": 5, "ic": 0.007790889643046099, "t_stat": 0.22914389300237947, "n": 867}, "10": {"horizon": 10, "ic": 0.05343632647677602, "t_stat": 1.569302831230908, "n": 862}, "20": {"horizon": 20, "ic": 0.04379179650583195, "t_stat": 1.2779652728277162, "n": 852}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.4207138209716456, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0133
    - ann_vol: 0.0507
    - sharpe: -0.2623
    - max_dd: -0.0758
    - calmar: -0.1754
    - ann_turnover: 11.9259
    - non_zero_frac: 0.1367
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0248
    - ann_vol: 0.0433
    - sharpe: 0.5735
    - max_dd: -0.0668
    - calmar: 0.3717
    - ann_turnover: 5.2174
    - non_zero_frac: 0.1219
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e5_e4_x_composite_regime

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.23329907502569372, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 18.14814814814815, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.46111682999292214, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.0444439756035024, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": -0.19039297617678566, "t_stat": -5.654289935509399, "n": 852}, "ic_sign_match_thesis": "False", "quintile_means": [0.013874821871275103, -0.003918146426097121, -0.0011706120844766463, 0.0014687023391261678, -0.013243860599874778], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.08227147832380312, "t_stat": -2.433514666854587, "n": 871}, "5": {"horizon": 5, "ic": -0.10949695075895725, "t_stat": -3.239882925007094, "n": 867}, "10": {"horizon": 10, "ic": -0.11311749066800195, "t_stat": -3.3386849507927687, "n": 862}, "20": {"horizon": 20, "ic": -0.19039297617678566, "t_stat": -5.654289935509399, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.15673385503772688, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0778
    - ann_vol: 0.0745
    - sharpe: -1.0444
    - max_dd: -0.2888
    - calmar: -0.2694
    - ann_turnover: 18.1481
    - non_zero_frac: 0.2333
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0088
    - ann_vol: 0.0571
    - sharpe: 0.1548
    - max_dd: -0.1005
    - calmar: 0.0880
    - ann_turnover: 18.7826
    - non_zero_frac: 0.2376
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e6_e2_x_volgate_tanh_t1

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.3371017471736896, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 24.37037037037037, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.6875177283515197, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.3937521409482723, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": -0.16222705863345407, "t_stat": -4.849246538802475, "n": 872}, "ic_sign_match_thesis": "False", "quintile_means": [0.013685809644863016, 0.005797901288028457, -0.0002918409373579433, -0.0003355987573792521, -0.014657809188487173], "monotonic_inversions": 4, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.09967042542847074, "t_stat": -2.986655709578903, "n": 891}, "5": {"horizon": 5, "ic": -0.11707233000288678, "t_stat": -3.5068943821078324, "n": 887}, "10": {"horizon": 10, "ic": -0.09932760468027042, "t_stat": -2.9611765783857478, "n": 882}, "20": {"horizon": 20, "ic": -0.16222705863345407, "t_stat": -4.849246538802475, "n": 872}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.08668115346516109, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.1253
    - ann_vol: 0.0899
    - sharpe: -1.3938
    - max_dd: -0.4046
    - calmar: -0.3097
    - ann_turnover: 24.3704
    - non_zero_frac: 0.3371
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0308
    - ann_vol: 0.0722
    - sharpe: 0.4267
    - max_dd: -0.0611
    - calmar: 0.5037
    - ann_turnover: 25.0435
    - non_zero_frac: 0.3306
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e7_e4_monthly_rebalance

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.5549845837615622, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 6.222222222222221, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.1053426752913513, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 1.2450455376215095, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.24556616412723478, "t_stat": 7.302558726649925, "n": 833}, "ic_sign_match_thesis": "True", "quintile_means": [-0.009757862136388568, -0.01748607129470492, -0.004589379890426072, -0.005182463780369654, 0.03594634125605821], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.10114126915291426, "t_stat": 2.963948282458389, "n": 852}, "5": {"horizon": 5, "ic": 0.17330187875472725, "t_stat": 5.118115637960583, "n": 848}, "10": {"horizon": 10, "ic": 0.21235938989497152, "t_stat": 6.302164378814932, "n": 843}, "20": {"horizon": 20, "ic": 0.24556616412723478, "t_stat": 7.302558726649925, "n": 833}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.48137942969864905, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.1408
    - ann_vol: 0.1131
    - sharpe: 1.2450
    - max_dd: -0.1445
    - calmar: 0.9738
    - ann_turnover: 6.2222
    - non_zero_frac: 0.5550
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0008
    - ann_vol: 0.0890
    - sharpe: -0.0087
    - max_dd: -0.1615
    - calmar: -0.0048
    - ann_turnover: 6.7826
    - non_zero_frac: 0.5434
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r4_e8_e4_x_market_60d_gate

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.3607399794450154, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 15.037037037037036, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.7430721075623241, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.08171012728297107, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.018583272810718122, "t_stat": 0.5418844237690966, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [0.003602791047788531, 0.002300909896623644, -0.009990305619125955, -0.0045818045643828, 0.0056287228529941155], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.03475986725278481, "t_stat": 1.025298976574533, "n": 871}, "5": {"horizon": 5, "ic": 0.07462373222656626, "t_stat": 2.200886403017512, "n": 867}, "10": {"horizon": 10, "ic": 0.09882637185595734, "t_stat": 2.912415296062047, "n": 862}, "20": {"horizon": 20, "ic": 0.018583272810718122, "t_stat": 0.5418844237690966, "n": 852}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.2334214842502427, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0076
    - ann_vol: 0.0934
    - sharpe: -0.0817
    - max_dd: -0.2060
    - calmar: -0.0370
    - ann_turnover: 15.0370
    - non_zero_frac: 0.3607
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0038
    - ann_vol: 0.0734
    - sharpe: 0.0523
    - max_dd: -0.1252
    - calmar: 0.0306
    - ann_turnover: 25.0435
    - non_zero_frac: 0.3512
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}


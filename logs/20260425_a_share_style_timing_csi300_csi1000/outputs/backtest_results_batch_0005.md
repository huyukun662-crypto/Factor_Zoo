# Backtest Results — Batch 0001

Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.
Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).
Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.
Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).

## Per-expression gate + metrics table

| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| r5_e1_e4_x_neg_volgate_tanh_t1 | ✓ | ✓ | ✗ | ✓ | 0.561 | -0.268 | 24.89 | 27.13 | -18.01% | -8.67% | +31.55% |
| r5_e2_e4_x_neg_volgate_tanh_t2 | ✓ | ✓ | ✗ | ✗ | 1.239 | 0.102 | 15.56 | 17.74 | -6.41% | -4.35% | +20.66% |
| r5_e3_e4_x_neg_turnoverlevel_tanh | ✓ | ✓ | ✗ | ✗ | -0.239 | -0.664 | 14.78 | 19.83 | -24.74% | -12.34% | +29.29% |
| r5_e4_e4_x_neg_volgate_oneside | ✓ | ✓ | ✗ | ✓ | 0.876 | 0.348 | 12.96 | 21.91 | -12.33% | -2.77% | +17.88% |
| r5_e5_e4_x_neg_composite | ✓ | ✓ | ✗ | ✗ | 0.555 | -0.819 | 18.15 | 18.78 | -12.09% | -9.14% | +23.33% |
| r5_e6_e2_x_neg_volgate_tanh_t1 | ✓ | ✓ | ✗ | ✓ | 0.849 | -1.133 | 24.37 | 25.04 | -13.97% | -16.61% | +33.71% |
| r5_e7_e4_x_neg_market_60d_gate | ✓ | ✓ | ✓ | ✗ | -0.239 | -0.743 | 15.04 | 25.04 | -27.88% | -16.39% | +36.07% |
| r5_e8_e4_x_neg_volgate_monthly | ✓ | ✓ | ✗ | ✓ | 0.946 | 1.584 | 5.70 | 7.30 | -7.92% | -5.35% | +26.72% |

## G5 — Batch horizon consistency

- Declared primary horizon: **20d**
- Surviving (G1-G4 pass) expressions: 0
- Peak |IC| horizons across survivors: []
- N at declared horizon: 0 (need ≥ 4)
- G5 result: **FAIL** → escalate to Agent 2 (revise horizon)

## Per-expression detail

### r5_e1_e4_x_neg_volgate_tanh_t1

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.31551901336073995, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 24.888888888888886, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.6986804334387602, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.5608436714223607, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.20576232530571503, "t_stat": 6.130123514034698, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [-0.009548771671580195, -0.00773792458968203, 0.0028078804830079934, -0.006617540066513451, 0.018060901131844737], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.10251952369838077, "t_stat": 3.0381612394081516, "n": 871}, "5": {"horizon": 5, "ic": 0.1342507633352889, "t_stat": 3.9845035555807304, "n": 867}, "10": {"horizon": 10, "ic": 0.13254116794910792, "t_stat": 3.921467169960277, "n": 862}, "20": {"horizon": 20, "ic": 0.20576232530571503, "t_stat": 6.130123514034698, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": -0.0374429162975516, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0461
    - ann_vol: 0.0822
    - sharpe: 0.5608
    - max_dd: -0.1801
    - calmar: 0.2560
    - ann_turnover: 24.8889
    - non_zero_frac: 0.3155
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0178
    - ann_vol: 0.0665
    - sharpe: -0.2680
    - max_dd: -0.0867
    - calmar: -0.2056
    - ann_turnover: 27.1304
    - non_zero_frac: 0.3202
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e2_e4_x_neg_volgate_tanh_t2

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.2065775950668037, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 15.555555555555555, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.4596798334439319, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 1.2392056487366867, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.2167865685616394, "t_stat": 6.4743260532553855, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [-0.008752983118992157, -0.008858778859149102, 0.0025979283258531364, -0.004985842490969181, 0.01696598102769648], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.10182160949495697, "t_stat": 3.0172611578146507, "n": 871}, "5": {"horizon": 5, "ic": 0.13028192981521233, "t_stat": 3.8646449218218635, "n": 867}, "10": {"horizon": 10, "ic": 0.1321645182041468, "t_stat": 3.910124911812301, "n": 862}, "20": {"horizon": 20, "ic": 0.2167865685616394, "t_stat": 6.4743260532553855, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": -0.05575793431029153, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0795
    - ann_vol: 0.0641
    - sharpe: 1.2392
    - max_dd: -0.0641
    - calmar: 1.2393
    - ann_turnover: 15.5556
    - non_zero_frac: 0.2066
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0048
    - ann_vol: 0.0471
    - sharpe: 0.1019
    - max_dd: -0.0435
    - calmar: 0.1103
    - ann_turnover: 17.7391
    - non_zero_frac: 0.1612
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e3_e4_x_neg_turnoverlevel_tanh

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.29290853031860226, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 14.777777777777777, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.5192026907748987, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.23867593103767204, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.05602031970664885, "t_stat": 1.6358278034937828, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [0.0033480483456119797, 0.0009895666086856265, -0.004144154015476903, -0.018171126092078403, 0.014885028397494506], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.017556715501907523, "t_stat": 0.5176307922849673, "n": 871}, "5": {"horizon": 5, "ic": 0.019158538591462406, "t_stat": 0.5635729634225679, "n": 867}, "10": {"horizon": 10, "ic": 0.01784079105856188, "t_stat": 0.523277980788386, "n": 862}, "20": {"horizon": 20, "ic": 0.05602031970664885, "t_stat": 1.6358278034937828, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": -0.2558231958567141, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0201
    - ann_vol: 0.0843
    - sharpe: -0.2387
    - max_dd: -0.2474
    - calmar: -0.0813
    - ann_turnover: 14.7778
    - non_zero_frac: 0.2929
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0440
    - ann_vol: 0.0662
    - sharpe: -0.6640
    - max_dd: -0.1234
    - calmar: -0.3564
    - ann_turnover: 19.8261
    - non_zero_frac: 0.3140
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e4_e4_x_neg_volgate_oneside

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.17882836587872558, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 12.962962962962964, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.5509987844709336, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.8757840269776145, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.29458445981029524, "t_stat": 8.987348644259397, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [-0.02321409372821295, -0.0003945018748136261, 0.004776299642306383, 0.01894318764642624], "monotonic_inversions": 0, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.11063239422359326, "t_stat": 3.2814544317894994, "n": 871}, "5": {"horizon": 5, "ic": 0.1762029457844044, "t_stat": 5.264655645115052, "n": 867}, "10": {"horizon": 10, "ic": 0.20952455086643906, "t_stat": 6.283948352910899, "n": 862}, "20": {"horizon": 20, "ic": 0.29458445981029524, "t_stat": 8.987348644259397, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.28057259428040826, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0566
    - ann_vol: 0.0647
    - sharpe: 0.8758
    - max_dd: -0.1233
    - calmar: 0.4595
    - ann_turnover: 12.9630
    - non_zero_frac: 0.1788
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0174
    - ann_vol: 0.0502
    - sharpe: 0.3479
    - max_dd: -0.0277
    - calmar: 0.6295
    - ann_turnover: 21.9130
    - non_zero_frac: 0.1983
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e5_e4_x_neg_composite

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.23329907502569372, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 18.14814814814815, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.46111682999292214, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.5551807815851638, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.19039297617678566, "t_stat": 5.654289935509399, "n": 852}, "ic_sign_match_thesis": "True", "quintile_means": [-0.013243860599874778, 0.0014687023391261678, -0.0011706120844766463, -0.003918146426097121, 0.013874821871275103], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.08227147832380312, "t_stat": 2.433514666854587, "n": 871}, "5": {"horizon": 5, "ic": 0.10949695075895725, "t_stat": 3.239882925007094, "n": 867}, "10": {"horizon": 10, "ic": 0.11311749066800195, "t_stat": 3.3386849507927687, "n": 862}, "20": {"horizon": 20, "ic": 0.19039297617678566, "t_stat": 5.654289935509399, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": -0.15673385503772688, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0415
    - ann_vol: 0.0747
    - sharpe: 0.5552
    - max_dd: -0.1209
    - calmar: 0.3430
    - ann_turnover: 18.1481
    - non_zero_frac: 0.2333
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0464
    - ann_vol: 0.0566
    - sharpe: -0.8192
    - max_dd: -0.0914
    - calmar: -0.5075
    - ann_turnover: 18.7826
    - non_zero_frac: 0.2376
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e6_e2_x_neg_volgate_tanh_t1

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.3371017471736896, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 24.37037037037037, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.6875177283515197, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.8493814253514256, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.16222705863345407, "t_stat": 4.849246538802475, "n": 872}, "ic_sign_match_thesis": "True", "quintile_means": [-0.014657809188487173, -0.0003355987573792521, -0.0002918409373579433, 0.005797901288028457, 0.013685809644863016], "monotonic_inversions": 0, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.09967042542847074, "t_stat": 2.986655709578903, "n": 891}, "5": {"horizon": 5, "ic": 0.11707233000288678, "t_stat": 3.5068943821078324, "n": 887}, "10": {"horizon": 10, "ic": 0.09932760468027042, "t_stat": 2.9611765783857478, "n": 882}, "20": {"horizon": 20, "ic": 0.16222705863345407, "t_stat": 4.849246538802475, "n": 872}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": -0.08668115346516109, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0766
    - ann_vol: 0.0902
    - sharpe: 0.8494
    - max_dd: -0.1397
    - calmar: 0.5483
    - ann_turnover: 24.3704
    - non_zero_frac: 0.3371
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0809
    - ann_vol: 0.0714
    - sharpe: -1.1331
    - max_dd: -0.1661
    - calmar: -0.4869
    - ann_turnover: 25.0435
    - non_zero_frac: 0.3306
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e7_e4_x_neg_market_60d_gate

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.3607399794450154, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 15.037037037037036, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.7430721075623241, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.23925640314087956, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 20, "ic": -0.018583272810718122, "t_stat": -0.5418844237690966, "n": 852}, "ic_sign_match_thesis": "False", "quintile_means": [0.0056287228529941155, -0.0045818045643828, -0.009990305619125955, 0.002300909896623644, 0.003602791047788531], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.03475986725278481, "t_stat": -1.025298976574533, "n": 871}, "5": {"horizon": 5, "ic": -0.07462373222656626, "t_stat": -2.200886403017512, "n": 867}, "10": {"horizon": 10, "ic": -0.09882637185595734, "t_stat": -2.912415296062047, "n": 862}, "20": {"horizon": 20, "ic": -0.018583272810718122, "t_stat": -0.5418844237690966, "n": 852}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": -0.2334214842502427, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0224
    - ann_vol: 0.0938
    - sharpe: -0.2393
    - max_dd: -0.2788
    - calmar: -0.0805
    - ann_turnover: 15.0370
    - non_zero_frac: 0.3607
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0539
    - ann_vol: 0.0726
    - sharpe: -0.7427
    - max_dd: -0.1639
    - calmar: -0.3289
    - ann_turnover: 25.0435
    - non_zero_frac: 0.3512
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r5_e8_e4_x_neg_volgate_monthly

- thesis_sign=1, declared_horizon=20d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.2672147995889003, "threshold": 0.3, "pass": false}, "ann_turnover": {"observed": 5.703703703703704, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 0.6261475550572042, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.9457857156911774, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 20, "ic": 0.30859575572765274, "t_stat": 9.352370133134048, "n": 833}, "ic_sign_match_thesis": "True", "quintile_means": [-0.018273823244891508, -0.009719857932610128, 0.015162471997074814, -0.01443754896982924, 0.024570377542704764], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.08484147724844096, "t_stat": 2.482483551602786, "n": 852}, "5": {"horizon": 5, "ic": 0.19453235511695285, "t_stat": 5.768382059906864, "n": 848}, "10": {"horizon": 10, "ic": 0.25947965966872155, "t_stat": 7.79179005893016, "n": 843}, "20": {"horizon": 20, "ic": 0.30859575572765274, "t_stat": 9.352370133134048, "n": 833}}, "peak_horizon": 20, "horizon_match_declared": true, "corr_with_mom20": 0.20539619893410482, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0770
    - ann_vol: 0.0814
    - sharpe: 0.9458
    - max_dd: -0.0792
    - calmar: 0.9722
    - ann_turnover: 5.7037
    - non_zero_frac: 0.2672
- VAL metrics:
    - n_days: 483
    - ann_return: 0.1130
    - ann_vol: 0.0713
    - sharpe: 1.5843
    - max_dd: -0.0535
    - calmar: 2.1101
    - ann_turnover: 7.3043
    - non_zero_frac: 0.3719
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}


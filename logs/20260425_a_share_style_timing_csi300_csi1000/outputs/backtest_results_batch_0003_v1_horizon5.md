# Backtest Results — Batch 0001

Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.
Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).
Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.
Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).

## Per-expression gate + metrics table

| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| r3_e1_amt_accel_5_20_neg | ✓ | ✓ | ✗ | ✗ | 0.502 | 0.918 | 35.52 | 30.78 | -24.13% | -8.75% | +54.57% |
| r3_e2_amt_accel_5_60_neg | ✓ | ✓ | ✓ | ✗ | 1.024 | 0.320 | 19.70 | 23.48 | -24.23% | -14.98% | +61.77% |
| r3_e3_amt_accel_10_60_neg | ✓ | ✓ | ✓ | ✗ | 1.165 | -0.256 | 14.00 | 17.22 | -12.56% | -20.83% | +63.62% |
| r3_e4_amt_accel_5_120_neg | ✓ | ✓ | ✓ | ✗ | 1.132 | 0.438 | 14.26 | 19.30 | -11.44% | -11.58% | +56.12% |
| r3_e5_amt_accel_spread_5_20_neg | ✓ | ✓ | ✗ | ✗ | -0.612 | -0.126 | 40.70 | 33.91 | -40.51% | -13.31% | +56.63% |
| r3_e6_amt_accel_spread_5_60_neg | ✓ | ✓ | ✗ | ✗ | -0.225 | -0.338 | 28.00 | 30.78 | -37.63% | -20.93% | +60.23% |
| r3_e7_vol_accel_spread_5_60_neg | ✓ | ✓ | ✗ | ✗ | -0.765 | -0.027 | 29.30 | 31.83 | -44.36% | -14.58% | +60.53% |
| r3_e8_accel_high_vol_regime | ✓ | ✓ | ✗ | ✗ | -0.246 | 0.197 | 20.74 | 16.17 | -15.81% | -8.34% | +31.24% |

## G5 — Batch horizon consistency

- Declared primary horizon: **5d**
- Surviving (G1-G4 pass) expressions: 0
- Peak |IC| horizons across survivors: []
- N at declared horizon: 0 (need ≥ 4)
- G5 result: **FAIL** → escalate to Agent 2 (revise horizon)

## Per-expression detail

### r3_e1_amt_accel_5_20_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5457348406988695, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 35.51851851851852, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9976050714024666, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.5024291787042039, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.13615020858826513, "t_stat": 4.122897834644619, "n": 902}, "ic_sign_match_thesis": "True", "quintile_means": [-0.006209163959536618, -4.8158509186994417e-05, 0.0018121865764405387, 0.004015958048397931, 0.002174072346403187], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.06036186975027801, "t_stat": 1.818191118460978, "n": 906}, "5": {"horizon": 5, "ic": 0.13615020858826513, "t_stat": 4.122897834644619, "n": 902}, "10": {"horizon": 10, "ic": 0.1772734705017363, "t_stat": 5.38875991692374, "n": 897}, "20": {"horizon": 20, "ic": 0.2008982839804933, "t_stat": 6.100897361842201, "n": 887}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.27040806482382573, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0571
    - ann_vol: 0.1136
    - sharpe: 0.5024
    - max_dd: -0.2413
    - calmar: 0.2365
    - ann_turnover: 35.5185
    - non_zero_frac: 0.5457
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0899
    - ann_vol: 0.0980
    - sharpe: 0.9182
    - max_dd: -0.0875
    - calmar: 1.0277
    - ann_turnover: 30.7826
    - non_zero_frac: 0.5579
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e2_amt_accel_5_60_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.6176772867420349, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 19.703703703703706, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.0632407875743868, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 1.0241765923020008, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.19551600999402133, "t_stat": 5.930858464815456, "n": 887}, "ic_sign_match_thesis": "True", "quintile_means": [-0.010998434971312986, 0.002413081769358366, 0.005589116271899573, 0.0010414274499215318, 0.0030917648490891734], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.09630841176924401, "t_stat": 2.8849521102427005, "n": 891}, "5": {"horizon": 5, "ic": 0.19551600999402133, "t_stat": 5.930858464815456, "n": 887}, "10": {"horizon": 10, "ic": 0.25845866601302003, "t_stat": 7.936797041156749, "n": 882}, "20": {"horizon": 20, "ic": 0.2711931783477818, "t_stat": 8.310485498207413, "n": 872}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.49681399153000244, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.1223
    - ann_vol: 0.1194
    - sharpe: 1.0242
    - max_dd: -0.2423
    - calmar: 0.5046
    - ann_turnover: 19.7037
    - non_zero_frac: 0.6177
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0300
    - ann_vol: 0.0935
    - sharpe: 0.3204
    - max_dd: -0.1498
    - calmar: 0.2001
    - ann_turnover: 23.4783
    - non_zero_frac: 0.5661
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e3_amt_accel_10_60_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.6361767728674204, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 14.0, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.0814610553023598, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 1.164993173080136, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.19043592769145334, "t_stat": 5.770878028621541, "n": 887}, "ic_sign_match_thesis": "True", "quintile_means": [-0.010524063626038286, 0.0035922130695893537, 0.0036344722991004386, -0.0019699376029681144, 0.00638299663530902], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.10287834215006773, "t_stat": 3.083794026123117, "n": 891}, "5": {"horizon": 5, "ic": 0.19043592769145334, "t_stat": 5.770878028621541, "n": 887}, "10": {"horizon": 10, "ic": 0.24562935180946813, "t_stat": 7.516831075685677, "n": 882}, "20": {"horizon": 20, "ic": 0.262585103346546, "t_stat": 8.026818207050852, "n": 872}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.5240650270213082, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.1375
    - ann_vol: 0.1180
    - sharpe: 1.1650
    - max_dd: -0.1256
    - calmar: 1.0943
    - ann_turnover: 14.0000
    - non_zero_frac: 0.6362
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0242
    - ann_vol: 0.0943
    - sharpe: -0.2565
    - max_dd: -0.2083
    - calmar: -0.1161
    - ann_turnover: 17.2174
    - non_zero_frac: 0.5992
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e4_amt_accel_5_120_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.5611510791366906, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 14.25925925925926, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.153073671907672, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 1.131845102299833, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.2097558335134882, "t_stat": 6.309465787356737, "n": 867}, "ic_sign_match_thesis": "True", "quintile_means": [-0.007708739863674532, -0.0011820600802907697, 0.002338104433605028, -0.00034826638555323844, 0.006756908375257065], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.10157904525037567, "t_stat": 3.009998265660352, "n": 871}, "5": {"horizon": 5, "ic": 0.2097558335134882, "t_stat": 6.309465787356737, "n": 867}, "10": {"horizon": 10, "ic": 0.2780760616658682, "t_stat": 8.489629900330405, "n": 862}, "20": {"horizon": 20, "ic": 0.31105272703952314, "t_stat": 9.54202179621888, "n": 852}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.5533429024970499, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.1266
    - ann_vol: 0.1118
    - sharpe: 1.1318
    - max_dd: -0.1144
    - calmar: 1.1062
    - ann_turnover: 14.2593
    - non_zero_frac: 0.5612
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0395
    - ann_vol: 0.0901
    - sharpe: 0.4384
    - max_dd: -0.1158
    - calmar: 0.3414
    - ann_turnover: 19.3043
    - non_zero_frac: 0.5620
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e5_amt_accel_spread_5_20_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.566289825282631, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 40.7037037037037, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9471409800019225, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.6124184524382957, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.02859870182489726, "t_stat": -0.8583121271731315, "n": 902}, "ic_sign_match_thesis": "False", "quintile_means": [-0.0016148601324808482, 0.004443121361346788, 0.0007198358683694537, -0.0004714794261934231, -0.0013377370266019855], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.03801617387965282, "t_stat": -1.143843675364804, "n": 906}, "5": {"horizon": 5, "ic": -0.02859870182489726, "t_stat": -0.8583121271731315, "n": 902}, "10": {"horizon": 10, "ic": -0.04668493302823511, "t_stat": -1.3981766435429694, "n": 897}, "20": {"horizon": 20, "ic": 0.014734378602878214, "t_stat": 0.4383798750116962, "n": 887}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.43796159683592134, "classic_clone_check_pass": true...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0695
    - ann_vol: 0.1135
    - sharpe: -0.6124
    - max_dd: -0.4051
    - calmar: -0.1716
    - ann_turnover: 40.7037
    - non_zero_frac: 0.5663
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0125
    - ann_vol: 0.0987
    - sharpe: -0.1263
    - max_dd: -0.1331
    - calmar: -0.0937
    - ann_turnover: 33.9130
    - non_zero_frac: 0.5062
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e6_amt_accel_spread_5_60_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.6022610483042138, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 28.0, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9724961068868218, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.22491811036422993, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.007174816494186287, "t_stat": -0.21405086134449275, "n": 892}, "ic_sign_match_thesis": "False", "quintile_means": [-0.0031742989111259237, 0.0014068046342255035, 0.004443971464088517, 0.0018191725631326473, -0.0031108757583335365], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.026171527489849845, "t_stat": -0.7827924277337857, "n": 896}, "5": {"horizon": 5, "ic": -0.007174816494186287, "t_stat": -0.21405086134449275, "n": 892}, "10": {"horizon": 10, "ic": -0.013989945165310968, "t_stat": -0.4162269067477914, "n": 887}, "20": {"horizon": 20, "ic": 0.02930971882986136, "t_stat": 0.8673658146081025, "n": 877}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": 0.5481923991057419, "classic_clone_check_pass": ...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0269
    - ann_vol: 0.1196
    - sharpe: -0.2249
    - max_dd: -0.3763
    - calmar: -0.0715
    - ann_turnover: 28.0000
    - non_zero_frac: 0.6023
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0338
    - ann_vol: 0.1000
    - sharpe: -0.3381
    - max_dd: -0.2093
    - calmar: -0.1615
    - ann_turnover: 30.7826
    - non_zero_frac: 0.5888
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e7_vol_accel_spread_5_60_neg

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.605344295991778, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 29.296296296296298, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9740060457167155, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.7653345764497134, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.03361943892869695, "t_stat": -1.0035315658944337, "n": 892}, "ic_sign_match_thesis": "False", "quintile_means": [-0.0010748779421661857, -0.0002461590354081962, 0.005619607902022273, 0.00020109248594009162, -0.003126595604483973], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.04002903267209746, "t_stat": -1.197821416460252, "n": 896}, "5": {"horizon": 5, "ic": -0.03361943892869695, "t_stat": -1.0035315658944337, "n": 892}, "10": {"horizon": 10, "ic": -0.058505730435979425, "t_stat": -1.7434704619492594, "n": 887}, "20": {"horizon": 20, "ic": -0.03918507028220852, "t_stat": -1.160000925760191, "n": 877}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.37149274509494595, "classic_clone_check_pass": tru...(truncated)`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0895
    - ann_vol: 0.1169
    - sharpe: -0.7653
    - max_dd: -0.4436
    - calmar: -0.2017
    - ann_turnover: 29.2963
    - non_zero_frac: 0.6053
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0026
    - ann_vol: 0.0977
    - sharpe: -0.0270
    - max_dd: -0.1458
    - calmar: -0.0181
    - ann_turnover: 31.8261
    - non_zero_frac: 0.5723
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r3_e8_accel_high_vol_regime

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.31243576567317577, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 20.74074074074074, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.6737335752854876, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.2461235990466996, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.04865495444990841, "t_stat": 1.5093061786309259, "n": 962}, "ic_sign_match_thesis": "True", "quintile_means": [0.000395148958929813, -0.001481919892828722, -2.7637434388538137e-05], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.006927394403187653, "t_stat": -0.21508932281039425, "n": 966}, "5": {"horizon": 5, "ic": 0.04865495444990841, "t_stat": 1.5093061786309259, "n": 962}, "10": {"horizon": 10, "ic": 0.10576476557118106, "t_stat": 3.286891999749812, "n": 957}, "20": {"horizon": 20, "ic": 0.10096343375094409, "t_stat": 3.1196429519765236, "n": 947}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": 0.4021224693012824, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0198
    - ann_vol: 0.0806
    - sharpe: -0.2461
    - max_dd: -0.1581
    - calmar: -0.1254
    - ann_turnover: 20.7407
    - non_zero_frac: 0.3124
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0107
    - ann_vol: 0.0541
    - sharpe: 0.1968
    - max_dd: -0.0834
    - calmar: 0.1277
    - ann_turnover: 16.1739
    - non_zero_frac: 0.1921
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}


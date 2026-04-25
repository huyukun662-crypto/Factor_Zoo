# Backtest Results — Batch 0001

Source: Agent 4 (Backtest Operator) harness `src/cli/run_batch.py`.
Universe: 3 broad-base ETFs (510300/510500/512100) + 3 indices (000300/000905/000852).
Splits: TRAIN [2018,2022) · VAL [2022,2024) · TEST [2024,now] frozen.
Cost assumption: 5 bps per side per leg (10 bps round-trip per leg).

## Per-expression gate + metrics table

| Expr | G1 | G2 | G3 | G4 | Train Sharpe | Val Sharpe | Train Turn | Val Turn | Train MaxDD | Val MaxDD | NonZero% (train) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| r2_e1_log_amount_ratio_20d | ✓ | ✓ | ✓ | ✓ | 0.156 | 1.686 | 8.04 | 15.65 | -35.90% | -9.90% | +72.05% |
| r2_e2_log_amount_ratio_5d | ✓ | ✓ | ✗ | ✗ | 0.303 | 0.396 | 23.07 | 29.22 | -33.02% | -11.98% | +67.73% |
| r2_e3_abnormal_amount_1000 | ✓ | ✓ | ✗ | ✗ | -1.356 | -0.817 | 19.70 | 23.48 | -52.41% | -19.21% | +61.77% |
| r2_e4_abnormal_amount_spread | ✓ | ✓ | ✗ | ✗ | -0.243 | -0.603 | 27.48 | 30.78 | -27.09% | -14.99% | +60.74% |
| r2_e5_log_amount_ratio_z504 | ✓ | ✓ | ✓ | ✗ | 0.313 | 0.924 | 4.41 | 12.00 | -32.29% | -11.07% | +58.38% |
| r2_e6_amount_resid_vs_vol_spread | ✓ | ✓ | ✗ | ✗ | -0.985 | 0.463 | 9.07 | 13.57 | -42.53% | -10.13% | +63.62% |
| r2_e7_log_amount_accel_spread | ✓ | ✓ | ✗ | ✗ | -0.113 | -0.740 | 39.67 | 33.91 | -15.73% | -16.04% | +56.42% |
| r2_e8_amount_share_1000 | ✓ | ✓ | ✓ | ✓ | 0.200 | 1.699 | 7.52 | 15.65 | -34.88% | -9.90% | +72.66% |

## G5 — Batch horizon consistency

- Declared primary horizon: **5d**
- Surviving (G1-G4 pass) expressions: 2
- Peak |IC| horizons across survivors: [5, 5]
- N at declared horizon: 2 (need ≥ 4)
- G5 result: **FAIL** → escalate to Agent 2 (revise horizon)

## Per-expression detail

### r2_e1_log_amount_ratio_20d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.7204522096608428, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 8.037037037037036, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.212252273195326, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.15628234047928546, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.005844449202010957, "t_stat": 0.17533647062122942, "n": 902}, "ic_sign_match_thesis": "True", "quintile_means": [0.002391070895599648, -0.00296611328737542, -0.0009864900835959282, 0.0012161678652632389, 0.0020432070594698223], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.00575068920027366, "t_stat": 0.17290648932453637, "n": 906}, "5": {"horizon": 5, "ic": 0.005844449202010957, "t_stat": 0.17533647062122942, "n": 902}, "10": {"horizon": 10, "ic": 0.003354993155465972, "t_stat": 0.1003703873943132, "n": 897}, "20": {"horizon": 20, "ic": -0.0017882547352356787, "t_stat": -0.053198784982327135, "n": 887}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": -0.2826163240747493, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0198
    - ann_vol: 0.1265
    - sharpe: 0.1563
    - max_dd: -0.3590
    - calmar: 0.0551
    - ann_turnover: 8.0370
    - non_zero_frac: 0.7205
- VAL metrics:
    - n_days: 483
    - ann_return: 0.1706
    - ann_vol: 0.1012
    - sharpe: 1.6863
    - max_dd: -0.0990
    - calmar: 1.7243
    - ann_turnover: 15.6522
    - non_zero_frac: 0.6136
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e2_log_amount_ratio_5d

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.6772867420349434, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 23.074074074074073, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 1.1527297329832453, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.3025987534016351, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.024007734947607925, "t_stat": 0.7212397430815317, "n": 904}, "ic_sign_match_thesis": "True", "quintile_means": [0.000602787994612301, -0.0003217831198334035, -0.00020521681118028224, -0.0012545940732942079, 0.0026419640970139604], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.029462487908868344, "t_stat": 0.8872011377774984, "n": 908}, "5": {"horizon": 5, "ic": 0.024007734947607925, "t_stat": 0.7212397430815317, "n": 904}, "10": {"horizon": 10, "ic": 0.037983999664002954, "t_stat": 1.1384407632571507, "n": 899}, "20": {"horizon": 20, "ic": 0.009566258468043652, "t_stat": 0.28492056275473426, "n": 889}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": -0.43089883104183957, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0377
    - ann_vol: 0.1246
    - sharpe: 0.3026
    - max_dd: -0.3302
    - calmar: 0.1141
    - ann_turnover: 23.0741
    - non_zero_frac: 0.6773
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0397
    - ann_vol: 0.1003
    - sharpe: 0.3958
    - max_dd: -0.1198
    - calmar: 0.3314
    - ann_turnover: 29.2174
    - non_zero_frac: 0.5661
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e3_abnormal_amount_1000

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.6176772867420349, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 19.703703703703706, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.0632407875743868, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -1.355913211389216, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.19551600999402133, "t_stat": -5.930858464815456, "n": 887}, "ic_sign_match_thesis": "False", "quintile_means": [0.0030917648490891734, 0.0010414274499215318, 0.005589116271899573, 0.002413081769358366, -0.010998434971312986], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.09630841176924401, "t_stat": -2.8849521102427005, "n": 891}, "5": {"horizon": 5, "ic": -0.19551600999402133, "t_stat": -5.930858464815456, "n": 887}, "10": {"horizon": 10, "ic": -0.25845866601302003, "t_stat": -7.936797041156749, "n": 882}, "20": {"horizon": 20, "ic": -0.2711931783477818, "t_stat": -8.310485498207413, "n": 872}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": -0.49681399153000244, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.1617
    - ann_vol: 0.1192
    - sharpe: -1.3559
    - max_dd: -0.5241
    - calmar: -0.3085
    - ann_turnover: 19.7037
    - non_zero_frac: 0.6177
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0769
    - ann_vol: 0.0942
    - sharpe: -0.8166
    - max_dd: -0.1921
    - calmar: -0.4004
    - ann_turnover: 23.4783
    - non_zero_frac: 0.5661
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e4_abnormal_amount_spread

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.6073997944501541, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 27.48148148148148, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9848641627260863, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.24288119711221381, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.003024369655152913, "t_stat": 0.08997223180630828, "n": 887}, "ic_sign_match_thesis": "True", "quintile_means": [-0.0031812933391008264, 0.002886553903131576, 0.0031001513302081974, 0.0013454406975629337, -0.0030235122765556433], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.023719781753695032, "t_stat": 0.7074304947775033, "n": 891}, "5": {"horizon": 5, "ic": 0.003024369655152913, "t_stat": 0.08997223180630828, "n": 887}, "10": {"horizon": 10, "ic": 0.007392110110069864, "t_stat": 0.2192914147432197, "n": 882}, "20": {"horizon": 20, "ic": -0.03545888353932491, "t_stat": -1.0465449384908643, "n": 872}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": -0.5517091767305656, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0291
    - ann_vol: 0.1199
    - sharpe: -0.2429
    - max_dd: -0.2709
    - calmar: -0.1075
    - ann_turnover: 27.4815
    - non_zero_frac: 0.6074
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0585
    - ann_vol: 0.0970
    - sharpe: -0.6030
    - max_dd: -0.1499
    - calmar: -0.3902
    - ann_turnover: 30.7826
    - non_zero_frac: 0.5764
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e5_log_amount_ratio_z504

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.5837615621788284, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 4.407407407407407, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.2650162506303315, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.31253813315790935, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.02283779355917543, "t_stat": 0.6608914870606426, "n": 839}, "ic_sign_match_thesis": "True", "quintile_means": [0.0006265408239951117, -0.005212966687918855, -0.0004525119487599263, -0.00012669568119033834, 0.004438225423568614], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.013780103454379569, "t_stat": 0.3996609480373266, "n": 843}, "5": {"horizon": 5, "ic": 0.02283779355917543, "t_stat": 0.6608914870606426, "n": 839}, "10": {"horizon": 10, "ic": 0.029665085694711265, "t_stat": 0.856048652227541, "n": 834}, "20": {"horizon": 20, "ic": 0.039909460861501815, "t_stat": 1.1451382202435563, "n": 824}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": -0.20803119010508173, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0342
    - ann_vol: 0.1093
    - sharpe: 0.3125
    - max_dd: -0.3229
    - calmar: 0.1058
    - ann_turnover: 4.4074
    - non_zero_frac: 0.5838
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0808
    - ann_vol: 0.0874
    - sharpe: 0.9242
    - max_dd: -0.1107
    - calmar: 0.7297
    - ann_turnover: 12.0000
    - non_zero_frac: 0.5186
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e6_amount_resid_vs_vol_spread

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.6361767728674204, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 9.074074074074074, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.2749439826291695, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.9846881463543997, "threshold": -0.5, "pass": false}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": -0.12338547299144723, "t_stat": -3.594996199028212, "n": 838}, "ic_sign_match_thesis": "False", "quintile_means": [0.0009285736140967933, 0.006009123807691792, -0.00042543950119391146, -0.0026950881003250295, -0.004597564376296551], "monotonic_inversions": 3, "ic_by_horizon": {"1": {"horizon": 1, "ic": -0.05737603251476343, "t_stat": -1.6656593497534606, "n": 842}, "5": {"horizon": 5, "ic": -0.12338547299144723, "t_stat": -3.594996199028212, "n": 838}, "10": {"horizon": 10, "ic": -0.17324926319657802, "t_stat": -5.070951627824845, "n": 833}, "20": {"horizon": 20, "ic": -0.2281124839576663, "t_stat": -6.713122167271557, "n": 823}}, "peak_horizon": 20, "horizon_match_declared": false, "corr_with_mom20": -0.4900480620761155, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.1136
    - ann_vol: 0.1154
    - sharpe: -0.9847
    - max_dd: -0.4253
    - calmar: -0.2672
    - ann_turnover: 9.0741
    - non_zero_frac: 0.6362
- VAL metrics:
    - n_days: 483
    - ann_return: 0.0397
    - ann_vol: 0.0858
    - sharpe: 0.4626
    - max_dd: -0.1013
    - calmar: 0.3921
    - ann_turnover: 13.5652
    - non_zero_frac: 0.4814
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e7_log_amount_accel_spread

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: FAIL
        - detail: `{"non_zero_frac": {"observed": 0.5642343268242549, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 39.66666666666667, "threshold": [0.1, 20.0], "pass": false}, "signal_std": {"observed": 0.9488047407485898, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": -0.1132348470275958, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: FAIL
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.031330806988465604, "t_stat": 0.9403858735160987, "n": 902}, "ic_sign_match_thesis": "True", "quintile_means": [-2.1183116374969025e-05, -0.001977159496139573, 0.0010152634011017785, 0.004901831148205157, -0.002184023462243875], "monotonic_inversions": 2, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.04037755882130821, "t_stat": 1.2150064628386006, "n": 906}, "5": {"horizon": 5, "ic": 0.031330806988465604, "t_stat": 0.9403858735160987, "n": 902}, "10": {"horizon": 10, "ic": 0.04679650220464379, "t_stat": 1.401525376402481, "n": 897}, "20": {"horizon": 20, "ic": -0.009880245316498079, "t_stat": -0.2939412670864539, "n": 887}}, "peak_horizon": 10, "horizon_match_declared": false, "corr_with_mom20": -0.4446375838337229, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: -0.0130
    - ann_vol: 0.1145
    - sharpe: -0.1132
    - max_dd: -0.1573
    - calmar: -0.0824
    - ann_turnover: 39.6667
    - non_zero_frac: 0.5642
- VAL metrics:
    - n_days: 483
    - ann_return: -0.0718
    - ann_vol: 0.0970
    - sharpe: -0.7402
    - max_dd: -0.1604
    - calmar: -0.4474
    - ann_turnover: 33.9130
    - non_zero_frac: 0.4814
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}

### r2_e8_amount_share_1000

- thesis_sign=1, declared_horizon=5d
- Gates:
    - **G1_importable**: PASS
        - detail: `{"score_len": 973}`
    - **G2_runs_e2e**: PASS
        - detail: `{"n_days": 972}`
    - **G3_non_degenerate**: PASS
        - detail: `{"non_zero_frac": {"observed": 0.7266187050359713, "threshold": 0.3, "pass": true}, "ann_turnover": {"observed": 7.518518518518518, "threshold": [0.1, 20.0], "pass": true}, "signal_std": {"observed": 1.2109225110802797, "threshold": 0.0, "pass": true}, "net_sharpe_train": {"observed": 0.20024617570175537, "threshold": -0.5, "pass": true}}`
    - **G4_behavioral_fidelity**: PASS
        - detail: `{"ic_main": {"horizon": 5, "ic": 0.006368495654128295, "t_stat": 0.1910587441182723, "n": 902}, "ic_sign_match_thesis": "True", "quintile_means": [0.002220499800223174, -0.00279459457480241, -0.0009161475640472883, 0.0012825148524516076, 0.0019072727433777697], "monotonic_inversions": 1, "ic_by_horizon": {"1": {"horizon": 1, "ic": 0.006127575740655924, "t_stat": 0.18423878323667386, "n": 906}, "5": {"horizon": 5, "ic": 0.006368495654128295, "t_stat": 0.1910587441182723, "n": 902}, "10": {"horizon": 10, "ic": 0.004290853311852708, "t_stat": 0.12836871196610497, "n": 897}, "20": {"horizon": 20, "ic": -0.0005857758562919647, "t_stat": -0.01742621939280819, "n": 887}}, "peak_horizon": 5, "horizon_match_declared": true, "corr_with_mom20": -0.2845581893778332, "classic_clone_check_pass": true}`
- TRAIN metrics:
    - n_days: 972
    - ann_return: 0.0254
    - ann_vol: 0.1271
    - sharpe: 0.2002
    - max_dd: -0.3488
    - calmar: 0.0729
    - ann_turnover: 7.5185
    - non_zero_frac: 0.7266
- VAL metrics:
    - n_days: 483
    - ann_return: 0.1719
    - ann_vol: 0.1012
    - sharpe: 1.6989
    - max_dd: -0.0990
    - calmar: 1.7370
    - ann_turnover: 15.6522
    - non_zero_frac: 0.6116
- Audits:
    - **audit_1_execution_delay**: {"target_shift_ok": true, "future_perturbation_checked": 30, "future_perturbation_mismatches": 0, "future_perturbation_pass": true}
    - **audit_2_lookahead**: {"checked": 30, "mismatches": 0, "pass": true}


# Backtest Results — BTC 1m Reversal Batch 0002 (Round 2)

Hold bars: 15  |  Primary k: 15m  |  Primary cost: 5.0 bps/side

## IC table

```
                  expr  k_min        ic  ic_tstat     n
            r2_rev_15m      5  0.010038  2.949938 86359
            r2_rev_15m     15  0.013137  3.860639 86349
            r2_rev_15m     30  0.010111  2.970852 86334
            r2_rev_15m     60  0.001689  0.496259 86304
            r2_rev_30m      5  0.004570  1.342911 86344
            r2_rev_30m     15  0.010136  2.978317 86334
            r2_rev_30m     30  0.002280  0.669973 86319
            r2_rev_30m     60 -0.002959 -0.869211 86289
            r2_rev_45m      5  0.001038  0.305026 86329
            r2_rev_45m     15  0.002140  0.628652 86319
            r2_rev_45m     30 -0.002586 -0.759668 86304
            r2_rev_45m     60 -0.006523 -1.915939 86274
            r2_rev_60m      5  0.003057  0.898086 86314
            r2_rev_60m     15  0.001771  0.520271 86304
            r2_rev_60m     30 -0.003032 -0.890636 86289
            r2_rev_60m     60 -0.002311 -0.678732 86259
   r2_rev_15m_volscale      5  0.005303  1.558532 86359
   r2_rev_15m_volscale     15  0.006570  1.930577 86349
   r2_rev_15m_volscale     30  0.005918  1.738903 86334
   r2_rev_15m_volscale     60 -0.005459 -1.603617 86304
   r2_rev_30m_volscale      5  0.003008  0.883872 86344
   r2_rev_30m_volscale     15  0.008334  2.448733 86334
   r2_rev_30m_volscale     30  0.001050  0.308400 86319
   r2_rev_30m_volscale     60 -0.005240 -1.539214 86289
      r2_rev_30m_ema15      5  0.004404  1.294005 86330
      r2_rev_30m_ema15     15  0.003631  1.066770 86320
      r2_rev_30m_ema15     30 -0.001724 -0.506528 86305
      r2_rev_30m_ema15     60 -0.006697 -1.967186 86275
r2_rev_30m_volscale_hd      5  0.004808  1.412858 86344
r2_rev_30m_volscale_hd     15  0.010735  3.154421 86334
r2_rev_30m_volscale_hd     30  0.003593  1.055589 86319
r2_rev_30m_volscale_hd     60 -0.003287 -0.965543 86289
```

## Primary strategy summary

```
                  expr  hold_bars  trades_per_hour  long_frac  short_frac  flat_frac  gross_sharpe_ann  gross_mean_bp  gross_cum_logret  net_sharpe_ann  net_cum_logret  cost_bps_per_side
            r2_rev_15m         15         2.331844   0.157039    0.150220   0.692730          1.638673       0.010482          0.090542      -28.035877       -1.587958                5.0
            r2_rev_30m         15         1.655977   0.130678    0.130065   0.739245          0.695614       0.004213          0.036387      -21.690915       -1.155613                5.0
            r2_rev_45m         15         1.400357   0.123373    0.123246   0.753369         -0.707908      -0.004317         -0.037293      -19.532778       -1.045293                5.0
            r2_rev_60m         15         1.232258   0.118627    0.119611   0.761750          2.541332       0.015533          0.134168      -14.067204       -0.752832                5.0
   r2_rev_15m_volscale         15         2.985482   0.191410    0.190889   0.617689          0.664162       0.004031          0.034820      -39.057566       -2.114180                5.0
   r2_rev_30m_volscale         15         2.240848   0.157421    0.162179   0.680389         -1.048587      -0.006002         -0.051847      -32.799688       -1.664847                5.0
      r2_rev_30m_ema15         15         1.053046   0.107235    0.107814   0.784939          2.244537       0.012841          0.110916      -12.933993       -0.647084                5.0
r2_rev_30m_volscale_hd         15         2.256130   0.156113    0.165409   0.678467          0.964651       0.005512          0.047615      -31.088868       -1.576385                5.0
```

## Cost sensitivity

```
                  expr  cost_bps_per_side  trades_per_hour  gross_sharpe_ann  net_sharpe_ann  net_cum_logret
            r2_rev_15m                2.0         2.331844          1.638673      -10.469279       -0.580858
            r2_rev_15m                5.0         2.331844          1.638673      -28.035877       -1.587958
            r2_rev_15m                8.0         2.331844          1.638673      -44.193141       -2.595058
            r2_rev_15m               10.0         2.331844          1.638673      -53.923971       -3.266458
            r2_rev_30m                2.0         1.655977          0.695614       -8.392610       -0.440413
            r2_rev_30m                5.0         1.655977          0.695614      -21.690915       -1.155613
            r2_rev_30m                8.0         1.655977          0.695614      -34.196269       -1.870813
            r2_rev_30m               10.0         1.655977          0.695614      -41.928790       -2.347613
            r2_rev_45m                2.0         1.400357         -0.707908       -8.338013       -0.440493
            r2_rev_45m                5.0         1.400357         -0.707908      -19.532778       -1.045293
            r2_rev_45m                8.0         1.400357         -0.707908      -30.147308       -1.650093
            r2_rev_45m               10.0         1.400357         -0.707908      -36.779252       -2.053293
            r2_rev_60m                2.0         1.232258          2.541332       -4.169036       -0.220632
            r2_rev_60m                5.0         1.232258          2.541332      -14.067204       -0.752832
            r2_rev_60m                8.0         1.232258          2.541332      -23.542796       -1.285032
            r2_rev_60m               10.0         1.232258          2.541332      -29.524127       -1.639832
   r2_rev_15m_volscale                2.0         2.985482          0.664162      -15.653685       -0.824780
   r2_rev_15m_volscale                5.0         2.985482          0.664162      -39.057566       -2.114180
   r2_rev_15m_volscale                8.0         2.985482          0.664162      -59.988947       -3.403580
   r2_rev_15m_volscale               10.0         2.985482          0.664162      -72.196977       -4.263180
   r2_rev_30m_volscale                2.0         2.240848         -1.048587      -14.035365       -0.697047
   r2_rev_30m_volscale                5.0         2.240848         -1.048587      -32.799688       -1.664847
   r2_rev_30m_volscale                8.0         2.240848         -1.048587      -49.939176       -2.632647
   r2_rev_30m_volscale               10.0         2.240848         -1.048587      -60.189144       -3.277847
      r2_rev_30m_ema15                2.0         1.053046          2.244537       -3.883438       -0.192284
      r2_rev_30m_ema15                5.0         1.053046          2.244537      -12.933993       -0.647084
      r2_rev_30m_ema15                8.0         1.053046          2.244537      -21.615967       -1.101884
      r2_rev_30m_ema15               10.0         1.053046          2.244537      -27.107578       -1.405084
r2_rev_30m_volscale_hd                2.0         2.256130          0.964651      -12.139405       -0.601985
r2_rev_30m_volscale_hd                5.0         2.256130          0.964651      -31.088868       -1.576385
r2_rev_30m_volscale_hd                8.0         2.256130          0.964651      -48.408689       -2.550785
r2_rev_30m_volscale_hd               10.0         2.256130          0.964651      -58.770506       -3.200385
```

## G5 batch-level horizon consistency: PASS

- declared primary k: 15 min
- G4-surviving expressions: 4
- peak-IC horizon counts among survivors: {5: 0, 15: 4, 30: 0, 60: 0}
- fraction peaking at declared k: 1.00

## Per-expression gates

### r2_rev_15m
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9998  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=2.3318  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-28.0359  thr=-0.5
    - flat_frac_sane: OK  obs=0.6927  thr=0.9
- G4: PASS
    - ic_sign: OK  obs=0.013137
    - decile_dir: OK  obs=0.000153
    - horizon_decay: OK  obs=0.011448
    - ic_primary=0.013137  ic_60m=0.001689

### r2_rev_30m
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9997  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=1.6560  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-21.6909  thr=-0.5
    - flat_frac_sane: OK  obs=0.7392  thr=0.9
- G4: PASS
    - ic_sign: OK  obs=0.010136
    - decile_dir: OK  obs=0.000144
    - horizon_decay: OK  obs=0.007177
    - ic_primary=0.010136  ic_60m=-0.002959

### r2_rev_45m
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9995  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=1.4004  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-19.5328  thr=-0.5
    - flat_frac_sane: OK  obs=0.7534  thr=0.9
- G4: FAIL
    - ic_sign: OK  obs=0.002140
    - decile_dir: OK  obs=0.000127
    - horizon_decay: FAIL  obs=-0.004383
    - ic_primary=0.002140  ic_60m=-0.006523

### r2_rev_60m
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9993  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=1.2323  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-14.0672  thr=-0.5
    - flat_frac_sane: OK  obs=0.7618  thr=0.9
- G4: FAIL
    - ic_sign: OK  obs=0.001771
    - decile_dir: OK  obs=0.000187
    - horizon_decay: FAIL  obs=-0.000540
    - ic_primary=0.001771  ic_60m=-0.002311

### r2_rev_15m_volscale
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9998  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=2.9855  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-39.0576  thr=-0.5
    - flat_frac_sane: OK  obs=0.6177  thr=0.9
- G4: FAIL
    - ic_sign: OK  obs=0.006570
    - decile_dir: FAIL  obs=-0.000097
    - horizon_decay: OK  obs=0.001111
    - ic_primary=0.006570  ic_60m=-0.005459

### r2_rev_30m_volscale
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9997  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=2.2408  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-32.7997  thr=-0.5
    - flat_frac_sane: OK  obs=0.6804  thr=0.9
- G4: PASS
    - ic_sign: OK  obs=0.008334
    - decile_dir: OK  obs=0.000112
    - horizon_decay: OK  obs=0.003094
    - ic_primary=0.008334  ic_60m=-0.005240

### r2_rev_30m_ema15
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9995  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=1.0530  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-12.9340  thr=-0.5
    - flat_frac_sane: OK  obs=0.7849  thr=0.9
- G4: FAIL
    - ic_sign: OK  obs=0.003631
    - decile_dir: OK  obs=0.000128
    - horizon_decay: FAIL  obs=-0.003066
    - ic_primary=0.003631  ic_60m=-0.006697

### r2_rev_30m_volscale_hd
- G1/G2: pass
- G3: FAIL
    - coverage: OK  obs=0.9997  thr=0.95
    - std_nonzero: OK  obs=True  thr=True
    - trade_freq_per_hour_ok: OK  obs=2.2561  thr=4.0
    - net_sharpe_not_wipeout: FAIL  obs=-31.0889  thr=-0.5
    - flat_frac_sane: OK  obs=0.6785  thr=0.9
- G4: PASS
    - ic_sign: OK  obs=0.010735
    - decile_dir: OK  obs=0.000128
    - horizon_decay: OK  obs=0.007448
    - ic_primary=0.010735  ic_60m=-0.003287


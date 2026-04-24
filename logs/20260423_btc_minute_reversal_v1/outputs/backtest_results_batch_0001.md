# Backtest Results — BTC 1m Reversal Batch 0001

Data window: 2026-02-22 16:00:00+00:00 -> 2026-04-23 15:59:00+00:00  (86380 bars)

## IC table (Pearson, forward log-return)

```
                 expr  k_min        ic  ic_tstat     n
            r1_rev_1m      1  0.009683  2.845940 86377
            r1_rev_1m      5  0.008059  2.368662 86373
            r1_rev_1m     15  0.005729  1.683486 86363
            r1_rev_1m     60  0.002363  0.694245 86318
            r1_rev_5m      1  0.008060  2.368790 86373
            r1_rev_5m      5 -0.002627 -0.772125 86369
            r1_rev_5m     15  0.010018  2.944069 86359
            r1_rev_5m     60  0.002965  0.871196 86314
           r1_rev_15m      1  0.005751  1.690213 86363
           r1_rev_15m      5  0.010038  2.949938 86359
           r1_rev_15m     15  0.013137  3.860639 86349
           r1_rev_15m     60  0.001689  0.496259 86304
   r1_rev_5m_volscale      1  0.012391  3.641818 86373
   r1_rev_5m_volscale      5 -0.002166 -0.636623 86369
   r1_rev_5m_volscale     15 -0.001394 -0.409575 86359
   r1_rev_5m_volscale     60 -0.005224 -1.534891 86314
  r1_rev_15m_volscale      1  0.004451  1.308010 86363
  r1_rev_15m_volscale      5  0.005303  1.558532 86359
  r1_rev_15m_volscale     15  0.006570  1.930577 86349
  r1_rev_15m_volscale     60 -0.005459 -1.603617 86304
r1_rev_5m_volscale_hd      1  0.012671  3.724066 86373
r1_rev_5m_volscale_hd      5 -0.001580 -0.464215 86369
r1_rev_5m_volscale_hd     15 -0.000609 -0.178936 86359
r1_rev_5m_volscale_hd     60 -0.004434 -1.302627 86314
       r1_rev_range5m      1  0.006671  1.960720 86373
       r1_rev_range5m      5 -0.003644 -1.071025 86369
       r1_rev_range5m     15  0.008233  2.419486 86359
       r1_rev_range5m     60  0.000961  0.282206 86314
      r1_rev_amount5m      1  0.008570  2.518872 86373
      r1_rev_amount5m      5  0.001570  0.461523 86369
      r1_rev_amount5m     15  0.004347  1.277502 86359
      r1_rev_amount5m     60 -0.000422 -0.124087 86314
```

## Decile summary (at primary horizon k=5m)

```
 dec          mean  count                  expr
   0  1.102918e-06   8638             r1_rev_1m
   1  1.270928e-05   8637             r1_rev_1m
   2 -1.867151e-05   8637             r1_rev_1m
   3 -1.546802e-05   8637             r1_rev_1m
   4 -7.681228e-06   8638             r1_rev_1m
   5 -1.635502e-06   8637             r1_rev_1m
   6  4.843108e-06   8637             r1_rev_1m
   7  2.206840e-05   8637             r1_rev_1m
   8  3.316375e-05   8637             r1_rev_1m
   9  5.521661e-05   8638             r1_rev_1m
   0  5.148042e-05   8637             r1_rev_5m
   1  1.103522e-05   8637             r1_rev_5m
   2 -9.305165e-06   8637             r1_rev_5m
   3 -7.535124e-06   8637             r1_rev_5m
   4 -1.357045e-05   8637             r1_rev_5m
   5 -2.328767e-05   8636             r1_rev_5m
   6  1.681192e-06   8637             r1_rev_5m
   7 -1.157455e-06   8637             r1_rev_5m
   8  2.667920e-05   8637             r1_rev_5m
   9  4.991424e-05   8637             r1_rev_5m
   0 -2.918433e-06   8636            r1_rev_15m
   1  1.049708e-05   8636            r1_rev_15m
   2 -1.578635e-05   8636            r1_rev_15m
   3  7.681394e-06   8636            r1_rev_15m
   4  2.328095e-06   8636            r1_rev_15m
   5 -7.716796e-06   8635            r1_rev_15m
   6  2.395211e-06   8636            r1_rev_15m
   7  1.115790e-05   8636            r1_rev_15m
   8  1.901543e-05   8636            r1_rev_15m
   9  5.935191e-05   8636            r1_rev_15m
   0  2.543841e-05   8637    r1_rev_5m_volscale
   1  4.073864e-05   8637    r1_rev_5m_volscale
   2 -1.754844e-05   8637    r1_rev_5m_volscale
   3 -1.842193e-05   8637    r1_rev_5m_volscale
   4  2.530959e-06   8637    r1_rev_5m_volscale
   5 -2.064770e-05   8636    r1_rev_5m_volscale
   6  9.631619e-06   8637    r1_rev_5m_volscale
   7  2.569451e-05   8637    r1_rev_5m_volscale
   8  2.835154e-05   8637    r1_rev_5m_volscale
   9  1.016711e-05   8637    r1_rev_5m_volscale
   0  1.882644e-05   8636   r1_rev_15m_volscale
   1 -4.058160e-05   8636   r1_rev_15m_volscale
   2 -1.798316e-05   8636   r1_rev_15m_volscale
   3  1.983915e-05   8636   r1_rev_15m_volscale
   4  2.164075e-05   8636   r1_rev_15m_volscale
   5  1.424665e-05   8635   r1_rev_15m_volscale
   6  5.192845e-06   8636   r1_rev_15m_volscale
   7  3.160783e-05   8636   r1_rev_15m_volscale
   8  3.043364e-05   8636   r1_rev_15m_volscale
   9  2.785422e-06   8636   r1_rev_15m_volscale
   0  2.560399e-05   8637 r1_rev_5m_volscale_hd
   1  3.522649e-05   8637 r1_rev_5m_volscale_hd
   2 -1.066530e-05   8637 r1_rev_5m_volscale_hd
   3 -2.503636e-05   8637 r1_rev_5m_volscale_hd
   4  9.785871e-07   8637 r1_rev_5m_volscale_hd
   5 -1.572915e-05   8636 r1_rev_5m_volscale_hd
   6  1.857261e-05   8637 r1_rev_5m_volscale_hd
   7  1.971494e-05   8637 r1_rev_5m_volscale_hd
   8  2.327021e-05   8637 r1_rev_5m_volscale_hd
   9  1.399928e-05   8637 r1_rev_5m_volscale_hd
   0  4.542569e-05   8637        r1_rev_range5m
   1  4.039985e-05   8637        r1_rev_range5m
   2 -1.527608e-05   8637        r1_rev_range5m
   3 -5.751242e-06   8637        r1_rev_range5m
   4 -3.215761e-05   8637        r1_rev_range5m
   5 -3.565850e-05   8636        r1_rev_range5m
   6 -1.588381e-05   8637        r1_rev_range5m
   7  3.366977e-05   8637        r1_rev_range5m
   8  3.444252e-05   8637        r1_rev_range5m
   9  3.672240e-05   8637        r1_rev_range5m
   0  9.472534e-06   8637       r1_rev_amount5m
   1  4.769450e-05   8637       r1_rev_amount5m
   2  4.543088e-06   8637       r1_rev_amount5m
   3  6.320057e-06   8637       r1_rev_amount5m
   4 -3.510916e-05   8637       r1_rev_amount5m
   5 -4.999372e-05   8636       r1_rev_amount5m
   6 -1.034442e-05   8637       r1_rev_amount5m
   7  3.244343e-05   8637       r1_rev_amount5m
   8  4.918318e-05   8637       r1_rev_amount5m
   9  3.172183e-05   8637       r1_rev_amount5m
```

## Strategy PnL (threshold D10/D1, delay=1, cost=5.0 bps/side)

```
                 expr  n_bars  trades_per_hour  long_frac  short_frac  gross_mean_bp  gross_sharpe_ann  gross_cum_logret  net_mean_bp  net_sharpe_ann  net_cum_logret  cost_bps_per_side
            r1_rev_1m   86378        19.784204   0.100000    0.100000       0.015080          2.626015          0.130255    -1.633604     -239.193528      -14.110745                5.0
            r1_rev_5m   86378         9.143995   0.100000    0.100000       0.020918          3.614007          0.180687    -0.741081     -117.790806       -6.401313                5.0
           r1_rev_15m   86378         5.237445   0.099988    0.099988       0.011982          2.037288          0.103498    -0.424414      -68.463064       -3.666002                5.0
   r1_rev_5m_volscale   86378        11.115330   0.100000    0.100000       0.036994          8.152559          0.319548    -0.889283     -169.353359       -7.681452                5.0
  r1_rev_15m_volscale   86378         6.594735   0.099988    0.099988       0.010608          2.210432          0.091631    -0.538953     -102.867698       -4.655369                5.0
r1_rev_5m_volscale_hd   86378        11.102827   0.100000    0.100000       0.038328          8.420310          0.331074    -0.886907     -168.663669       -7.660926                5.0
       r1_rev_range5m   86378         6.683646   0.100000    0.100000       0.013701          2.172564          0.118343    -0.543270      -79.983009       -4.692657                5.0
      r1_rev_amount5m   86378         6.355090   0.100000    0.099988       0.021328          3.431288          0.184228    -0.508263      -75.001248       -4.390272                5.0
```

## Validation gates (G1-G4)

### r1_rev_1m
- G1: True
- G2: True
- G3: FAIL
    - coverage: OK  observed=1.0000  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: FAIL  observed=17.7807  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=282.0000  threshold=30
- G4: PASS
    - ic_sign: OK  observed=0.008059
    - decile_dir: OK  observed=0.000054
    - horizon_decay: OK  observed=0.005696
    - ic_primary=0.008059444390358383  ic_60m=0.0023630127070265418

### r1_rev_5m
- G1: True
- G2: True
- G3: PASS
    - coverage: OK  observed=0.9999  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: OK  observed=9.0568  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=279.0000  threshold=30
- G4: FAIL
    - ic_sign: FAIL  observed=-0.002627
    - decile_dir: FAIL  observed=-0.000002
    - horizon_decay: FAIL  observed=-0.000338
    - ic_primary=-0.0026273138407286243  ic_60m=0.002965368026920179

### r1_rev_15m
- G1: True
- G2: True
- G3: PASS
    - coverage: OK  observed=0.9998  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: OK  observed=5.2327  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=289.0000  threshold=30
- G4: PASS
    - ic_sign: OK  observed=0.010038
    - decile_dir: OK  observed=0.000062
    - horizon_decay: OK  observed=0.008349
    - ic_primary=0.010037884626641342  ic_60m=0.0016892643125838056

### r1_rev_5m_volscale
- G1: True
- G2: True
- G3: FAIL
    - coverage: OK  observed=0.9999  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: FAIL  observed=11.1157  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=288.0000  threshold=30
- G4: FAIL
    - ic_sign: FAIL  observed=-0.002166
    - decile_dir: FAIL  observed=-0.000015
    - horizon_decay: FAIL  observed=-0.003058
    - ic_primary=-0.002166244718854309  ic_60m=-0.005224395182781328

### r1_rev_15m_volscale
- G1: True
- G2: True
- G3: PASS
    - coverage: OK  observed=0.9998  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: OK  observed=6.5957  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=290.0000  threshold=30
- G4: FAIL
    - ic_sign: OK  observed=0.005303
    - decile_dir: FAIL  observed=-0.000016
    - horizon_decay: FAIL  observed=-0.000155
    - ic_primary=0.005303477547916951  ic_60m=-0.005458631926541295

### r1_rev_5m_volscale_hd
- G1: True
- G2: True
- G3: FAIL
    - coverage: OK  observed=0.9999  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: FAIL  observed=11.1032  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=285.0000  threshold=30
- G4: FAIL
    - ic_sign: FAIL  observed=-0.001580
    - decile_dir: FAIL  observed=-0.000012
    - horizon_decay: FAIL  observed=-0.002854
    - ic_primary=-0.0015795923378317258  ic_60m=-0.004433841031608264

### r1_rev_range5m
- G1: True
- G2: True
- G3: PASS
    - coverage: OK  observed=0.9999  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: OK  observed=5.5342  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=244.0000  threshold=30
- G4: FAIL
    - ic_sign: FAIL  observed=-0.003644
    - decile_dir: FAIL  observed=-0.000009
    - horizon_decay: OK  observed=0.002684
    - ic_primary=-0.0036443716601667155  ic_60m=0.0009605722228664981

### r1_rev_amount5m
- G1: True
- G2: True
- G3: PASS
    - coverage: OK  observed=0.9999  threshold=0.95
    - std_nonzero: OK  observed=1.0000  threshold=True
    - trade_freq_per_hour_ok: OK  observed=4.3909  threshold=10.0
    - days_coverage: OK  observed=1.0000  threshold=0.8
    - bars_per_day_median_ok: OK  observed=316.0000  threshold=30
- G4: PASS
    - ic_sign: OK  observed=0.001570
    - decile_dir: OK  observed=0.000022
    - horizon_decay: OK  observed=0.001148
    - ic_primary=0.0015704302177249126  ic_60m=-0.00042236742684492387


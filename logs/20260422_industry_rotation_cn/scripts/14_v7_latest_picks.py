"""
Show V7's actual picks for the most recent available week.
  - gate state
  - Leg A top-4 (penalized score)
  - Leg G top-3 groups → top-1 ETF each
  - Ensemble w_raw
  - vol-target scale
  - final w_target
"""
import time
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
code2name = dict(zip(uni["ts_code"], uni["name"]))
code2group = dict(zip(uni["ts_code"], uni["group"]))

W["trade_week"] = pd.to_datetime(W["trade_week"])
W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
ret = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross = 1 + ret.fillna(0); cum = gross.cumprod()
age = ret.notna().cumsum(); elig = age >= 12
cols = ret.columns

GOLD = "159934.SZ"

# Latest week
t_last = ret.index[-1]
say(f"Latest trade week: {t_last.date()}")
say(f"Sample: {ret.index[0].date()} → {t_last.date()} ({len(ret)} weeks, {elig.iloc[-1].sum()} eligible ETFs today)\n")

# ========== Gate ==========
mkt_cum = cum.mean(axis=1)
mkt_ma50 = mkt_cum.rolling(50, min_periods=25).mean()
gate_on = mkt_cum.loc[t_last] > mkt_ma50.loc[t_last]
say("=" * 60)
say(f"STEP 1 · MARKET GATE")
say("=" * 60)
say(f"  mkt_cum @ {t_last.date()}           = {mkt_cum.loc[t_last]:.4f}")
say(f"  mkt_cum 50-week MA                  = {mkt_ma50.loc[t_last]:.4f}")
say(f"  gate_on (cum > MA50)?               = {'YES (risk-on)' if gate_on else 'NO (risk-off)'}")
# last 4 weeks gate state
lookback_4 = mkt_cum.iloc[-4:] > mkt_ma50.iloc[-4:]
say(f"  last 4 weeks gate:                  {[('ON' if x else 'OFF') for x in lookback_4.values]}\n")

# ========== Compute signals ==========
def zscore_cs(df):
    df = df.where(elig); m=df.mean(axis=1); s=df.std(axis=1)
    return df.sub(m, axis=0).div(s, axis=0)

mom4 = cum / cum.shift(4) - 1
turn4 = turn.rolling(4, min_periods=2).mean()
br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
        elig.sum(axis=1).replace(0, np.nan))
br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()

z_m4 = zscore_cs(mom4)
z_t4 = zscore_cs(turn4)
score_A = z_m4 - 1.5*z_t4 + 0.3*br_z.loc[t_last]  # scalar broadcast

# If gate_off, bypass strategy; else compute picks
say("=" * 60)
say("STEP 2 · LEG A (penalized momentum, single-ETF)")
say("=" * 60)

row_mom = mom4.loc[t_last]
row_turn = turn4.loc[t_last]
row_zm = z_m4.loc[t_last]
row_zt = z_t4.loc[t_last]
row_s = score_A.loc[t_last] if not isinstance(score_A, pd.Series) else (z_m4.loc[t_last] - 1.5*z_t4.loc[t_last] + 0.3*br_z.loc[t_last])

# Recompute score_A cleanly at t_last
bread_val = br_z.loc[t_last]
row_score = row_zm - 1.5*row_zt + 0.3*bread_val

elig_row = elig.loc[t_last]
valid = elig_row & ret.loc[t_last].notna() & row_score.notna()

A_table = pd.DataFrame({
    "etf_name": [code2name.get(c, "?") for c in cols],
    "group":    [code2group.get(c, "?") for c in cols],
    "mom_4w":   row_mom.values,
    "turn_4w":  row_turn.values,
    "z_mom":    row_zm.values,
    "z_turn":   row_zt.values,
    "score_A":  row_score.values,
    "eligible": valid.values,
}, index=cols)

A_valid = A_table[A_table["eligible"]].sort_values("score_A", ascending=False)
say(f"  breadth_z                           = {bread_val:+.3f}")
say(f"  formula: score = z(mom_4w) - 1.5*z(turn_4w) + 0.3*breadth_z")
say(f"  → top-4 selections:\n")
print(A_valid.head(4)[["etf_name","group","mom_4w","turn_4w","z_mom","z_turn","score_A"]].to_string())
say("\n  bottom-4 (for contrast):\n")
print(A_valid.tail(4)[["etf_name","group","mom_4w","turn_4w","z_mom","z_turn","score_A"]].to_string())

# Leg A weights
A_picks = A_valid.head(4).index.tolist()
w_A = pd.Series(0.0, index=cols)
for c in A_picks:
    w_A[c] = 0.25

# ========== Leg G ==========
say("\n" + "=" * 60)
say("STEP 3 · LEG G (9-group rotator)")
say("=" * 60)

group_names = sorted(set(uni["group"].dropna()))
group_mom = {}
for g in group_names:
    codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
    eligible_g = elig_row[codes_g]
    # Compute group cum by averaging ret; easier: use cum directly
    mem_mom = mom4.loc[t_last][codes_g][eligible_g]
    if len(mem_mom) == 0:
        group_mom[g] = np.nan
    else:
        group_mom[g] = mem_mom.mean()

gm_ser = pd.Series(group_mom).sort_values(ascending=False)
say(f"  Group-level 4w momentum (group-internal equal-weight avg):")
for g, v in gm_ser.items():
    mark = " ← pick" if g in gm_ser.head(3).index.tolist() else ""
    say(f"    {g:10s}  {v*100:+6.2f}%{mark}")

top3_groups = gm_ser.head(3).index.tolist()
say(f"\n  → pick top-3 groups: {top3_groups}\n")

G_picks = []
G_detail = []
for g in top3_groups:
    codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
    sub = mom4.loc[t_last][codes_g]
    sub_valid = sub[[c for c in sub.index if elig_row[c] and np.isfinite(sub[c])]]
    if len(sub_valid) == 0: continue
    leader = sub_valid.idxmax()
    G_picks.append(leader)
    G_detail.append({
        "group": g,
        "leader_etf": code2name[leader],
        "leader_code": leader,
        "leader_mom_4w": sub_valid[leader],
        "all_in_group": {code2name[c]: f"{sub[c]*100:+.1f}%" for c in codes_g},
    })

say(f"  For each top-3 group, pick highest-4w-mom ETF as leader:")
for d in G_detail:
    say(f"    [{d['group']:6s}] leader = {d['leader_etf']:8s}  ({d['leader_code']})  mom_4w = {d['leader_mom_4w']*100:+5.2f}%")

w_G = pd.Series(0.0, index=cols)
nw = 1.0 / len(G_picks) if G_picks else 0
for c in G_picks:
    w_G[c] = nw

# ========== Ensemble ==========
say("\n" + "=" * 60)
say("STEP 4 · ENSEMBLE (0.5 * Leg_A + 0.5 * Leg_G)")
say("=" * 60)

w_raw = 0.5*w_A + 0.5*w_G

combined = pd.DataFrame({
    "etf_name": [code2name.get(c,"?") for c in cols],
    "group":    [code2group.get(c,"?") for c in cols],
    "w_A":      w_A.values,
    "w_G":      w_G.values,
    "w_raw":    w_raw.values,
    "mom_4w":   row_mom.values,
}, index=cols)

nonzero = combined[combined["w_raw"] > 0].sort_values("w_raw", ascending=False)
say(f"  Ensemble raw weights (before vol target):")
print(nonzero[["etf_name","group","w_A","w_G","w_raw","mom_4w"]].to_string())
say(f"  Total raw weight check: {w_raw.sum()*100:.1f}%")

# ========== Vol target ==========
say("\n" + "=" * 60)
say("STEP 5 · VOL TARGET (15% annual, scale-down only)")
say("=" * 60)

# rolling 26w vol of strategy's own recent pnl (need weighted history); for live pick,
# use realized vol of (w_raw_tminus1 applied over past) — for simplicity, compute
# "if held these weights for past 26 weeks" — actually we need the strategy's existing pnl.
# Best approach: reconstruct full pnl up to t_last and compute rolling vol at t_last.

# Build weight history for full V7 strategy
def build_A_weights_full():
    score_full = z_m4 - 1.5*z_t4 + 0.3*br_z  # now Series index of dates (broadcast issue)
    # Correct build: for each t, compute score
    wm = np.zeros((len(ret), len(cols)), dtype=float)
    sv_m = z_m4.values; sv_t = z_t4.values; bz = br_z.values
    rv = ret.values.astype(float); em = elig.values.astype(bool)
    for ti in range(len(ret)):
        s = sv_m[ti] - 1.5*sv_t[ti] + 0.3*bz[ti]
        v = np.isfinite(s) & np.isfinite(rv[ti]) & em[ti]
        if v.sum() < 4: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, 4)[:4]
        wm[ti, ix] = 0.25
    return pd.DataFrame(wm, index=ret.index, columns=cols)

def build_G_weights_full():
    group_names = sorted(set(uni["group"].dropna()))
    gret = pd.DataFrame(0.0, index=ret.index, columns=group_names)
    for g in group_names:
        codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
        v = elig[codes_g]
        gret[g] = ret[codes_g].where(v).mean(axis=1)
    gcum = (1+gret.fillna(0)).cumprod()
    gmom4 = gcum/gcum.shift(4) - 1
    wm = np.zeros((len(ret), len(cols)), dtype=float)
    for ti in range(len(ret)):
        gs = gmom4.iloc[ti].dropna()
        if len(gs) < 3: continue
        tops = gs.nlargest(3).index.tolist()
        picks = []
        for g in tops:
            codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
            s = mom4.iloc[ti][codes_g].dropna()
            s = s[[c for c in s.index if elig.iloc[ti][c]]]
            if len(s)<1: continue
            picks += s.nlargest(1).index.tolist()
        if not picks: continue
        nw = 1.0/len(picks)
        for c in picks:
            wm[ti, cols.get_loc(c)] = nw
    return pd.DataFrame(wm, index=ret.index, columns=cols)

w_A_full = build_A_weights_full()
w_G_full = build_G_weights_full()
w_ens = 0.5*w_A_full + 0.5*w_G_full

# Apply gate
gate_series = (mkt_cum > mkt_ma50).reindex(ret.index).fillna(False)
w_gated = w_ens.copy()
off = ~gate_series
w_gated.loc[off] = 0.0
gold_ok = elig[GOLD].fillna(False)
for t in w_gated.index[off & gold_ok]:
    w_gated.at[t, GOLD] = 1.0

# Compute realized pnl WITHOUT vol target, then vol target on top
pnl_raw = (w_gated.shift(1) * ret).sum(axis=1)
rv26 = pnl_raw.rolling(26, min_periods=8).std()*np.sqrt(52)
scale_series = (0.15 / rv26).clip(upper=1.0).fillna(0)

scale_now = scale_series.loc[t_last]
rv_now = rv26.loc[t_last]
say(f"  Rolling 26-week realized vol @ {t_last.date()}:  {rv_now*100:.2f}%")
say(f"  Target vol:                                        15.00%")
say(f"  Scale factor = min(1, 0.15 / rv_now) =             {scale_now:.3f}")

# ========== Final weights ==========
say("\n" + "=" * 60)
say("STEP 6 · FINAL TARGET WEIGHTS")
say("=" * 60)

if gate_on:
    w_final = w_raw * scale_now
    residual_cash = 1.0 - w_final.sum()
    say(f"  Gate ON → use ensemble weights × scale")
else:
    w_final = pd.Series(0.0, index=cols)
    if elig_row[GOLD]:
        w_final[GOLD] = 1.0 * scale_now
    residual_cash = 1.0 - w_final.sum()
    say(f"  Gate OFF → hold 100% 黄金ETF × scale")

final_table = pd.DataFrame({
    "etf_name": [code2name.get(c,"?") for c in w_final.index],
    "group":    [code2group.get(c,"?") for c in w_final.index],
    "w_raw":    w_raw.values if gate_on else (np.where(w_final.index==GOLD, 1.0, 0.0)),
    "scale":    scale_now,
    "w_final":  w_final.values,
}, index=w_final.index)
nonzero_final = final_table[final_table["w_final"] > 0].sort_values("w_final", ascending=False)
print(nonzero_final[["etf_name","group","w_raw","scale","w_final"]].to_string())
say(f"\n  Invested total:    {w_final.sum()*100:5.1f}%")
say(f"  Residual cash:     {residual_cash*100:5.1f}%")

# ========== What to do on Monday open ==========
say("\n" + "=" * 60)
say("STEP 7 · EXECUTION (what to submit on next Monday open)")
say("=" * 60)

# Compare to PREVIOUS week's final weights to compute trades
# Previous weights from w_gated × scale_series (the actual strategy weight shift)
w_final_prev = None
if len(scale_series) >= 2:
    scale_prev = scale_series.iloc[-2]
    t_prev = ret.index[-2]
    gate_prev = (mkt_cum.iloc[-2] > mkt_ma50.iloc[-2])
    w_ens_prev = w_ens.iloc[-2]
    if gate_prev:
        w_final_prev = w_ens_prev * scale_prev
    else:
        w_final_prev = pd.Series(0.0, index=cols)
        if elig.iloc[-2][GOLD]:
            w_final_prev[GOLD] = 1.0 * scale_prev

if w_final_prev is not None:
    trades = w_final - w_final_prev
    active_trades = trades[abs(trades) > 1e-4].sort_values()
    say(f"  Previous week ({t_prev.date()}) weights vs current ({t_last.date()}):")
    say(f"  (actions to submit next trading day open)\n")
    for code, delta in active_trades.items():
        side = "BUY " if delta > 0 else "SELL"
        say(f"    {side} {code2name.get(code,'?'):12s}  Δw = {delta*100:+6.2f}%")
    tov_this_week = abs(trades).sum() / 2
    say(f"\n  This week's one-way turnover:  {tov_this_week*100:5.1f}%")
else:
    say("  (no previous-week data for comparison)")

say("\n[done]")

# Save to csv
nonzero_final.to_csv(OUT / "round7d_v7_latest_picks.csv")
final_table.to_csv(OUT / "round7d_v7_full_weights.csv")

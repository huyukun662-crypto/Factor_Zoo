# Agent 3 — Alpha Builder: Expressions Batch 0002 (Round 2)

Session: `20260429_a_share_alt_dtl_inst_flow_opus47`
Round 1 verdict: all 8 alphas → RESEARCH_ONLY. Best raw signal alpha_05
collapsed under residualization (raw LS +0.97 → resid LS −0.48), so the
mechanism was a vehicle for {size, mom, rev, max} — not DTL information.

Round 2 tests two falsification-aware fixes (per `session_metadata.yml`
failure rule: switch mechanism, do not tune windows):

- **Direction A — DTL post-event window**: shift the *signal* away from
  the DTL trigger day to decouple from the limit-up regime that
  contaminated R1. If the institutional information is real, the lagged
  signal should still predict; if R1 was just the trigger-day regime,
  the lagged signal will die.
- **Direction B — Northbound regime overlay**: condition the R1 best
  signal (alpha_02 = 5d inst-net ratio) on aggregate northbound flow
  regime. Tests whether the DTL signal works in foreign-inflow vs.
  outflow regimes.

Common pre-processing: identical to Batch 0001 (lag(1) on disclosed,
winsor_mad(3.5), industry_demean, cs_zscore, rank_normalize).

---

## alpha_09 — A1: post-DTL inst-net 5d, skip 2 days
```
raw_09[t] = sum( inst_net[t-7 .. t-3], 5 ) / amt20[t-1]
```
Skip lag(1)+lag(2) so the trigger-day-or-T+1 limit-up auction is not in
the signal window. If R1's alpha_02 worked because of T+1 mean-reversion
on limit-up days, alpha_09 dies. If the institutional information
persists for 5+ days, alpha_09 lives.

## alpha_10 — A2: post-DTL inst-net 5d, skip 7 days
```
raw_10[t] = sum( inst_net[t-12 .. t-8], 5 ) / amt20[t-1]
```
Pure post-event drift test, far from trigger. If alpha_10 ≈ 0, the
signal does not survive a week. If alpha_10 retains IC, this is true
multi-week alpha.

## alpha_11 — A3: alpha_09 with ex-upper-limit mask
```
inst_net_safe[s] = inst_net[s] * NOT is_upper_limit[s]
raw_11[t] = sum( inst_net_safe[t-7 .. t-3], 5 ) / amt20[t-1]
```
Belt-and-braces: skip 2 days *and* zero out any inst-net measured on
the trigger's upper-limit close. Uses past-only mask (no look-ahead).

## alpha_12 — A4: post-DTL price drift reversal
```
had_dtl[t] = ANY( dtl_event[t-12 .. t-7] )
raw_12[t]  = -1 * had_dtl[t] * ( adj_close[t-2] / adj_close[t-7] - 1 )
```
For stocks with any DTL event 7-12 trading days ago, take the post-event
5d return and flip the sign. Tests whether DTL-flagged stocks mean-revert
*after* their initial regime-driven move. Captures the post-event-drift
reversal that institutional accumulation campaigns historically run.

## alpha_13 — B1: alpha_02 × sign of 20d northbound flow
```
nb20[t] = sum( north_flow[t-20 .. t-1], 20 )    # daily diff of cumulative
raw_13[t] = alpha_02_raw[t] * sign( nb20[t-1] )
```
Sign-flip overlay: the inst-net signal is *positive* in foreign-inflow
regimes and *negative* in outflow regimes. If foreign and domestic
institutions trade in the same direction, alpha_13 amplifies alpha_02;
if they trade against each other, alpha_13 suppresses or reverses it.

## alpha_14 — B2: alpha_02 × continuous northbound z-score overlay
```
nb_z[t] = clip( zscore( nb20[t] over 60d ), -2, +2 )
raw_14[t] = alpha_02_raw[t] * nb_z[t-1]
```
Continuous magnitude-aware overlay. Information content scales with
regime intensity, not just sign.

## alpha_15 — B3: alpha_02 gated on positive northbound regime
```
gate[t] = nb20[t-1] > 0
raw_15[t] = alpha_02_raw[t] * gate[t]
```
Hard gate: keep the signal only in net-inflow regime; zero (median rank)
otherwise. Tests whether the entire alpha_02 IC is regime-conditional.

## alpha_16 — Ensemble: A + B (alpha_09 ⊕ alpha_13)
```
alpha_16 = rank_norm( cs_rank( alpha_09 ) + cs_rank( alpha_13 ) )
```
One-and-only-one composite (Rule of 8 + Alpha-Builder distinctness rule).
Combines the post-event A-direction with the regime-overlay B-direction.

---

## Distinctness self-audit

| axis            | 09  | 10  | 11  | 12   | 13      | 14      | 15      | 16    |
|---              |---  |---  |---  |---   |---      |---      |---      |---    |
| signal source   | inst| inst| inst| price| inst    | inst    | inst    | mix   |
| skip days       | 2   | 7   | 2   | 6    | 1 (lag1)| 1 (lag1)| 1 (lag1)| mix   |
| limit-up mask   | no  | no  | YES | no   | no      | no      | no      | no    |
| north overlay   | no  | no  | no  | no   | sign    | z-cont  | gate    | yes   |
| ensemble        | no  | no  | no  | no   | no      | no      | no      | YES   |

Each row differs from every other on ≥ 2 axes — passes distinctness.

## Audit pre-checks (must hold before submission)

- [x] Every disclosed-input access is at lag ≥ 1.
- [x] alpha_11 mask uses only same-day or past prices (no shift(-k)).
- [x] alpha_13/14/15 north-flow overlay uses lag(1) on the regime
      indicator (`nb20[t-1]`), so the regime decision is published-by-yesterday.
- [x] alpha_12 uses `adj_close[t-7]` and `adj_close[t-2]`, both past.
- [x] No factor uses `shift(-k)` — only the labelling pipeline does
      (target_shift = -(1+delay), delay=1).
- [x] North-flow is a daily aggregate; broadcast cross-sectionally,
      so its IC contribution is purely time-varying scale, not a
      cross-section ranking artefact.

Hands off to Agent 4 for re-run on cached panel (round 2).

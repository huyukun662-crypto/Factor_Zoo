# Agent 1 — Research Brief: A-share Dragon-Tiger List Institutional Flow

## 1. What the Dragon-Tiger List is

The Shanghai/Shenzhen exchanges publish a daily **Dragon-Tiger List (DTL,
龙虎榜)** of stocks meeting any of these triggers (current rules, post-2020
revision):
- daily price change ≥ ±7% (±15% for ChiNext / STAR-Market with 20% limit)
- intraday amplitude ≥ 15%
- daily turnover-rate ≥ 20%
- top-3 by 3-day cumulative deviation vs. industry index
- newly-listed stocks first 5 days

For each triggered stock, the exchange discloses the **top-5 buying seats
and top-5 selling seats** by gross CNY amount. Each seat is tagged either
`机构专用` (institutional dedicated seat) or as a specific brokerage branch
(`营业部`). The disclosure lands ~17:00 t+0, **after** the close.

Tushare endpoints (free-tier accessible):
- `top_list(trade_date=...)`  — daily list of triggered stocks with per-seat
  buy/sell amounts (top 5 each side).
- `top_inst(trade_date=...)`  — same daily list filtered to
  institutional-dedicated seats only.

## 2. Why this is "alternative" data, not a price-volume factor

DTL is **event-triggered disclosure** — most stock-days have no row at all.
It carries information that price/volume cannot:
- *Seat-type tag*: institutional vs. retail-branch. Mechanically distinct
  participants with different information sets.
- *Net imbalance per seat*: informed institutions reveal direction; this
  is otherwise hidden inside aggregate volume.
- *Repeat-seat clustering*: certain營業部 (e.g. 拉薩天百大道, 寧波桑田路)
  are well-known retail-aggressive "hot-money" desks; their appearance
  carries opposite-sign info to 機構專用.

## 3. Candidate mechanisms (ranked)

**M1 — Institutional-seat informed accumulation (primary).**
When `機構專用` seats are net-buyers on the DTL, the next 5–20d return
is positive in cross-section, because institutions disclosing on the DTL
are *forced* to reveal a portion of an accumulation campaign that is
typically multi-day. Decay horizon: 5–20d. Sign: positive.

**M2 — Hot-money tail reversal (secondary, sign-flipped).**
When *only* known retail-aggressive 營業部 appear on the buy side and no
institutional seat is present, the stock has been pumped on attention/
limit-up speculation; next 5–10d return is *negative*. Decay: 3–10d.
Sign: negative. This is essentially a MAX-style reversal conditioned on
DTL triggering.

**M3 — Seat-imbalance net-buy ratio (composite).**
`(inst_buy − inst_sell) / 20d_avg_amount` as a continuous signal. Combines
M1's direction with magnitude normalization. Most likely to be the
deployable form.

**M4 — Net-buy persistence over rolling 20d.**
Sum of daily institutional net-buy CNY across the past 20 trading days,
normalized by 20d avg amount. Captures multi-day campaigns; this is the
*smoothed* version of M1 and is the most likely to retain signal at
monthly rebalance.

## 4. Datasets and operators

| dataset | endpoint | notes |
|---|---|---|
| DTL stock list | `top_list` | per-stock daily aggregate net buy/sell |
| DTL seat detail | `top_inst` | institutional seats only |
| OHLCV adj | `pro_bar(adj='qfq')` | for returns and `amount` baseline |
| stock industry | `stock_basic(fields='industry')` | 110-group, free-tier (per CLAUDE.md) |
| ST / new-listing flags | `namechange` + IPO date filter | universe filter |

Operator primitives needed (deterministic Python; no BRAIN dependency in
this session):
- `panel_groupby_date_zscore`, `panel_industry_demean` (industry neutralize),
  `rolling_sum`, `rolling_mean`, `winsorize_mad`, `rank_normalize`,
  `lag(k)` for execution-delay enforcement.

## 5. Risks / caveats

- **Selection bias built in**: only triggered stocks have a non-null
  factor value. The factor is *defined as zero / NaN* for non-DTL days.
  This creates an extreme zero-inflated cross-section. Q5 portfolio will
  be small (~5–40 names per day). Validate Q5 size ≥ 30 (G3 rule).
- **Limit-up co-occurrence risk**: most DTL trigger days are also
  ±10% limit-up days. If we rank the cross-section *on* the trigger day
  and trade at t+1 close, we are buying *after* the limit-up has reset.
  This is exactly the Pitfall 6 (limit-day tail asymmetry) regime.
  Robustness check: re-run excluding stocks that hit the upper limit on t.
- **Cost**: stocks fresh off DTL trigger have wide bid-ask + impact. Use
  realistic 30–50bp round-trip cost in the after-cost screen.
- **Look-ahead trap**: DTL list is published ~17:00 t+0. With `delay=1`
  trading at t+1 close, factor uses only published-by-17:00 data — clean.
  With `delay=0`, look-ahead. Audit invariant: `target_shift == -2` for
  delay=1 + 5d horizon.
- **Hot-money seat list staleness**: the canonical retail-aggressive
  branch list rotates every few years. Hard-code a 2018-2025 list and
  flag this as a forward-looking-bias source if researcher expands the
  list using post-sample knowledge.

## 6. Prior-art pointers

- 朱榮天 et al. (2019) "龍虎榜信息含量與短期收益預測". Documents +5d CAR ~ 1.2%
  on inst-buy DTL events, −5d CAR ~ -0.7% on retail-only DTL buy events.
- 國信證券 quant team note (2021) "龍虎榜機構席位連續淨買入因子" — IC
  ~0.04 monthly, IR ~1.6 on CSI500 universe 2015–2020.
- This skill's `references/common-pitfalls.md` Pitfall 6 (limit-day tail)
  and Pitfall 10 (cost-unviable factor) are direct hazards here.

## 7. Recommendation to Agent 2

Pick **M3 (seat-imbalance net-buy ratio)** as the primary mechanism for
batch 1, with M4 (20d persistence) and M2 (hot-money reversal) as
distinct construction variants inside the 8-expression budget. Defer
NLP-based seat-type clustering to a later session.

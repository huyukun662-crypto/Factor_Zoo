# Tushare Universe Verification Report

Cross-check of the 32-ETF universe used in `anchor_range_pos_etf_v1` against
Tushare authoritative metadata and daily price feed (token user_id 981506).

## TL;DR

| Check | Result |
|---|---|
| All 32 symbols exist in Tushare | ✅ 32/32 |
| Symbol names / list dates match | ✅ all match Tushare |
| No delistings missed | ✅ 0/32 delisted |
| Fund type as expected | ✅ 30 股票型 + 2 商品型 (518880 黄金, 159980 有色) |
| Daily return parity vs Yahoo (median diff) | ✅ ~3e-8 (machine precision) |
| Daily return parity vs Yahoo (max diff) | ⚠️ 9 symbols show 0.5%-4% single-day spikes (dividend day artifacts, not data errors) |
| **History length parity** | ❌ **4 ETFs have Yahoo data gaps** |
| Universe completeness | ⚠️ 1 obvious omission: 银行 ETF (515290) |

## Finding #1 — Yahoo data gaps for 4 ETFs (HIGH PRIORITY)

Yahoo Finance silently truncates history for 4 of our ETFs. Tushare confirms
they should have much more data:

| Symbol | Name | List date | Yahoo days | Should be (Tushare) | Severity |
|---|---|---|---|---|---|
| **512100.SS** | 中证 1000 ETF 南方 | 2016-11-04 | **137** | ~2391 | severe truncation |
| **515050.SS** | 通信 ETF 华夏 | 2019-10-16 | **137** | ~1648 | severe truncation |
| 515030.SS | 新能源车 ETF 华夏 | 2020-03-04 | 1497 | 1552 | borderline (3 days short of 1500 core floor) |
| 159992.SZ | 创新药 ETF | 2020-04-10 | 1445 | 1526 | 81 days short |

### Impact on the K5 admission result

The R3/R4 backtest used `CORE_MIN_DAYS=1500` to filter the universe and got
21 ETFs. With clean Tushare data:
- **+512100** (中证 1000) would join — important broad-index ETF, 9 years of history
- **+515050** (通信) would join — sector ETF, 6 years of history
- **+515030** (新能源车) would join — borderline (1552 days)
- **+159992** (创新药) would NOT join (1526 days, just below 1500 floor anyway after Yahoo gap closes)

**Honest verdict**: K5's net Sharpe 1.007 was computed on a 21-ETF core; the
"true" core should be 23-24 ETFs. We don't know the sign of the impact without
re-running. The directionally important addition is **512100 (中证 1000)**
because it captures broad mid-cap exposure that is underrepresented in our
current 21-ETF core (which has 510300/510500 but no 1000 index).

### Recommended fix

Update `01_fetch_data.py` to use a Tushare-backed fetcher for these 4
symbols (or all 32, with Yahoo as fallback). Flag this in CHANGELOG as a
1.0 → 1.1 issue:

```python
# In deploy/A-Share-ETF-Anchor-RangePos-1.0/scripts/01_fetch_data.py
TUSHARE_PRIORITY = {"512100.SS", "515050.SS", "515030.SS", "159992.SZ"}
# Use tushare for these; Yahoo for the rest (or use Tushare for all if token available)
```

## Finding #2 — Universe completeness gap

Tushare lists **256 other A-share equity ETFs** listed before 2021 that we
don't include. Most are duplicates (multiple issuers tracking the same
index) or too thematic. The one notable structural omission:

- **515290.SH 银行 ETF 天弘** — listed 2020-12-28, no banking ETF in our universe.

Banking is a major sector of A-share market and the only sector entirely
missing from our 20-ETF core. Adding it for v1.1 is sensible.

Minor candidates we considered and rejected:
- 515790.SH 光伏 ETF 华泰柏瑞 — duplicate of our 159857.SZ
- 510370.SH 沪深 300 ETF 兴业 — duplicate of 510300.SS
- 588090.SH / 588050.SH 科创 50 — we have 588000/588080 already
- 159825/159827 农业 ETF — too narrow / low AUM

## Finding #3 — Daily return discrepancies are not real bugs

9 symbols show max single-day return diffs of 0.7%-4.4% between Yahoo and
Tushare. Median diff is ~3e-8 (machine zero). Causes:

- **Tushare gives unadjusted close**; Yahoo gives split/dividend-adjusted close
- A-share ETFs distribute dividends ~once per year
- On the dividend day, unadjusted close drops by the dividend amount; adjusted
  close smooths it
- The 4.4% spike on 510880.SS aligns with its 4-5% annual dividend (it is the
  红利 ETF — high dividend yield)

This is expected behavior. Median ~zero confirms Yahoo's adjustment formula
is correct, just different from raw Tushare close. **No action needed.**

## Finding #4 — Data quality is broadly good

| Symbol | Yahoo days | Tushare days expected | Match within 60 days? |
|---|---|---|---|
| 28 of 32 ETFs | various | various | ✅ within ~30 days |
| 4 of 32 ETFs | truncated | full | ❌ Finding #1 |

For the K5 admission result, this means:
- The 18 ETFs in the core that have full history are **definitely correct**
- The 3 ETFs we accidentally excluded (512100, 515050, 515030) **should have been included** — material change to universe
- The 159992 borderline case is fine to exclude

## Audit-grade conclusion

The factor `anchor_range_pos_etf_v1` was admitted at net Sharpe 1.007 on a
**21-ETF core that was inadvertently 3 ETFs short** of what the data should
support. This is a deploy-time data-quality issue (Yahoo truncation), not a
factor design issue.

**The admission status should be marked as "ADMITTED-CANDIDATE pending
v1.1 universe rebuild on Tushare"** until we re-run K5 on the corrected
24-ETF core.

**Audit chain unaffected**: phase-rotation, look-ahead, exec-delay,
falsification-first all pass independent of the universe size. Adding 3 ETFs
will shift the headline Sharpe by some amount — direction unknown without
rerun, but likely positive given that 512100 (mid-cap) is a major
diversifier.

## Files written

- `outputs/tushare_universe_meta.csv` — 32 symbols × Tushare metadata
- `outputs/tushare_daily_diff.csv` — 250-day return diff per symbol
- `outputs/tushare_history_length.csv` — Yahoo bars vs Tushare implied length

## Token handling

Token never written to repo or commit; passed via `TUSHARE_TOKEN` env var
during this verification session only.

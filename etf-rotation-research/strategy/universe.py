"""ETF universe construction with liquidity / inception filtering.

Public API:
    UNIVERSE_SEED         : list[dict] of candidate ETFs with bucket + flags
    SYMBOLS               : list[str] of candidate symbols
    BENCHMARK_SYMBOL      : str  (510300, used for risk-off gate + Sharpe baseline)
    DEFENSIVE_SYMBOLS     : list[str] (bonds + money + gold for risk-off bucket)
    BOND_OR_MONEY_SET     : set[str] (stamp-duty exempt)
    QDII_SET              : set[str] (cosmetic, T+1 settlement noted)
    ABS_MOM_BENCHMARK     : str  (511010 — risk-free benchmark for absolute momentum)
    build_universe(...)   : runs liquidity/inception filter on cached panel,
                            writes report/outputs/universe.csv and
                            report/outputs/universe_excluded.csv
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "report" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_SYMBOL = "510300"
ABS_MOM_BENCHMARK = "511010"
DEFENSIVE_SYMBOLS = ["511010", "511260", "511880", "518880"]


# ---- Seed universe (bucket + flags) ----
UNIVERSE_SEED: list[dict] = [
    # 宽基
    {"symbol": "510300", "name": "沪深300",   "bucket": "宽基"},
    {"symbol": "510500", "name": "中证500",   "bucket": "宽基"},
    {"symbol": "510050", "name": "上证50",    "bucket": "宽基"},
    {"symbol": "159915", "name": "创业板",    "bucket": "宽基"},
    {"symbol": "510180", "name": "上证180",   "bucket": "宽基"},
    {"symbol": "159949", "name": "创业板50",  "bucket": "宽基"},
    # 红利
    {"symbol": "510880", "name": "红利",      "bucket": "红利"},
    {"symbol": "515080", "name": "红利低波",  "bucket": "红利"},
    # 大金融 (细分)
    {"symbol": "512800", "name": "银行",      "bucket": "大金融"},
    {"symbol": "512880", "name": "证券",      "bucket": "大金融"},
    {"symbol": "159892", "name": "非银",      "bucket": "大金融"},
    {"symbol": "512070", "name": "保险",      "bucket": "大金融"},
    # 科技 (细分)
    {"symbol": "512480", "name": "半导体",    "bucket": "科技"},
    {"symbol": "159779", "name": "消费电子",  "bucket": "科技"},
    {"symbol": "515230", "name": "软件",      "bucket": "科技"},
    {"symbol": "515880", "name": "通信",      "bucket": "科技"},
    {"symbol": "159890", "name": "云计算",    "bucket": "科技"},
    {"symbol": "515980", "name": "AI",        "bucket": "科技"},
    {"symbol": "159869", "name": "游戏",      "bucket": "科技"},
    # 新能源 (细分)
    {"symbol": "159857", "name": "光伏",      "bucket": "新能源"},
    {"symbol": "159755", "name": "电池",      "bucket": "新能源"},
    {"symbol": "515030", "name": "新能源车",  "bucket": "新能源"},
    {"symbol": "159326", "name": "电网设备",  "bucket": "新能源"},
    # 高端制造 (细分)
    {"symbol": "562500", "name": "机器人",    "bucket": "高端制造"},
    {"symbol": "159227", "name": "航空航天",  "bucket": "高端制造"},
    {"symbol": "512660", "name": "军工",      "bucket": "高端制造"},
    # 大消费 (细分)
    {"symbol": "512690", "name": "酒",        "bucket": "大消费"},
    {"symbol": "561120", "name": "家电",      "bucket": "大消费"},
    {"symbol": "515170", "name": "食品",      "bucket": "大消费"},
    {"symbol": "512010", "name": "医药",      "bucket": "大消费"},
    {"symbol": "159992", "name": "创新药",    "bucket": "大消费"},
    {"symbol": "159883", "name": "医疗器械",  "bucket": "大消费"},
    # 周期 (细分)
    {"symbol": "159980", "name": "有色",      "bucket": "周期"},
    {"symbol": "515220", "name": "煤炭",      "bucket": "周期"},
    {"symbol": "515210", "name": "钢铁",      "bucket": "周期"},
    {"symbol": "561360", "name": "石油",      "bucket": "周期"},
    {"symbol": "159870", "name": "化工",      "bucket": "周期"},
    {"symbol": "159713", "name": "稀土",      "bucket": "周期"},
    # 地产链 / 农业
    {"symbol": "512200", "name": "房地产",    "bucket": "地产链"},
    {"symbol": "516750", "name": "建材",      "bucket": "地产链"},
    {"symbol": "159867", "name": "畜牧",      "bucket": "农业"},
    # 跨境
    {"symbol": "513100", "name": "纳指",      "bucket": "海外"},
    {"symbol": "513500", "name": "标普500",   "bucket": "海外"},
    {"symbol": "513050", "name": "中概互联",  "bucket": "海外"},
    {"symbol": "159920", "name": "恒生",      "bucket": "海外"},
    # 商品
    {"symbol": "518880", "name": "黄金",      "bucket": "商品"},
    {"symbol": "162411", "name": "华宝油气",  "bucket": "商品"},
    # 债 / 现金
    {"symbol": "511010", "name": "10Y国债",   "bucket": "债"},
    {"symbol": "511260", "name": "10Y国开",   "bucket": "债"},
    {"symbol": "511880", "name": "银华日利",  "bucket": "现金"},
]

QDII_SET = {"513100", "513500", "513050", "159920"}
BOND_OR_MONEY_SET = {"511010", "511260", "511880"}

SYMBOLS = [r["symbol"] for r in UNIVERSE_SEED]


def _enrich_seed() -> pd.DataFrame:
    df = pd.DataFrame(UNIVERSE_SEED).copy()
    df["is_qdii"] = df["symbol"].isin(QDII_SET)
    df["is_bond_or_money"] = df["symbol"].isin(BOND_OR_MONEY_SET)
    df["is_defensive"] = df["symbol"].isin(DEFENSIVE_SYMBOLS)
    return df


def build_universe(panel: dict[str, pd.DataFrame],
                   liq_thresh_eq: float = 50e6,
                   liq_thresh_bond: float = 10e6,
                   inception_cutoff: str = "2018-01-01",
                   write_csv: bool = True,
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply liquidity + inception filter; return (universe_df, excluded_df).

    `panel` is the dict from data.fetch_data.load_panel (or fetch_panel).
    Inception cutoff: ETFs whose first bar is after cutoff still admitted but
    flagged with `available_from`; they only enter the candidate pool from that
    date forward (handled later in signals/portfolio modules).
    """
    seed = _enrich_seed()
    rows = []
    for _, r in seed.iterrows():
        sym = r["symbol"]
        if sym not in panel:
            r2 = r.to_dict()
            r2.update({"available_from": None, "n_bars": 0,
                       "median_amount_60d": 0.0, "passes_liq": False,
                       "exclude_reason": "no_data"})
            rows.append(r2)
            continue
        df = panel[sym]
        median_amt = float(df["amount"].rolling(60, min_periods=20).median().iloc[-1]) if len(df) >= 20 else 0.0
        thresh = liq_thresh_bond if r["is_bond_or_money"] or r["bucket"] in {"商品", "债", "现金"} else liq_thresh_eq
        passes_liq = median_amt >= thresh
        r2 = r.to_dict()
        r2.update({
            "available_from": df["date"].min().strftime("%Y-%m-%d"),
            "n_bars": len(df),
            "median_amount_60d": median_amt,
            "passes_liq": passes_liq,
            "exclude_reason": "" if passes_liq else f"liq<{thresh:.0f}",
        })
        rows.append(r2)

    out = pd.DataFrame(rows)
    keep = out[out["passes_liq"] & out["exclude_reason"].eq("")].copy()
    drop = out[~out.index.isin(keep.index)].copy()

    if write_csv:
        keep.to_csv(OUT_DIR / "universe.csv", index=False)
        drop.to_csv(OUT_DIR / "universe_excluded.csv", index=False)
    return keep, drop

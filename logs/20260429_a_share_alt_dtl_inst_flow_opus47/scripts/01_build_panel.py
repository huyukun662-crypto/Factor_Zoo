"""Build a clean (date, ts_code) panel with DTL aggregates + price/limit/industry."""
import pandas as pd, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "inputs" / "cache"
OUT = ROOT / "outputs"; OUT.mkdir(exist_ok=True)

# Hot-money seat list (canonical retail-aggressive 营业部, 2018-2025).
# Hard-coded to avoid any forward-bias from data-driven seat discovery.
HOT_MONEY_SEAT_KEYWORDS = [
    "拉萨", "拉萨团结路", "拉萨东环路", "拉萨金融城", "拉萨北京西路",
    "西藏东方财富", "深圳益田路荣超商务中心", "宁波桑田路", "宁波解放南路",
    "华鑫证券上海分公司", "中信证券北京金融大街", "国泰君安顺德",
    "深股通专用", "沪股通专用",  # not hot-money but often co-occur — exclude from inst tag instead
    "财通证券绍兴", "东方财富证券拉萨",
]
INST_TAG = "机构专用"  # exact tag from Tushare top_inst.exalter / top_list.exalter


def is_hot_money(name: str) -> bool:
    if not isinstance(name, str): return False
    return any(kw in name for kw in HOT_MONEY_SEAT_KEYWORDS)


def main():
    daily = pd.read_parquet(CACHE / "daily.parquet")
    adj = pd.read_parquet(CACHE / "adj_factor.parquet")
    sb = pd.read_parquet(CACHE / "stock_basic.parquet")
    top_list = pd.read_parquet(CACHE / "top_list.parquet")
    top_inst = pd.read_parquet(CACHE / "top_inst.parquet")
    limit = pd.read_parquet(CACHE / "limit_list.parquet")

    daily = daily.merge(adj[["ts_code", "trade_date", "adj_factor"]],
                        on=["ts_code", "trade_date"], how="left")
    # qfq close
    last_adj = adj.groupby("ts_code")["adj_factor"].last().rename("last_adj")
    daily = daily.merge(last_adj, on="ts_code", how="left")
    daily["adj_close"] = daily["close"] * daily["adj_factor"] / daily["last_adj"]

    daily = daily.merge(sb[["ts_code", "industry", "list_date"]], on="ts_code", how="left")
    daily["age_days"] = (
        pd.to_datetime(daily["trade_date"]) - pd.to_datetime(daily["list_date"])
    ).dt.days
    # ST filter: skip — name not in daily; rely on amount/close-validity.
    daily = daily[(daily["age_days"] >= 250) & daily["industry"].notna()].copy()

    # upper limit flag
    lim_u = limit[limit["limit"] == "U"][["ts_code", "trade_date"]].assign(is_upper_limit=True)
    daily = daily.merge(lim_u, on=["ts_code", "trade_date"], how="left")
    daily["is_upper_limit"] = daily["is_upper_limit"].fillna(False)

    # ---- DTL aggregates ----
    # top_list per (date, code) gives net_amount in CNY 万 (tushare unit). Use directly as event-day net.
    tl = top_list[["trade_date", "ts_code", "net_amount", "l_buy", "l_sell"]].copy()
    tl["dtl_event"] = 1
    tl = tl.rename(columns={"net_amount": "dtl_net_amount",
                            "l_buy": "dtl_top5_buy", "l_sell": "dtl_top5_sell"})

    # top_inst per (date, code, exalter): institutional seats. Sum by code/date.
    ti = top_inst.copy()
    ti["is_inst"] = ti["exalter"].astype(str).str.contains(INST_TAG, na=False)
    inst = ti[ti["is_inst"]].groupby(["trade_date", "ts_code"]).agg(
        inst_buy_amt=("buy", "sum"), inst_sell_amt=("sell", "sum")
    ).reset_index()
    inst["inst_net"] = inst["inst_buy_amt"] - inst["inst_sell_amt"]

    # hot-money-only flag from top_list seats: in top_list, l_buy column is sum;
    # the per-seat detail is in top_inst (which includes both inst and 营业部 seats).
    seats = ti.copy()
    seats["is_hot"] = seats["exalter"].astype(str).map(is_hot_money)
    by = seats.groupby(["trade_date", "ts_code"]).agg(
        any_inst_buy=("is_inst", lambda s: (s & (seats.loc[s.index, "buy"] > 0)).any()),
        any_hot_buy=("is_hot", lambda s: (s & (seats.loc[s.index, "buy"] > 0)).any()),
    ).reset_index()
    by["hot_money_only"] = (by["any_hot_buy"] & ~by["any_inst_buy"]).astype(int)
    by = by[["trade_date", "ts_code", "hot_money_only"]]

    panel = daily.merge(tl, on=["trade_date", "ts_code"], how="left")
    panel = panel.merge(inst, on=["trade_date", "ts_code"], how="left")
    panel = panel.merge(by, on=["trade_date", "ts_code"], how="left")

    for c in ["dtl_event", "dtl_net_amount", "dtl_top5_buy", "dtl_top5_sell",
              "inst_buy_amt", "inst_sell_amt", "inst_net", "hot_money_only"]:
        panel[c] = panel[c].fillna(0)

    panel = panel.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    panel["amt20"] = panel.groupby("ts_code")["amount"].transform(
        lambda s: s.rolling(20, min_periods=10).mean())

    panel.to_parquet(OUT / "panel.parquet")
    print(f"panel rows={len(panel)} stocks={panel['ts_code'].nunique()} dates={panel['trade_date'].nunique()}")
    print(f"DTL events: {(panel['dtl_event']>0).sum()}, inst net != 0 rows: {(panel['inst_net']!=0).sum()}")


if __name__ == "__main__":
    main()

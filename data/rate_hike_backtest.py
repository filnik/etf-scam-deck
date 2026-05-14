"""
Rate Hike Backtest — "Vendere tutto l'azionario quando la Fed alza i tassi?"

Testa l'ipotesi: durante i rate cycle Fed, conviene uscire dall'azionario
e parcheggiare i soldi altrove (cash / bond / oro / commodities)?

3 cicli storici testati:
1. Greenspan tightening (2004-06): 1% → 5.25%, +425bps in 25 mesi (17 hikes)
2. Yellen/Powell normalization (2015-18): 0.25% → 2.50%, +225bps in 36 mesi (9 hikes)
3. Powell anti-inflation (2022-23): 0.25% → 5.50%, +525bps in 16 mesi (11 hikes)

3 strategie di trigger:
A) "Sell at first hike": vendi SPY al primo aumento, rientra alla fine del cycle
B) "Sell at +50 bps cumulative": vendi quando i tassi sono saliti +50bps dal cycle start
C) "Sell at +100 bps cumulative": idem ma +100bps trigger (più tardivo)
D) "Sell at +150 bps cumulative": ancora più tardivo

5 asset di parking testati:
- BIL/SHY (cash equivalent, 1-3y T-bill)
- IEF (7-10y Treasury)
- TLT (20+y Treasury)
- GLD (oro)
- DBC (commodity broad)
- XLE (energy)
- B&H SPY (benchmark "non fai niente")

Output: rate_hike_data.json
"""

import json
import sys
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"ERROR: missing dependency {e}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# RATE CYCLES (date Fed FOMC ufficiali)
# ============================================================

CYCLES = [
    {
        "id": "greenspan_2004_06",
        "name": "Greenspan Tightening 2004-06",
        "subtitle": "1% → 5,25% · +425 bps in 25 mesi · 17 hikes",
        "start_rate_pct": 1.00,
        "end_rate_pct": 5.25,
        "hikes": [  # (date, new_rate_pct)
            ("2004-06-30", 1.25),
            ("2004-08-10", 1.50),
            ("2004-09-21", 1.75),
            ("2004-11-10", 2.00),
            ("2004-12-14", 2.25),
            ("2005-02-02", 2.50),
            ("2005-03-22", 2.75),
            ("2005-05-03", 3.00),
            ("2005-06-30", 3.25),
            ("2005-08-09", 3.50),
            ("2005-09-20", 3.75),
            ("2005-11-01", 4.00),
            ("2005-12-13", 4.25),
            ("2006-01-31", 4.50),
            ("2006-03-28", 4.75),
            ("2006-05-10", 5.00),
            ("2006-06-29", 5.25),
        ],
        "cycle_end": "2006-08-08",  # last hike + ~6 weeks (start of pause)
    },
    {
        "id": "yellen_powell_2015_18",
        "name": "Yellen-Powell Normalization 2015-18",
        "subtitle": "0,25% → 2,50% · +225 bps in 36 mesi · 9 hikes",
        "start_rate_pct": 0.25,
        "end_rate_pct": 2.50,
        "hikes": [
            ("2015-12-16", 0.50),
            ("2016-12-14", 0.75),
            ("2017-03-15", 1.00),
            ("2017-06-14", 1.25),
            ("2017-12-13", 1.50),
            ("2018-03-21", 1.75),
            ("2018-06-13", 2.00),
            ("2018-09-26", 2.25),
            ("2018-12-19", 2.50),
        ],
        "cycle_end": "2019-07-31",  # first cut after pause
    },
    {
        "id": "powell_2022_23",
        "name": "Powell Anti-Inflation 2022-23",
        "subtitle": "0,25% → 5,50% · +525 bps in 16 mesi · 11 hikes",
        "start_rate_pct": 0.25,
        "end_rate_pct": 5.50,
        "hikes": [
            ("2022-03-17", 0.50),
            ("2022-05-05", 1.00),
            ("2022-06-16", 1.75),
            ("2022-07-28", 2.50),
            ("2022-09-22", 3.25),
            ("2022-11-03", 4.00),
            ("2022-12-15", 4.50),
            ("2023-02-02", 4.75),
            ("2023-03-23", 5.00),
            ("2023-05-04", 5.25),
            ("2023-07-27", 5.50),
        ],
        "cycle_end": "2024-09-18",  # first cut Sept 2024
    },
]


# ============================================================
# ASSET TICKERS
# ============================================================

ASSETS = {
    "SPY":  ("SPY",  "S&P 500"),
    "SHY":  ("SHY",  "1-3y Treasury (cash equiv)"),
    "IEF":  ("IEF",  "7-10y Treasury"),
    "TLT":  ("TLT",  "20+y Treasury"),
    "GLD":  ("GLD",  "Gold"),
    "DBC":  ("DBC",  "Commodity broad"),
    "XLE":  ("XLE",  "Energy sector"),
    "VNQ":  ("VNQ",  "REIT"),
}


# ============================================================
# HELPERS
# ============================================================

def download_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    print(f"  Downloading {ticker} {start}→{end}...", file=sys.stderr)
    df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False, threads=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    out = df[[col]].rename(columns={col: "price"})
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out


def get_price_at(df: pd.DataFrame, target: pd.Timestamp) -> float:
    """Return price at nearest trading day >= target."""
    if df is None or df.empty:
        return None
    available = df.index[df.index >= target]
    if len(available) == 0:
        # fallback: latest available
        return float(df.iloc[-1]["price"])
    return float(df.loc[available[0], "price"])


def find_trigger_date(hikes: list, threshold_bps: int, start_rate_pct: float) -> str:
    """Find the date when cumulative bps from start_rate exceeds threshold."""
    for date_str, new_rate in hikes:
        delta_bps = (new_rate - start_rate_pct) * 100
        if delta_bps >= threshold_bps:
            return date_str
    return None


def calc_return(df: pd.DataFrame, start: str, end: str) -> float:
    """% return between start and end dates (using nearest trading days)."""
    p_start = get_price_at(df, pd.Timestamp(start))
    p_end = get_price_at(df, pd.Timestamp(end))
    if p_start is None or p_end is None:
        return None
    return (p_end - p_start) / p_start * 100


# ============================================================
# RUN BACKTEST
# ============================================================

def run():
    output = {
        "generated_at": date.today().isoformat(),
        "cycles": [],
    }

    for cycle in CYCLES:
        print(f"\n=== {cycle['name']} ===", file=sys.stderr)
        first_hike_date = cycle["hikes"][0][0]
        cycle_end = cycle["cycle_end"]

        # Determine trigger dates for each strategy
        triggers = {
            "first_hike": first_hike_date,
            "delta_50bps": find_trigger_date(cycle["hikes"], 50, cycle["start_rate_pct"]),
            "delta_100bps": find_trigger_date(cycle["hikes"], 100, cycle["start_rate_pct"]),
            "delta_150bps": find_trigger_date(cycle["hikes"], 150, cycle["start_rate_pct"]),
        }

        # Download all assets for the full cycle period
        fetch_start = (pd.Timestamp(first_hike_date) - timedelta(days=30)).strftime("%Y-%m-%d")
        fetch_end = (pd.Timestamp(cycle_end) + timedelta(days=30)).strftime("%Y-%m-%d")

        prices = {}
        for key, (ticker, _label) in ASSETS.items():
            df = download_history(ticker, fetch_start, fetch_end)
            if not df.empty:
                prices[key] = df

        # === Asset returns DURING the cycle (full period) ===
        full_cycle_returns = {}
        for asset_key in prices:
            ret = calc_return(prices[asset_key], first_hike_date, cycle_end)
            if ret is not None:
                full_cycle_returns[asset_key] = round(ret, 2)

        # === Strategy backtest ===
        # For each strategy, sell SPY at trigger, hold parking_asset until cycle_end, re-buy SPY
        # Compute total return = SPY pre-trigger + parking from trigger to cycle_end
        # Compare vs B&H SPY for the full cycle
        bh_spy_return = full_cycle_returns.get("SPY", 0)

        strategies = []
        for strat_key, trigger_date in triggers.items():
            if trigger_date is None:
                continue
            # SPY return from cycle start to trigger
            spy_pre = calc_return(prices["SPY"], first_hike_date, trigger_date) or 0
            for parking_key in prices:
                if parking_key == "SPY":
                    continue
                # Parking return from trigger to cycle_end
                park_ret = calc_return(prices[parking_key], trigger_date, cycle_end)
                if park_ret is None:
                    continue
                # Combined: (1 + spy_pre/100) * (1 + park_ret/100) - 1
                combined = ((1 + spy_pre/100) * (1 + park_ret/100) - 1) * 100
                vs_bh = combined - bh_spy_return
                strategies.append({
                    "strategy": strat_key,
                    "trigger_date": trigger_date,
                    "parking": parking_key,
                    "spy_pre_trigger_pct": round(spy_pre, 2),
                    "parking_post_trigger_pct": round(park_ret, 2),
                    "total_return_pct": round(combined, 2),
                    "vs_bh_spy_pp": round(vs_bh, 2),  # percentage points delta
                })

        cycle_results = {
            "id": cycle["id"],
            "name": cycle["name"],
            "subtitle": cycle["subtitle"],
            "first_hike_date": first_hike_date,
            "cycle_end": cycle_end,
            "start_rate_pct": cycle["start_rate_pct"],
            "end_rate_pct": cycle["end_rate_pct"],
            "triggers": triggers,
            "full_cycle_asset_returns": full_cycle_returns,
            "strategies": strategies,
            "bh_spy_return_pct": round(bh_spy_return, 2),
        }
        output["cycles"].append(cycle_results)

        # Print summary
        print(f"\n  Asset returns durante il cycle ({first_hike_date} → {cycle_end}):", file=sys.stderr)
        sorted_returns = sorted(full_cycle_returns.items(), key=lambda x: -x[1])
        for asset, ret in sorted_returns:
            label = ASSETS[asset][1]
            star = " ★" if asset != "SPY" and ret > full_cycle_returns.get("SPY", 0) else ""
            print(f"    {asset:<5} ({label:<28}): {ret:+7.2f}%{star}", file=sys.stderr)

        # Best strategy per trigger
        print(f"\n  Migliori strategie (vs B&H SPY {bh_spy_return:+.2f}%):", file=sys.stderr)
        for strat_key in ["first_hike", "delta_50bps", "delta_100bps", "delta_150bps"]:
            strat_results = [s for s in strategies if s["strategy"] == strat_key]
            if not strat_results:
                continue
            best = max(strat_results, key=lambda s: s["vs_bh_spy_pp"])
            print(f"    {strat_key:<14} → vendi SPY @ {best['trigger_date']}, parcheggia in {best['parking']:<5} "
                  f"→ {best['total_return_pct']:+7.2f}% ({best['vs_bh_spy_pp']:+.2f}pp vs B&H)", file=sys.stderr)

    # Write JSON
    out_path = Path(__file__).parent / "rate_hike_data.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n✓ Output: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    run()

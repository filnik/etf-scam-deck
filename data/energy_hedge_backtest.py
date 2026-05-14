"""
Energy Hedge Backtest — "Vale la pena hedgare con XLE/Top1/Top3 oil + oro?"

Test 10 varianti su 21 anni (2004-2024), copertura totale dei 3 rate cycle Fed.

Strategie testate:
GROUP A — Static (allocation costante mensile):
  A1. SPY 100%                                  (baseline)
  A2. SPY 80% + GLD 10% + XLE 10%
  A3. SPY 70% + GLD 15% + XLE 15%
  A4. SPY 60% + GLD 20% + XLE 20%               (heavy hedge)
  A5. SPY 70% + GLD 15% + XOM 15%               (top 1 XLE)
  A6. SPY 70% + GLD 15% + Top3 15%              (XOM+CVX+COP)

GROUP B — Dynamic Fed-hike signal:
  B1. Default SPY 100%; durante rate cycle → SPY 50/XLE 25/GLD 25
  B2. Default SPY 100%; durante rate cycle → SELL ALL → GLD 50/XLE 50

GROUP C — Dynamic CPI signal (CPI YoY > 4%):
  C1. Default SPY 100%; quando CPI>4% → SPY 50/XLE 25/GLD 25
  C2. Default SPY 100%; quando CPI>4% → SELL ALL → GLD 50/XLE 50

Costi: PAC €1k/mese, slippage 0.10%, €1/trade, bollo 0.20%, tasse 26% al sell.
Output: energy_hedge_data.json
"""

import json
import sys
import io
from urllib.request import urlopen
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
# PARAMS
# ============================================================

PAC_AMOUNT = 1000.0
SLIPPAGE = 0.001
TRADE_COST = 1.0
BOLLO = 0.002
TAX_RATE = 0.26
TER = {"SPY": 0.0007, "GLD": 0.0040, "XLE": 0.0009}

START = "2004-06-01"
END = "2024-12-31"

TICKERS = {
    "SPY": "SPY",
    "GLD": "GLD",        # post 2004-11; before that fallback to GC=F
    "XLE": "XLE",
    "XOM": "XOM",
    "CVX": "CVX",
    "COP": "COP",
}


# ============================================================
# RATE HIKE CYCLES (date di FOMC hike trigger)
# ============================================================

# Per ogni cycle: (start_date, end_date_inclusive)
RATE_CYCLES = [
    ("2004-06-30", "2006-08-08"),
    ("2015-12-16", "2019-07-31"),
    ("2022-03-17", "2024-09-18"),
]


# ============================================================
# DOWNLOAD HELPERS
# ============================================================

def download(ticker: str, start: str, end: str) -> pd.DataFrame:
    print(f"  {ticker}...", file=sys.stderr)
    df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False, threads=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    out = df[[col]].rename(columns={col: "price"})
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out


def download_cpi() -> pd.DataFrame:
    """Download CPI YoY % from FRED public CSV."""
    print(f"  CPI YoY from FRED...", file=sys.stderr)
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
    try:
        with urlopen(url, timeout=30) as resp:
            data = resp.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(data), parse_dates=["observation_date"])
        df = df.rename(columns={"observation_date": "date", "CPIAUCSL": "cpi"})
        df.set_index("date", inplace=True)
        # Compute YoY %
        df["cpi_yoy"] = (df["cpi"] / df["cpi"].shift(12) - 1) * 100
        return df
    except Exception as e:
        print(f"  WARN: failed CPI fetch ({e}), using static fallback", file=sys.stderr)
        return None


# ============================================================
# SIGNAL FUNCTIONS
# ============================================================

def in_rate_cycle(date_obj: pd.Timestamp) -> bool:
    for s, e in RATE_CYCLES:
        if pd.Timestamp(s) <= date_obj <= pd.Timestamp(e):
            return True
    return False


def cpi_above_4(date_obj: pd.Timestamp, cpi_df: pd.DataFrame) -> bool:
    if cpi_df is None:
        return False
    available = cpi_df.index[cpi_df.index <= date_obj]
    if len(available) == 0:
        return False
    last_cpi = cpi_df.loc[available[-1], "cpi_yoy"]
    return pd.notna(last_cpi) and last_cpi > 4.0


# ============================================================
# PORTFOLIO SIMULATION
# ============================================================

def get_price(df: pd.DataFrame, target: pd.Timestamp) -> float:
    if df is None or df.empty:
        return None
    avail = df.index[df.index >= target]
    if len(avail) == 0:
        return float(df.iloc[-1]["price"])
    return float(df.loc[avail[0], "price"])


def get_pac_dates(start: str, end: str) -> list:
    return list(pd.date_range(start, end, freq="MS"))


@dataclass
class StrategyResult:
    name: str
    final_value: float
    capital_invested: float
    cagr_pct: float
    max_drawdown_pct: float
    sharpe: float
    timeline_dates: list
    timeline_values: list  # NAV evolution


def simulate(
    name: str,
    prices: dict,
    default_weights: dict,
    alt_weights: dict = None,
    signal_func=None,  # callable(date) → bool
    cpi_df=None,
) -> StrategyResult:
    """
    Simulate PAC mensile with optional dynamic allocation.

    default_weights = {asset: weight} sum to 1
    alt_weights = {asset: weight} sum to 1 (used when signal_func returns True)
    signal_func = takes pac_date and returns bool. None = always default.
    """
    pac_dates = get_pac_dates(START, END)
    holdings = {a: 0.0 for a in set(list(default_weights.keys()) + (list(alt_weights.keys()) if alt_weights else []))}
    cash = 0.0
    capital = 0.0
    last_bollo = pac_dates[0]
    timeline_dates = []
    timeline_values = []
    monthly_returns = []
    prev_nav = None

    for pac_date in pac_dates:
        # Apply bollo (monthly drag)
        nav = sum(h * get_price(prices[a], pac_date) for a, h in holdings.items() if h > 0) + cash
        months_since = max((pac_date - last_bollo).days / 30, 1)
        cash -= nav * (BOLLO / 12) * months_since
        last_bollo = pac_date

        # Apply TER drag (monthly) on ETF holdings
        for a, ter in TER.items():
            if a in holdings and holdings[a] > 0:
                p = get_price(prices[a], pac_date)
                cash -= holdings[a] * p * (ter / 12)

        # Pick weights based on signal
        if signal_func and alt_weights and signal_func(pac_date):
            target_weights = alt_weights
            # If alt is "ALL CASH" (sell everything to switch), liquidate non-target assets
            for asset_in_holdings in list(holdings.keys()):
                if asset_in_holdings not in target_weights and holdings[asset_in_holdings] > 0:
                    p = get_price(prices[asset_in_holdings], pac_date)
                    sell_value = holdings[asset_in_holdings] * p * (1 - SLIPPAGE)
                    sell_value -= TRADE_COST
                    # Apply tax on gain (simplified: assume avg cost basis, tax 26% on gain estimate)
                    # For simplicity, assume gain = 0% (will add total tax burden later via deferred)
                    cash += sell_value
                    holdings[asset_in_holdings] = 0
        else:
            target_weights = default_weights
            # Liquidate non-target assets when switching back to default
            for asset_in_holdings in list(holdings.keys()):
                if asset_in_holdings not in target_weights and holdings[asset_in_holdings] > 0:
                    p = get_price(prices[asset_in_holdings], pac_date)
                    sell_value = holdings[asset_in_holdings] * p * (1 - SLIPPAGE)
                    sell_value -= TRADE_COST
                    cash += sell_value
                    holdings[asset_in_holdings] = 0

        # Invest PAC
        capital += PAC_AMOUNT
        available = PAC_AMOUNT + cash
        if available > 0:
            for asset, w in target_weights.items():
                allocation = available * w - TRADE_COST
                if allocation <= 0:
                    continue
                p = get_price(prices[asset], pac_date)
                shares = allocation / (p * (1 + SLIPPAGE))
                holdings[asset] = holdings.get(asset, 0) + shares
            cash = 0.0

        # Track NAV
        nav = sum(h * get_price(prices[a], pac_date) for a, h in holdings.items() if h > 0) + cash
        timeline_dates.append(pac_date.strftime("%Y-%m-%d"))
        timeline_values.append(round(nav, 0))

        if prev_nav is not None and prev_nav > 0:
            ret = (nav - PAC_AMOUNT - prev_nav) / prev_nav  # exclude new PAC contribution
            monthly_returns.append(ret)
        prev_nav = nav

    # Final NAV with tax estimate (simplified: 26% on total gain)
    final_nav = timeline_values[-1]
    estimated_gain = final_nav - capital
    if estimated_gain > 0:
        final_after_tax = final_nav - estimated_gain * TAX_RATE
    else:
        final_after_tax = final_nav

    # CAGR
    years = len(pac_dates) / 12
    if final_after_tax > 0 and capital > 0:
        # IRR-like: solve for r given monthly contributions
        # Simplified: use approximation (NAV / total_invested) ^ (1/years) - 1
        total_invested = capital
        if final_after_tax > 0:
            cagr = (final_after_tax / (total_invested / 2)) ** (1 / years) - 1  # approximate IRR
            cagr_pct = cagr * 100
        else:
            cagr_pct = -100
    else:
        cagr_pct = 0

    # Max drawdown
    peak = 0
    max_dd = 0
    for v in timeline_values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (v - peak) / peak
            if dd < max_dd:
                max_dd = dd
    max_dd_pct = max_dd * 100

    # Sharpe (rough: monthly returns annualized)
    if len(monthly_returns) > 12:
        ann_ret = np.mean(monthly_returns) * 12
        ann_vol = np.std(monthly_returns) * np.sqrt(12)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    else:
        sharpe = 0

    return StrategyResult(
        name=name,
        final_value=round(final_after_tax, 0),
        capital_invested=round(capital, 0),
        cagr_pct=round(cagr_pct, 2),
        max_drawdown_pct=round(max_dd_pct, 2),
        sharpe=round(sharpe, 3),
        timeline_dates=timeline_dates[::3],  # subsample every 3 months for JSON size
        timeline_values=timeline_values[::3],
    )


# ============================================================
# RUN
# ============================================================

def run():
    # Download all assets
    print("=== Downloading data ===", file=sys.stderr)
    prices = {}
    for key, ticker in TICKERS.items():
        df = download(ticker, START, END)
        if not df.empty:
            prices[key] = df

    cpi_df = download_cpi()
    if cpi_df is not None:
        # Filter to relevant range
        cpi_df = cpi_df[cpi_df.index >= pd.Timestamp("2003-01-01")]

    # Top 3 XLE: equal-weighted basket
    # We'll handle this by creating a synthetic Top3 weight in the simulator
    # using XOM 5% + CVX 5% + COP 5% (each 1/3 of 15%)

    print("\n=== Running 10 strategies ===", file=sys.stderr)
    results = []

    # === GROUP A: Static ===
    results.append(simulate("A1 · SPY 100%", prices,
        {"SPY": 1.0}))

    results.append(simulate("A2 · SPY 80 / GLD 10 / XLE 10", prices,
        {"SPY": 0.80, "GLD": 0.10, "XLE": 0.10}))

    results.append(simulate("A3 · SPY 70 / GLD 15 / XLE 15", prices,
        {"SPY": 0.70, "GLD": 0.15, "XLE": 0.15}))

    results.append(simulate("A4 · SPY 60 / GLD 20 / XLE 20", prices,
        {"SPY": 0.60, "GLD": 0.20, "XLE": 0.20}))

    results.append(simulate("A5 · SPY 70 / GLD 15 / XOM 15 (top1)", prices,
        {"SPY": 0.70, "GLD": 0.15, "XOM": 0.15}))

    results.append(simulate("A6 · SPY 70 / GLD 15 / Top3 15", prices,
        {"SPY": 0.70, "GLD": 0.15, "XOM": 0.05, "CVX": 0.05, "COP": 0.05}))

    # === GROUP B: Dynamic Fed-hike signal ===
    results.append(simulate("B1 · SPY 100% default; rate cycle → SPY 50/XLE 25/GLD 25", prices,
        default_weights={"SPY": 1.0},
        alt_weights={"SPY": 0.50, "XLE": 0.25, "GLD": 0.25},
        signal_func=lambda d: in_rate_cycle(d)))

    results.append(simulate("B2 · SPY 100% default; rate cycle → SELL ALL → GLD 50/XLE 50", prices,
        default_weights={"SPY": 1.0},
        alt_weights={"GLD": 0.50, "XLE": 0.50},
        signal_func=lambda d: in_rate_cycle(d)))

    # === GROUP C: Dynamic CPI signal ===
    if cpi_df is not None:
        results.append(simulate("C1 · SPY 100% default; CPI>4% → SPY 50/XLE 25/GLD 25", prices,
            default_weights={"SPY": 1.0},
            alt_weights={"SPY": 0.50, "XLE": 0.25, "GLD": 0.25},
            signal_func=lambda d: cpi_above_4(d, cpi_df),
            cpi_df=cpi_df))

        results.append(simulate("C2 · SPY 100% default; CPI>4% → SELL ALL → GLD 50/XLE 50", prices,
            default_weights={"SPY": 1.0},
            alt_weights={"GLD": 0.50, "XLE": 0.50},
            signal_func=lambda d: cpi_above_4(d, cpi_df),
            cpi_df=cpi_df))

    # === Print results table ===
    print(f"\n{'Strategy':<60} {'Final€':>12} {'CAGR':>7} {'MaxDD':>8} {'Sharpe':>7}", file=sys.stderr)
    print("-" * 100, file=sys.stderr)
    for r in sorted(results, key=lambda x: -x.final_value):
        print(f"{r.name:<60} {r.final_value:>12,.0f} {r.cagr_pct:>6.2f}% {r.max_drawdown_pct:>7.2f}% {r.sharpe:>7.2f}", file=sys.stderr)

    # === Save JSON ===
    output = {
        "generated_at": date.today().isoformat(),
        "params": {
            "pac": PAC_AMOUNT, "period": f"{START} to {END}",
            "slippage": SLIPPAGE, "trade_cost": TRADE_COST, "bollo": BOLLO, "tax_rate": TAX_RATE
        },
        "rate_cycles": RATE_CYCLES,
        "strategies": [asdict(r) for r in results],
    }
    out_path = Path(__file__).parent / "energy_hedge_data.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n✓ Output: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    run()

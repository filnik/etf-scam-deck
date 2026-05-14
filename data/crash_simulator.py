"""
Crash Test Simulator — "Gli ETF sono SCAM?" video deck

Simula 4 crash storici × 3 portfolio × 2 entry timing = 24 simulazioni PAC realistiche.

Crash:
1. Dot-com bubble  (peak 2000-03-24 → trough 2002-10-09)
2. GFC 2008        (peak 2007-10-31 → trough 2008-11-20)
3. Memory Glut '18 (peak 2018-03-12 → trough 2018-12-24)
4. Rate Hike 2022  (peak 2021-12-27 → trough 2022-10-13)

Portfolio:
A. SPY PAC puro
B. P/E Switch + oro (proxy: 85% top tech + 15% gold + TS-15%)
C. NVDA + AVGO + 15% oro PAC fisso (pre-2009-08: solo NVDA + 15% oro)

Costi realistici Italia (regime dichiarativo):
- Slippage 0.10% per trade
- Costo €1/trade fixed
- Bollo 0.20% annuo su NAV
- Tasse 26% capital gain (al sell)
- TER 0.07% SPY, 0.40% GLD (drag annuo)

Output: crash_data.json consumato dal slide deck.

NOTE: questo script è standalone (fuori dal progetto investing).
Usa yfinance direttamente. Run one-shot.
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
    print(f"ERROR: missing dependency {e}. Run: pip install yfinance pandas numpy", file=sys.stderr)
    sys.exit(1)


# ============================================================
# CRASH DEFINITIONS
# ============================================================

CRASHES = [
    {
        "id": "dotcom",
        "name": "Dot-com Bubble",
        "subtitle": "La fine dell'illusione internet (2000-2002)",
        "peak_date": "2000-03-24",
        "trough_date": "2002-10-09",
        "duration_months": 31,
        "shape": "Slow grind, 31 mesi di discesa",
        "trigger": "Inflazione valuation tech, Greenspan rate hike, NASDAQ −78%, SPY −49%",
        "avgo_available": False,
    },
    {
        "id": "gfc2008",
        "name": "Global Financial Crisis",
        "subtitle": "Lehman Brothers + collasso credito (2007-2009)",
        "peak_date": "2007-10-31",
        "trough_date": "2008-11-20",
        "duration_months": 13,
        "shape": "V-shape concentrato (70% del DD in 6 settimane Sept-Oct '08)",
        "trigger": "Subprime + Lehman fail + freeze interbancario, VIX peak 80",
        "avgo_available": False,
    },
    {
        "id": "memory2018",
        "name": "Memory Glut + Trade War",
        "subtitle": "Eccesso capacità DRAM/NAND + tariffe USA-Cina (2018)",
        "peak_date": "2018-03-12",
        "trough_date": "2018-12-24",
        "duration_months": 9,
        "shape": "Crash interno al settore semi (NAND/DRAM down -40%)",
        "trigger": "Sovrapproduzione memory + Trump tariffs + Fed rate hikes",
        "avgo_available": True,
    },
    {
        "id": "rate2022",
        "name": "Rate Hike + Post-COVID",
        "subtitle": "Inflazione + Fed pivot hawkish (2021-2022)",
        "peak_date": "2021-12-27",
        "trough_date": "2022-10-13",
        "duration_months": 10,
        "shape": "Bear esteso 10 mesi + bond crash simultaneo (60/40 -17%)",
        "trigger": "CPI 9% + Fed funds 0% → 5%, growth stocks repricing",
        "avgo_available": True,
    },
]


# ============================================================
# COST PARAMETERS (Italia regime dichiarativo)
# ============================================================

PAC_AMOUNT_EUR = 1000.0          # PAC mensile €1k
SLIPPAGE = 0.001                  # 0.10% per trade
TRADE_COST = 1.0                  # €1 fissi per trade (BG Saxo)
BOLLO_ANNUAL = 0.002              # 0.20% su NAV (Italia)
TAX_RATE = 0.26                   # 26% capital gain
TER_SPY = 0.0007                  # 0.07% TER SPY annuo
TER_GLD = 0.0040                  # 0.40% TER GLD annuo
LATE_EXIT_EXTRA_LOSS = 0.04       # 4% extra peggio del trough (esci 1 settimana dopo)


# ============================================================
# YFINANCE TICKERS
# ============================================================

TICKERS = {
    "SPY": "SPY",          # S&P 500 ETF (since 1993)
    "NVDA": "NVDA",        # since 1999-01
    "AVGO": "AVGO",        # since 2009-08
    "GLD": "GLD",          # since 2004-11
    "GOLD_SPOT": "GC=F",   # gold futures (proxy pre-GLD)
    "QQQ": "QQQ",          # since 1999
    "AAPL": "AAPL",
    "GOOGL": "GOOGL",      # since 2004
    "MSFT": "MSFT",
}


def download_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download daily history; returns DataFrame with Adj Close indexed by date."""
    print(f"  Downloading {ticker} from {start} to {end}...", file=sys.stderr)
    df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False, threads=False)
    if df.empty:
        return pd.DataFrame()
    # Handle MultiIndex (yfinance multi-ticker behavior)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if "Adj Close" in df.columns:
        out = df[["Adj Close"]].rename(columns={"Adj Close": "price"})
    else:
        out = df[["Close"]].rename(columns={"Close": "price"})
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out


def get_gold_series(start: str, end: str) -> pd.DataFrame:
    """Use GLD post-2004-11, fallback to GC=F futures pre-2004."""
    start_dt = pd.Timestamp(start)
    gld_inception = pd.Timestamp("2004-11-18")
    if start_dt >= gld_inception:
        return download_history("GLD", start, end)
    # Use gold spot futures
    print(f"  Using GC=F gold spot for pre-2004 period...", file=sys.stderr)
    return download_history("GC=F", start, end)


# ============================================================
# PORTFOLIO SIMULATION
# ============================================================

@dataclass
class SimResult:
    portfolio: str          # "SPY", "PESwitch", "NoRot2"
    entry_offset: str       # "1y_before" or "1m_before"
    capital_invested: float
    peak_value: float
    peak_gain_pct: float
    trough_value: float
    trough_gain_pct: float
    drawdown_pct: float
    late_exit_value: float
    late_exit_gain_pct: float
    timeline_dates: list    # for chart
    timeline_values: list   # portfolio value % vs starting capital


def get_pac_dates(start: pd.Timestamp, end: pd.Timestamp) -> list:
    """Returns list of monthly PAC dates (1st trading day of each month)."""
    dates = pd.date_range(start, end, freq="MS").tolist()
    # tz-aware safety
    dates = [pd.Timestamp(d) for d in dates]
    return dates


def nearest_trading_day(target: pd.Timestamp, prices: pd.DataFrame) -> pd.Timestamp:
    """Find nearest trading day in prices index >= target."""
    available = prices.index[prices.index >= target]
    if len(available) == 0:
        return prices.index[-1]
    return available[0]


def get_price(prices: pd.DataFrame, target: pd.Timestamp) -> float:
    """Get price at nearest trading day >= target."""
    actual = nearest_trading_day(target, prices)
    return float(prices.loc[actual, "price"])


def simulate_pac(
    prices_dict: dict,           # {asset: pd.DataFrame}
    weights: dict,                # {asset: weight} sum to 1
    start: pd.Timestamp,
    peak_date: pd.Timestamp,
    trough_date: pd.Timestamp,
    portfolio_name: str,
    entry_label: str,
    apply_ter: dict = None,       # {asset: ter}
    apply_ts15: bool = False,     # trailing stop -15%
) -> SimResult:
    """
    Simulate PAC mensile:
    - Each month, buy weights[asset] * (PAC - trade_cost) of each asset (at price + slippage)
    - Track holdings
    - At each PAC: apply bollo to existing NAV (annualized to monthly)
    - At each PAC: apply TER drag to ETF holdings (annualized monthly)
    - If apply_ts15 and asset (e.g. NVDA) is -15% from peak monthly close, sell to cash for 1 month
    - Compute peak_value (just before peak_date), trough_value (at trough_date), late_exit (trough +4%)
    - Output also timeline (date, total_value%) for chart
    """
    pac_dates = get_pac_dates(start, trough_date + timedelta(days=14))
    apply_ter = apply_ter or {}

    # Holdings: {asset: shares}
    holdings = {asset: 0.0 for asset in weights}
    cash = 0.0
    capital_invested = 0.0
    last_bollo_date = pac_dates[0]
    peak_check_for_ts = {}  # {asset: peak_price}
    ts_active_until = pd.Timestamp.min  # if TS triggered, no buy until this date

    timeline_dates = []
    timeline_values = []

    # Snapshots captured during loop (correct: holdings as of those dates only)
    peak_snapshot = {"value": 0.0, "capital": 0.0}      # NAV at official crash peak date
    trough_snapshot = {"value": 0.0, "capital": 0.0}    # NAV at official trough date
    running_max_nav = 0.0                                # max NAV ever reached
    running_max_capital = 0.0
    running_min_nav_after_max = float('inf')             # min NAV after the running max

    for pac_date in pac_dates:
        if pac_date > trough_date + timedelta(days=14):
            break

        # Apply bollo on NAV (monthly)
        nav_now = compute_nav(holdings, prices_dict, pac_date) + cash
        months_since_bollo = max((pac_date - last_bollo_date).days / 30, 1)
        bollo_charge = nav_now * (BOLLO_ANNUAL / 12) * months_since_bollo
        cash -= bollo_charge
        last_bollo_date = pac_date

        # Apply TER drag on ETF holdings
        for asset, ter in apply_ter.items():
            if asset in holdings and holdings[asset] > 0:
                price = get_price(prices_dict[asset], pac_date)
                ter_charge = holdings[asset] * price * (ter / 12)
                # Cash decrement (TER is implicit in NAV, but we model as cash drag for simplicity)
                cash -= ter_charge

        # Check trailing stop (only on tech assets, not gold)
        if apply_ts15 and pac_date > ts_active_until:
            for asset, w in weights.items():
                if asset in ("NVDA", "TECH_BASKET", "AVGO", "AAPL", "GOOGL", "MSFT"):
                    if holdings.get(asset, 0) > 0:
                        cur_price = get_price(prices_dict[asset], pac_date)
                        peak_price = peak_check_for_ts.get(asset, cur_price)
                        peak_check_for_ts[asset] = max(peak_price, cur_price)
                        # If down >15% from peak, sell all to cash
                        if cur_price < peak_check_for_ts[asset] * 0.85:
                            sell_value = holdings[asset] * cur_price * (1 - SLIPPAGE)
                            sell_value -= TRADE_COST
                            cash += sell_value
                            holdings[asset] = 0
                            peak_check_for_ts[asset] = 0
                            ts_active_until = pac_date + timedelta(days=30)

        # PAC investment
        if pac_date <= ts_active_until:
            # Skip buying during TS lockout, accumulate cash
            cash += PAC_AMOUNT_EUR
            capital_invested += PAC_AMOUNT_EUR
        else:
            capital_invested += PAC_AMOUNT_EUR
            available = PAC_AMOUNT_EUR + cash  # use accumulated cash too if any
            # If TS just expired and we have lump cash, redeploy
            for asset, w in weights.items():
                allocation = available * w - TRADE_COST  # subtract trade cost per asset
                if allocation <= 0:
                    continue
                price = get_price(prices_dict[asset], pac_date)
                effective_price = price * (1 + SLIPPAGE)
                shares = allocation / effective_price
                holdings[asset] += shares
                # Update peak tracker on buy
                peak_check_for_ts[asset] = max(peak_check_for_ts.get(asset, price), price)
            cash = 0.0  # fully deployed

        # Track timeline
        nav_now = compute_nav(holdings, prices_dict, pac_date) + cash
        gain_pct = (nav_now - capital_invested) / max(capital_invested, 1) * 100
        timeline_dates.append(pac_date.strftime("%Y-%m-%d"))
        timeline_values.append(round(gain_pct, 2))

        # Track running max NAV (the actual portfolio peak)
        if nav_now > running_max_nav:
            running_max_nav = nav_now
            running_max_capital = capital_invested
            running_min_nav_after_max = float('inf')  # reset min tracker

        # Track min NAV after max (for drawdown)
        if nav_now < running_min_nav_after_max:
            running_min_nav_after_max = nav_now

        # Capture peak snapshot when we cross peak_date (NAV at official crash peak)
        if peak_snapshot["value"] == 0 and pac_date >= peak_date:
            peak_value_at_date = compute_nav(holdings, prices_dict, peak_date) + cash
            peak_snapshot["value"] = peak_value_at_date
            peak_snapshot["capital"] = capital_invested

        # Capture trough snapshot when we cross trough_date
        if trough_snapshot["value"] == 0 and pac_date >= trough_date:
            trough_value_calc = compute_nav(holdings, prices_dict, trough_date) + cash
            trough_snapshot["value"] = trough_value_calc
            trough_snapshot["capital"] = capital_invested

    # === METRICS based on gain % vs capital (timeline_values) ===
    # This is the cleanest narrative metric: "what did the user SEE?"
    # peak_gain_pct = highest gain% reached at or before peak_date
    # trough_gain_pct = lowest gain% reached at or after peak_date
    # drawdown_pp = peak_gain_pct - trough_gain_pct (percentage POINTS, not %)

    # Find peak_date index in timeline (last entry on or before peak_date)
    peak_idx = -1
    for i, d_str in enumerate(timeline_dates):
        if pd.Timestamp(d_str) <= peak_date:
            peak_idx = i
        else:
            break

    if peak_idx < 0:
        peak_idx = 0  # safety

    pre_peak_values = timeline_values[: peak_idx + 1]
    post_peak_values = timeline_values[peak_idx:]  # include peak point

    peak_gain_pct = max(pre_peak_values) if pre_peak_values else 0.0
    trough_gain_pct = min(post_peak_values) if post_peak_values else peak_gain_pct
    drawdown_pp = peak_gain_pct - trough_gain_pct  # in percentage POINTS

    # Late exit: gain % drops by 4pp more (you exit 1 week after the bottom)
    # Approximate: trough_gain_pct - 4pp, then tax on gain if positive
    late_exit_gain_pct_pretax = trough_gain_pct - LATE_EXIT_EXTRA_LOSS * 100
    if late_exit_gain_pct_pretax > 0:
        # Apply 26% tax to the gain portion
        late_exit_gain_pct = late_exit_gain_pct_pretax * (1 - TAX_RATE)
    else:
        late_exit_gain_pct = late_exit_gain_pct_pretax  # losses not taxed

    # Resolve raw values for display (informational, not used for metrics)
    capital_at_trough = trough_snapshot["capital"] or capital_invested
    trough_value = trough_snapshot["value"] or (compute_nav(holdings, prices_dict, trough_date) + cash)

    # Peak value = max NAV reached pre-peak_date
    peak_value = running_max_nav if running_max_nav > 0 else (peak_snapshot["value"] or trough_value)
    capital_at_peak = running_max_capital if running_max_nav > 0 else (peak_snapshot["capital"] or capital_at_trough)

    # Late exit value in EUR (for display)
    late_exit_value = capital_at_trough * (1 + late_exit_gain_pct / 100)

    # Add drawdown_pp as the headline drawdown metric
    drawdown_pct = drawdown_pp  # rename for backward-compat in output

    return SimResult(
        portfolio=portfolio_name,
        entry_offset=entry_label,
        capital_invested=round(capital_at_trough, 0),
        peak_value=round(peak_value, 0),
        peak_gain_pct=round(peak_gain_pct, 2),
        trough_value=round(trough_value, 0),
        trough_gain_pct=round(trough_gain_pct, 2),
        drawdown_pct=round(drawdown_pct, 2),
        late_exit_value=round(late_exit_value, 0),
        late_exit_gain_pct=round(late_exit_gain_pct, 2),
        timeline_dates=timeline_dates,
        timeline_values=timeline_values,
    )


def compute_nav(holdings: dict, prices_dict: dict, target_date: pd.Timestamp) -> float:
    """Sum (shares * price) across all assets at target_date."""
    total = 0.0
    for asset, shares in holdings.items():
        if shares > 0:
            price = get_price(prices_dict[asset], target_date)
            total += shares * price
    return total


# ============================================================
# RUN ALL SIMULATIONS
# ============================================================

def run_all():
    output = {
        "generated_at": date.today().isoformat(),
        "params": {
            "pac_eur": PAC_AMOUNT_EUR,
            "slippage": SLIPPAGE,
            "trade_cost_eur": TRADE_COST,
            "bollo_annual": BOLLO_ANNUAL,
            "tax_rate": TAX_RATE,
            "ter_spy": TER_SPY,
            "ter_gld": TER_GLD,
            "late_exit_extra_loss": LATE_EXIT_EXTRA_LOSS,
        },
        "crashes": [],
    }

    for crash in CRASHES:
        print(f"\n=== {crash['name']} ===", file=sys.stderr)
        peak = pd.Timestamp(crash["peak_date"])
        trough = pd.Timestamp(crash["trough_date"])

        # Determine data fetch window
        # Need: 1y before peak (T1) to 30 days after trough
        fetch_start = (peak - timedelta(days=400)).strftime("%Y-%m-%d")
        fetch_end = (trough + timedelta(days=30)).strftime("%Y-%m-%d")

        # Download all needed assets
        prices_dict = {}
        prices_dict["SPY"] = download_history("SPY", fetch_start, fetch_end)
        prices_dict["NVDA"] = download_history("NVDA", fetch_start, fetch_end)
        prices_dict["GOLD"] = get_gold_series(fetch_start, fetch_end)

        if crash["avgo_available"]:
            prices_dict["AVGO"] = download_history("AVGO", fetch_start, fetch_end)

        # P/E Switch tech basket: use NVDA pre-2010 / AAPL+GOOGL+NVDA+MSFT post-2010
        # Simplification: weighted avg of NVDA + (AAPL if available) + (GOOGL if available)
        if peak.year >= 2010:
            prices_dict["AAPL"] = download_history("AAPL", fetch_start, fetch_end)
            if peak.year >= 2005:  # GOOGL IPO 2004
                prices_dict["GOOGL"] = download_history("GOOGL", fetch_start, fetch_end)
            prices_dict["MSFT"] = download_history("MSFT", fetch_start, fetch_end)

        # ============ Run simulations for this crash ============

        crash_results = {
            "id": crash["id"],
            "name": crash["name"],
            "subtitle": crash["subtitle"],
            "peak_date": crash["peak_date"],
            "trough_date": crash["trough_date"],
            "duration_months": crash["duration_months"],
            "shape": crash["shape"],
            "trigger": crash["trigger"],
            "avgo_available": crash["avgo_available"],
            "scenarios": [],
        }

        for entry_label, days_before in [("1y_before", 365), ("1m_before", 30)]:
            entry_date = peak - timedelta(days=days_before)

            # Portfolio A: SPY puro
            res_a = simulate_pac(
                prices_dict={"SPY": prices_dict["SPY"]},
                weights={"SPY": 1.0},
                start=entry_date,
                peak_date=peak,
                trough_date=trough,
                portfolio_name="SPY",
                entry_label=entry_label,
                apply_ter={"SPY": TER_SPY},
                apply_ts15=False,
            )
            crash_results["scenarios"].append(asdict(res_a))

            # Portfolio B: P/E Switch proxy = 85% top tech + 15% gold + TS-15%
            # Pre-2005: 85% NVDA + 15% gold (no fundamentals data for true P/E switch)
            # Post-2010: 21.25% NVDA + 21.25% AAPL + 21.25% GOOGL (if available) + 21.25% MSFT + 15% gold
            if peak.year >= 2010 and "GOOGL" in prices_dict:
                tech_assets = ["NVDA", "AAPL", "GOOGL", "MSFT"]
                tech_weight_each = 0.85 / len(tech_assets)
                weights_b = {a: tech_weight_each for a in tech_assets}
                weights_b["GOLD"] = 0.15
            else:
                # Pre-2010: simplified to NVDA + gold
                weights_b = {"NVDA": 0.85, "GOLD": 0.15}

            res_b = simulate_pac(
                prices_dict=prices_dict,
                weights=weights_b,
                start=entry_date,
                peak_date=peak,
                trough_date=trough,
                portfolio_name="PESwitch",
                entry_label=entry_label,
                apply_ter={"GOLD": TER_GLD},
                apply_ts15=True,
            )
            crash_results["scenarios"].append(asdict(res_b))

            # Portfolio C: NVDA + AVGO + 15% gold (PAC fisso, no rotation)
            if crash["avgo_available"]:
                weights_c = {"NVDA": 0.425, "AVGO": 0.425, "GOLD": 0.15}
            else:
                weights_c = {"NVDA": 0.85, "GOLD": 0.15}

            res_c = simulate_pac(
                prices_dict=prices_dict,
                weights=weights_c,
                start=entry_date,
                peak_date=peak,
                trough_date=trough,
                portfolio_name="NoRot2",
                entry_label=entry_label,
                apply_ter={"GOLD": TER_GLD},
                apply_ts15=False,  # PAC fisso, zero rotazioni
            )
            crash_results["scenarios"].append(asdict(res_c))

            # Portfolio D: NVDA + AVGO + 15% gold + TS-15% (versione protetta)
            res_d = simulate_pac(
                prices_dict=prices_dict,
                weights=weights_c,  # stesso pool di C
                start=entry_date,
                peak_date=peak,
                trough_date=trough,
                portfolio_name="NoRot2_TS",
                entry_label=entry_label,
                apply_ter={"GOLD": TER_GLD},
                apply_ts15=True,  # con trailing stop −15%
            )
            crash_results["scenarios"].append(asdict(res_d))

        output["crashes"].append(crash_results)

        # Print summary
        print(f"\n  Summary {crash['name']}:", file=sys.stderr)
        for s in crash_results["scenarios"]:
            print(f"    {s['portfolio']:10} {s['entry_offset']:11} | "
                  f"peak gain {s['peak_gain_pct']:+7.1f}% | "
                  f"DD {s['drawdown_pct']:+7.1f}% | "
                  f"late exit {s['late_exit_gain_pct']:+7.1f}% | "
                  f"final €{s['late_exit_value']:>12,.0f}", file=sys.stderr)

    # Write JSON
    out_path = Path(__file__).parent / "crash_data.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n✓ Output written to {out_path}", file=sys.stderr)
    print(f"  Total crashes: {len(output['crashes'])}", file=sys.stderr)
    total_scenarios = sum(len(c["scenarios"]) for c in output["crashes"])
    print(f"  Total scenarios: {total_scenarios}", file=sys.stderr)


if __name__ == "__main__":
    run_all()

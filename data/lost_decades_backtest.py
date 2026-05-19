"""
Lost Decades Backtest — "Il mercato sale sempre? Falso. Ma non mollare al fondo."

Due tesi in un colpo:

1. LE LOST DECADES ESISTONO. In termini REALI (aggiustati per inflazione)
   l'S&P 500 ha avuto due stretch da oltre un decennio in cui non è andato
   da nessuna parte:
   - 1966-1982 (17 anni): stagflazione. Nominale ~piatto, CPI ×3 → reale -51%.
   - 2000-2013 (14 anni): dot-com bust + GFC. Due crash da -50% nel decennio.

2. MA CHI HA TENUTO DURO È STATO PREMIATO. Lo stesso PAC, continuato OLTRE
   il fondo della lost decade (le quote comprate a sconto durante la crisi
   esplodono nella recovery):
   - 1966 → 2000: il PAC che ha attraversato la stagflazione e il bull 1982-2000.
   - 2000 → 2024: il PAC che ha attraversato i due crash e il bull successivo.

Per ogni periodo calcola la finestra "lost decade" (brutale) E la finestra
"estesa" (stayed the course), entrambe nominale + reale, PAC + lump-sum.

Dati: ^GSPC da yfinance (price-only, copre dal 1960) + CPI-U annuale hardcoded
(BLS, 1982-84=100), interpolato a mensile. Price-only → stima conservativa
(i dividendi reinvestiti renderebbero il PAC ancora migliore).

Output: lost_decades_data.json
"""

import json
import sys
from datetime import date
from pathlib import Path

try:
    import yfinance as yf
    import pandas as pd
except ImportError as e:
    print(f"ERROR: missing dependency {e}", file=sys.stderr)
    sys.exit(1)


# CPI-U annuale (BLS, base 1982-84 = 100). Media annua.
CPI_ANNUAL = {
    1965: 31.5, 1966: 32.4, 1967: 33.4, 1968: 34.8, 1969: 36.7,
    1970: 38.8, 1971: 40.5, 1972: 41.8, 1973: 44.4, 1974: 49.3,
    1975: 53.8, 1976: 56.9, 1977: 60.6, 1978: 65.2, 1979: 72.6,
    1980: 82.4, 1981: 90.9, 1982: 96.5, 1983: 99.6, 1984: 103.9,
    1985: 107.6, 1986: 109.6, 1987: 113.6, 1988: 118.3, 1989: 124.0,
    1990: 130.7, 1991: 136.2, 1992: 140.3, 1993: 144.5, 1994: 148.2,
    1995: 152.4, 1996: 156.9, 1997: 160.5, 1998: 163.0, 1999: 166.6,
    2000: 172.2, 2001: 177.1, 2002: 179.9, 2003: 184.0, 2004: 188.9,
    2005: 195.3, 2006: 201.6, 2007: 207.342, 2008: 215.303, 2009: 214.537,
    2010: 218.056, 2011: 224.939, 2012: 229.594, 2013: 232.957, 2014: 236.736,
    2015: 237.017, 2016: 240.007, 2017: 245.120, 2018: 251.107, 2019: 255.657,
    2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702, 2024: 313.689,
    2025: 322.0,
}

PERIODS = [
    {
        "id": "stagflation_1966",
        "name": "1966-1982 · La stagflazione",
        "subtitle": "Vietnam, shock petroliferi, inflazione a doppia cifra",
        "start": "1966-01-01",
        "lost_decade_end": "1982-12-31",
        "extended_end": "2000-01-01",
    },
    {
        "id": "lost_2000",
        "name": "2000-2013 · Il decennio perduto",
        "subtitle": "dot-com bust + GFC · due crash da -50% nello stesso decennio",
        "start": "2000-01-01",
        "lost_decade_end": "2013-12-31",
        "extended_end": "2024-12-31",
    },
]

MONTHLY_PAC = 1000.0


def download_gspc() -> pd.DataFrame:
    print("  Downloading ^GSPC 1965→2025...", file=sys.stderr)
    df = yf.download("^GSPC", start="1965-01-01", end="2025-12-31",
                     auto_adjust=False, progress=False, threads=False)
    if df.empty:
        sys.exit("ERROR: ^GSPC download empty")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    out = df[["Close"]].rename(columns={"Close": "price"})
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out


def cpi_at(ts: pd.Timestamp) -> float:
    year = ts.year
    frac = (ts.month - 1) / 12.0
    c0 = CPI_ANNUAL.get(year)
    c1 = CPI_ANNUAL.get(year + 1, c0)
    if c0 is None:
        c0 = c1 = CPI_ANNUAL[min(CPI_ANNUAL)] if year < min(CPI_ANNUAL) else CPI_ANNUAL[max(CPI_ANNUAL)]
    return c0 + (c1 - c0) * frac


def monthly_series(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    sub = df.loc[start:end]
    monthly = sub.resample("MS").first().dropna()
    monthly["cpi"] = [cpi_at(ts) for ts in monthly.index]
    return monthly


def window_stats(m: pd.DataFrame) -> dict:
    """Stats per una finestra: return nominale/reale + PAC + lump-sum."""
    prices = m["price"].values
    cpi = m["cpi"].values
    n = len(m)
    p0, p_end, cpi0, cpi_end = prices[0], prices[-1], cpi[0], cpi[-1]
    years = round((m.index[-1] - m.index[0]).days / 365.25, 1)

    nominal_ret = (p_end / p0 - 1) * 100
    real_ret = (p_end * (cpi0 / cpi_end) / p0 - 1) * 100

    total_invested = MONTHLY_PAC * n
    pac_units = sum(MONTHLY_PAC / prices[i] for i in range(n))
    pac_nom = pac_units * p_end
    pac_real = pac_nom * (cpi0 / cpi_end)
    lump_units = total_invested / p0
    lump_nom = lump_units * p_end
    lump_real = lump_nom * (cpi0 / cpi_end)

    return {
        "years": years,
        "months": n,
        "nominal_return_pct": round(nominal_ret, 1),
        "real_return_pct": round(real_ret, 1),
        "inflation_multiple": round(cpi_end / cpi0, 2),
        "pac": {
            "total_invested": round(total_invested),
            "final_nominal": round(pac_nom),
            "final_real": round(pac_real),
            "real_multiple": round(pac_real / total_invested, 2),
        },
        "lump_sum": {
            "total_invested": round(total_invested),
            "final_nominal": round(lump_nom),
            "final_real": round(lump_real),
            "real_multiple": round(lump_real / total_invested, 2),
        },
    }


def run_period(df: pd.DataFrame, period: dict) -> dict:
    # finestra estesa (contiene anche la lost decade)
    m_ext = monthly_series(df, period["start"], period["extended_end"])
    prices = m_ext["price"].values
    cpi = m_ext["cpi"].values
    dates = [ts.strftime("%Y-%m-%d") for ts in m_ext.index]
    p0, cpi0 = prices[0], cpi[0]
    n = len(m_ext)

    # indice in cui finisce la "lost decade"
    ld_end_ts = pd.Timestamp(period["lost_decade_end"])
    ld_idx = max(i for i in range(n) if m_ext.index[i] <= ld_end_ts)

    lost = window_stats(m_ext.iloc[: ld_idx + 1])
    extended = window_stats(m_ext)

    # timeline per i chart
    real_index = [round(prices[i] * (cpi0 / cpi[i]) / p0 * 100, 1) for i in range(n)]
    pac_value, pac_value_real, cum_units = [], [], 0.0
    for i in range(n):
        cum_units += MONTHLY_PAC / prices[i]
        pac_value.append(round(cum_units * prices[i]))
        pac_value_real.append(round(cum_units * prices[i] * (cpi0 / cpi[i])))

    return {
        "id": period["id"],
        "name": period["name"],
        "subtitle": period["subtitle"],
        "start": period["start"],
        "lost_decade_end": period["lost_decade_end"],
        "extended_end": period["extended_end"],
        "lost_decade": lost,
        "extended": extended,
        "timeline": {
            "dates": dates,
            "real_index": real_index,
            "pac_value": pac_value,
            "pac_value_real": pac_value_real,
            "lost_decade_end_idx": ld_idx,
        },
    }


def run():
    df = download_gspc()
    output = {
        "generated_at": date.today().isoformat(),
        "source": "^GSPC (yfinance, price-only) + CPI-U BLS annuale interpolato",
        "monthly_pac_eur": MONTHLY_PAC,
        "periods": [],
    }

    for period in PERIODS:
        print(f"\n=== {period['name']} ===", file=sys.stderr)
        res = run_period(df, period)
        output["periods"].append(res)
        ld, ext = res["lost_decade"], res["extended"]

        print(f"  --- LOST DECADE ({res['start']} → {res['lost_decade_end']}, {ld['years']}y) ---", file=sys.stderr)
        print(f"    Return nominale: {ld['nominal_return_pct']:+.1f}%  |  reale: {ld['real_return_pct']:+.1f}%  (inflazione ×{ld['inflation_multiple']})", file=sys.stderr)
        print(f"    PAC €1k/mese (invest. €{ld['pac']['total_invested']:,}): finale reale €{ld['pac']['final_real']:,}  (×{ld['pac']['real_multiple']})", file=sys.stderr)
        print(f"    'Se molli al fondo' → hai ×{ld['pac']['real_multiple']} sul potere d'acquisto", file=sys.stderr)
        print(f"  --- STAYED THE COURSE ({res['start']} → {res['extended_end']}, {ext['years']}y) ---", file=sys.stderr)
        print(f"    Return nominale: {ext['nominal_return_pct']:+.1f}%  |  reale: {ext['real_return_pct']:+.1f}%", file=sys.stderr)
        print(f"    PAC €1k/mese (invest. €{ext['pac']['total_invested']:,}): finale reale €{ext['pac']['final_real']:,}  (×{ext['pac']['real_multiple']})", file=sys.stderr)
        edge = ext['pac']['real_multiple'] / ld['pac']['real_multiple'] if ld['pac']['real_multiple'] else 0
        print(f"    → chi ha tenuto duro ha fatto ×{edge:.1f} meglio di chi ha mollato al fondo", file=sys.stderr)

    out_path = Path(__file__).parent / "lost_decades_data.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n✓ Output: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    run()

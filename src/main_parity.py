import argparse
import os
from typing import List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from parity.data import (
    get_spot_and_dividends, get_rf_irx, list_expiries, load_option_chain,
    time_to_expiry_years, pv_of_dividends, _now_utc_naive
)
from parity.parity import compute_row

def parse_args():
    p = argparse.ArgumentParser(description="Put–Call Parity Checker")
    p.add_argument("--ticker", required=True, type=str, help="Underlying ticker (e.g., SPY, AAPL)")
    p.add_argument("--expiries", nargs="*", help="Explicit expiries (YYYY-MM-DD). If omitted, use DTE window.")
    p.add_argument("--min_dte", type=int, default=7, help="Minimum days to expiry (auto mode)")
    p.add_argument("--max_dte", type=int, default=120, help="Maximum days to expiry (auto mode)")
    p.add_argument("--use_dividends", action="store_true", help="Include PV(dividends) until expiry")
    p.add_argument("--rf_override", type=float, default=None, help="Annual risk-free rate override (e.g., 0.045)")
    p.add_argument("--stock_spread_cents", type=float, default=1.0, help="Assumed stock bid-ask spread (cents)")
    p.add_argument("--plots", action="store_true", help="Save plots")
    return p.parse_args()

def choose_expiries(ticker: str, expiries: Optional[List[str]], min_dte: int, max_dte: int) -> List[str]:
    if expiries:
        return expiries
    all_exps = list_expiries(ticker)
    now = _now_utc_naive()
    kept = []
    for e in all_exps:
        dte = (pd.to_datetime(e).to_pydatetime() - now).days
        if dte >= min_dte and dte <= max_dte:
            kept.append(e)
    return kept[:20]

def process_expiry(ticker: str, expiry: str, spot: float, rf: float, div_series: pd.Series,
                   use_dividends: bool, stock_spread_cents: float, out_dir: str) -> pd.DataFrame:
    calls, puts = load_option_chain(ticker, expiry)
    if calls.empty or puts.empty:
        return pd.DataFrame()

    tau = time_to_expiry_years(expiry)
    pv_div = 0.0
    if use_dividends:
        pv_div = pv_of_dividends(div_series, _now_utc_naive(), expiry, rf)

    c = calls.rename(columns={
        "bid":"call_bid", "ask":"call_ask", "lastPrice":"call_lastPrice"
    })[["strike","call_bid","call_ask","call_lastPrice","volume","openInterest"]]
    p = puts.rename(columns={
        "bid":"put_bid", "ask":"put_ask", "lastPrice":"put_lastPrice"
    })[["strike","put_bid","put_ask","put_lastPrice","volume","openInterest"]]
    df = pd.merge(c, p, on="strike", how="inner")

    common = dict(S=spot, tau=tau, r=rf, pv_div=pv_div, stock_spread_cents=stock_spread_cents)

    results = []
    for _, row in df.iterrows():
        metrics = compute_row(row, common)
        out = {**row.to_dict(), **metrics}
        out["expiry"] = expiry
        out["tau_years"] = tau
        out["rf_annual"] = rf
        out["pv_div"] = pv_div
        results.append(out)

    out_df = pd.DataFrame(results)
    os.makedirs(out_dir, exist_ok=True)
    out_df.to_csv(os.path.join(out_dir, f"parity_{ticker}_{expiry}.csv"), index=False)
    return out_df

def make_plots(all_df: pd.DataFrame, ticker: str, out_root: str):
    if all_df.empty:
        return
    os.makedirs(out_root, exist_ok=True)

    plt.figure()
    all_df["gap_mid"].dropna().hist(bins=60)
    plt.title(f"{ticker}: Δ_mid distribution (all expiries)")
    plt.xlabel("Δ_mid (USD)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(out_root, f"{ticker}_gap_mid_hist.png"))
    plt.close()

    plt.figure()
    all_df["gap_exec"].dropna().hist(bins=60)
    plt.title(f"{ticker}: Δ_exec distribution (all expiries)")
    plt.xlabel("Δ_exec (USD)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(out_root, f"{ticker}_gap_exec_hist.png"))
    plt.close()

    for expiry, grp in all_df.groupby("expiry"):
        if grp.empty: 
            continue
        plt.figure()
        plt.scatter(grp["strike"], grp["gap_mid"], s=10, alpha=0.6)
        plt.title(f"{ticker}: Δ_mid vs Strike ({expiry})")
        plt.xlabel("Strike")
        plt.ylabel("Δ_mid (USD)")
        plt.tight_layout()
        safe_exp = expiry.replace(":","-")
        plt.savefig(os.path.join(out_root, f"{ticker}_{safe_exp}_gap_mid_vs_strike.png"))
        plt.close()

def summarize(all_df: pd.DataFrame) -> pd.DataFrame:
    if all_df.empty:
        return pd.DataFrame()
    th_small = 0.01
    th_medium = 0.05
    def pct(x): 
        return 100.0 * x.mean() if len(x) else 0.0
    grp = all_df.groupby("expiry").apply(lambda g: pd.Series({
        "n_strikes": len(g),
        "pct_|Δ_mid|>1c": pct(g["gap_mid"].abs() > th_small),
        "pct_|Δ_mid|>5c": pct(g["gap_mid"].abs() > th_medium),
        "pct_Δ_exec>0": pct(g["gap_exec"] > 0.0),
        "avg_|Δ_mid|": g["gap_mid"].abs().mean(),
        "max_|Δ_mid|": g["gap_mid"].abs().max(),
    })).reset_index()
    return grp

def main():
    args = parse_args()
    ticker = args.ticker.upper()
    out_root = os.path.join("outputs", ticker)
    os.makedirs(out_root, exist_ok=True)

    print(f"[1/5] Fetching spot & dividends for {ticker} ...")
    spot, div_series = get_spot_and_dividends(ticker)

    print("[2/5] Picking expiries ...")
    expiries = choose_expiries(ticker, args.expiries, args.min_dte, args.max_dte)
    if not expiries:
        raise SystemExit("No expiries selected. Try adjusting --min_dte/--max_dte or specify --expiries.")

    print("[3/5] Getting risk-free rate ...")
    rf = args.rf_override if args.rf_override is not None else get_rf_irx()

    print("[4/5] Processing expiries ...")
    all_parts = []
    for e in expiries:
        print(f"  - {e}")
        part = process_expiry(
            ticker=ticker, expiry=e, spot=spot, rf=rf, div_series=div_series,
            use_dividends=args.use_dividends, stock_spread_cents=args.stock_spread_cents, out_dir=out_root
        )
        if not part.empty:
            all_parts.append(part)
    all_df = pd.concat(all_parts, ignore_index=True) if all_parts else pd.DataFrame()
    if all_df.empty:
        raise SystemExit("No option rows produced. (Illiquid ticker/expiry or API limits?)")

    combined_path = os.path.join("outputs", f"parity_results_{ticker}.csv")
    all_df.to_csv(combined_path, index=False)

    print("[5/5] Summarizing ...")
    summary = summarize(all_df)
    summary_path = os.path.join("outputs", f"summary_{ticker}.csv")
    summary.to_csv(summary_path, index=False)
    print(summary)

    if args.plots:
        make_plots(all_df, ticker, out_root)

    print("Done. See outputs/ for CSVs and plots.")

if __name__ == "__main__":
    main()

import datetime as dt
from dateutil import tz
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

def _now_utc_naive() -> dt.datetime:
    return dt.datetime.utcnow().replace(tzinfo=None)

def get_spot_and_dividends(ticker: str, lookback_days: int = 5) -> Tuple[float, pd.Series]:
    tkr = yf.Ticker(ticker)
    hist = tkr.history(period=f"{max(lookback_days,1)}d")
    if hist.empty:
        raise RuntimeError(f"No price history for {ticker}.")
    spot = float(hist["Close"].iloc[-1])
    div = tkr.dividends
    if div is None:
        div = pd.Series(dtype=float)
    else:
        div.index = pd.to_datetime(div.index).tz_localize(None)
    return spot, div

def get_rf_irx() -> float:
    irx = yf.Ticker("^IRX").history(period="10d")
    if irx.empty:
        return 0.03
    last = float(irx["Close"].iloc[-1])
    return last / 100.0

def list_expiries(ticker: str) -> List[str]:
    tkr = yf.Ticker(ticker)
    opts = tkr.options or []
    return list(opts)

def load_option_chain(ticker: str, expiry: str):
    tkr = yf.Ticker(ticker)
    chain = tkr.option_chain(expiry)
    calls = chain.calls.copy()
    puts = chain.puts.copy()
    for df in [calls, puts]:
        if "lastTradeDate" in df.columns:
            df["lastTradeDate"] = pd.to_datetime(df["lastTradeDate"]).dt.tz_localize(None)
    return calls, puts

def time_to_expiry_years(expiry: str) -> float:
    now = _now_utc_naive()
    exp = pd.to_datetime(expiry).to_pydatetime().replace(tzinfo=None)
    delta = exp - now
    return max(delta.days, 0) / 365.25

def pv_of_dividends(div_series: pd.Series, start: dt.datetime, expiry: str, r_annual: float) -> float:
    if div_series is None or div_series.empty:
        return 0.0
    exp = pd.to_datetime(expiry).to_pydatetime().replace(tzinfo=None)
    mask = (div_series.index > start) & (div_series.index <= exp)
    future_divs = div_series.loc[mask]
    if future_divs.empty:
        return 0.0
    pv = 0.0
    for ex_date, amt in future_divs.items():
        t = (ex_date - start).days / 365.25
        pv += float(amt) * np.exp(-r_annual * max(t, 0.0))
    return float(pv)

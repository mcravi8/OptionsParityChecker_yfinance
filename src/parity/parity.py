import math
from dataclasses import dataclass
from typing import Optional, Dict

import numpy as np
import pandas as pd

@dataclass
class ParityInputs:
    S: float
    K: float
    tau: float
    r: float
    C_mid: float
    P_mid: float
    C_bid: float
    C_ask: float
    P_bid: float
    P_ask: float
    pv_div: float = 0.0
    stock_spread_cents: float = 1.0

def _safe_mid(bid: float, ask: float, last: float = None) -> float:
    vals = [v for v in [bid, ask] if v is not None and np.isfinite(v) and v > 0]
    if len(vals) == 2:
        return 0.5 * (vals[0] + vals[1])
    if last is not None and np.isfinite(last) and last > 0:
        return float(last)
    return np.nan

def theoretical_rhs(S: float, K: float, tau: float, r: float, pv_div: float = 0.0) -> float:
    return S - K * math.exp(-r * tau) - pv_div

def parity_gap_mid(pi: ParityInputs) -> float:
    rhs = theoretical_rhs(pi.S, pi.K, pi.tau, pi.r, pi.pv_div)
    return (pi.C_mid - pi.P_mid) - rhs

def parity_gap_executable(pi: ParityInputs, direction_hint: Optional[str] = None) -> float:
    stock_half_spread = (pi.stock_spread_cents or 1.0) / 200.0
    S_bid = pi.S - stock_half_spread
    S_ask = pi.S + stock_half_spread

    gap_mid = parity_gap_mid(pi) if direction_hint is None else None
    go_A = (gap_mid is not None and gap_mid > 0) or direction_hint == "A"
    go_B = (gap_mid is not None and gap_mid < 0) or direction_hint == "B"

    if go_A:
        lhs_exec = (pi.C_bid or 0.0) - (pi.P_ask or 0.0)
        rhs_exec = (S_ask - (pi.K * math.exp(-pi.r * pi.tau)) - pi.pv_div)
        return lhs_exec - rhs_exec
    elif go_B:
        lhs_exec = (S_bid - (pi.K * math.exp(-pi.r * pi.tau)) - pi.pv_div)
        rhs_exec = ((pi.C_ask or 0.0) - (pi.P_bid or 0.0))
        return lhs_exec - rhs_exec
    else:
        return 0.0

def compute_row(row: pd.Series, common: Dict) -> Dict:
    C_mid = _safe_mid(row.get("call_bid"), row.get("call_ask"), row.get("call_lastPrice"))
    P_mid = _safe_mid(row.get("put_bid"), row.get("put_ask"), row.get("put_lastPrice"))
    pi = ParityInputs(
        S=common["S"], K=float(row["strike"]), tau=common["tau"], r=common["r"],
        C_mid=float(C_mid) if np.isfinite(C_mid) else np.nan,
        P_mid=float(P_mid) if np.isfinite(P_mid) else np.nan,
        C_bid=float(row.get("call_bid") or np.nan),
        C_ask=float(row.get("call_ask") or np.nan),
        P_bid=float(row.get("put_bid") or np.nan),
        P_ask=float(row.get("put_ask") or np.nan),
        pv_div=float(common.get("pv_div", 0.0) or 0.0),
        stock_spread_cents=float(common.get("stock_spread_cents", 1.0) or 1.0),
    )
    gap_mid = parity_gap_mid(pi)
    gap_exec = parity_gap_executable(pi)
    return {"gap_mid": gap_mid, "gap_exec": gap_exec}

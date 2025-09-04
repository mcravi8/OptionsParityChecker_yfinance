# Options Arbitrage / Put–Call Parity Checker

A compact Python project that:
- Downloads **option chains** and **spot prices** for a ticker (yfinance),
- Computes **put–call parity gaps** across strikes and expiries (with dividend adjustment),
- Estimates whether gaps **survive transaction costs** using bid/ask-based executable bounds,
- Outputs CSVs and plots into `outputs/` for review.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# SPY example, auto-select expiries 7–120 DTE
python src/main_parity.py --ticker SPY --min_dte 7 --max_dte 120 --plots

# Single-stock example (AAPL) with dividend adjustment
python src/main_parity.py --ticker AAPL --min_dte 14 --max_dte 180 --use_dividends --plots
```

Outputs:
- `outputs/parity_results_<TICKER>.csv` (combined)
- Per-expiry CSVs in `outputs/<TICKER>/`
- Plots if `--plots`

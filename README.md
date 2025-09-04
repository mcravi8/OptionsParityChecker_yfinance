# Options Parity Checker (yfinance)

A reproducible Python project that tests **put-call parity** using live option chains from [yfinance](https://pypi.org/project/yfinance/).  
The tool checks whether the law of one price holds, accounting for dividends and execution costs.

## ✨ Features

- Downloads live option chains (calls and puts) via yfinance.
- Adjusts for **dividends** and **risk-free rate discounting**.
- Computes two parity gap metrics:
  - **Δ_mid**: Theoretical mispricing using mid-prices.
  - **Δ_exec**: Executable gap after crossing bid-ask spreads.
- Generates CSV summaries and visual plots (histograms, scatter by strike).
- CLI interface for reproducibility (`main_parity.py`).

## 📂 Repository Structure

```
OptionsParityChecker_yfinance/
│
├── src/                    # Core project code
│   ├── main_parity.py      # CLI entry point
│   ├── parity/             # Parity calculation module
│   │   ├── parity.py       # Core parity calculations
│   │   └── data.py         # yfinance data fetching
│
├── outputs/                # Generated CSVs and plots (ignored in .gitignore)
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── .gitignore              # Git ignore file
```

## 📋 Requirements

- Python 3.8+ (tested with 3.10)
- Recommended packages (install in a virtual environment):

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If `requirements.txt` is not available, install minimum dependencies:

```bash
pip install yfinance pandas numpy matplotlib
```

## ⚙️ Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/mcravi8/OptionsParityChecker_yfinance.git
cd OptionsParityChecker_yfinance
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 🚀 Usage

Run the parity checker with the CLI. Example for SPY with expiries between 7 and 120 days, including dividends and plots:

```bash
python src/main_parity.py --ticker SPY --min_dte 7 --max_dte 120 --use_dividends --plots
```

### Key Flags

- `--ticker`: Ticker symbol (e.g., SPY)
- `--min_dte`: Minimum days to expiration (e.g., 7)
- `--max_dte`: Maximum days to expiration (e.g., 120)
- `--use_dividends`: Include dividend adjustments (flag, no value)
- `--plots`: Generate histograms and scatter plots (flag, no value)

### Outputs

Results are saved in the `outputs/` directory:

- `summary_SPY.csv`: Per-expiry summary table.
- `parity_results_<TICKER>.csv`: Strike-level results (Δ_mid, Δ_exec, etc.).
- Plots:
  - `parity_histogram_<TICKER>.png`: Histogram of parity gaps.
  - `parity_scatter_<TICKER>.png`: Scatter plot of gaps by strike.

## 📊 Example Results (SPY)

Sample run on SPY (September 2025):

**Summary** (from `summary_SPY.csv`):

```csv
expiry,n_strikes,pct_|Δ_mid|>1c,pct_|Δ_mid|>5c,pct_Δ_exec>0,avg_|Δ_mid|,max_|Δ_mid|
2025-09-19,182,100.0,97.8,0.0,2.35,34.9
2025-09-26,95,100.0,98.9,0.0,3.07,9.4
2025-10-17,128,100.0,100.0,0.0,4.88,52.2
```

### Interpretation

- Nearly all strikes show a Δ_mid deviation from parity greater than 1¢, indicating theoretical mispricing.
- After accounting for execution costs (bid-ask spreads), `pct_Δ_exec>0 = 0%`, suggesting no arbitrage opportunities exist under realistic trading conditions.
- This aligns with the textbook principle: apparent arbitrage opportunities vanish when frictions like bid-ask spreads are included.

## 🔍 Notes on Methodology

- **Data Source**: Option chains are fetched via yfinance, which provides live market data.
- **Parity Calculation**: Adjusts for dividends and risk-free rate using standard put-call parity formulas.
- **Execution Costs**: Δ_exec accounts for bid-ask spreads, reflecting realistic trading frictions.
- **Look-Ahead Bias**: Uses only current market data to avoid look-ahead issues.

### Limitations

- yfinance data may have occasional gaps or inconsistencies (e.g., missing strikes or delayed updates).
- Dividend estimates rely on yfinance’s reported values, which may not reflect ex-dividend dates accurately.
- Risk-free rate is assumed constant; actual rates may vary over time.

# Options Trader

A lightweight tool that scans Yahoo Finance option chains to identify attractive
synthetic long setups (buy 1 call, sell 2 puts) for a list of high-conviction
tickers. The scanner focuses on expiries between three and nine months, keeps
put strikes around 90% of spot (with optional adjustments), and reports the
expected premiums, capital requirements, and annualised yields. Runs can be
triggered on demand, scheduled daily, or driven from a YAML configuration file.

## Features

- Download live spot data and option chains using `yfinance`
- Automatically pick the closest ATM call and configurable put strikes
- Compute days to expiry, per-structure premiums, capital required, and
  annualised yield for the 1:2 call/put ratio
- Optional volatility filters to keep trades within desired IV bands
- Console summary tables plus Excel exports with summary/detail tabs
- Daily scheduler so the scan can execute every day at 16:30 GST (or any other
  timezone/time combination)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[full]"
```

> **Note**: Shells such as `zsh` require the extras specifier to be quoted. Use
> `pip install -e .` if you only need the core runtime.

Python 3.9 or newer is required because the scheduler relies on `zoneinfo`.

## Usage

### Quick scan

```bash
python -m options_trader --tickers AAPL MSFT GOOGL META
```

The command prints the highest-yielding trade per ticker (automatic mode) and
creates an Excel workbook under `reports/` with the run metadata.

### Manual review

```bash
python -m options_trader --mode manual --tickers AAPL MSFT
```

Manual mode lists every qualifying expiry within the configured window so you
can review the full surface before executing a trade.

### YAML configuration

Copy `configs/sample.yaml`, adjust any values, and execute:

```bash
python -m options_trader --config configs/sample.yaml
```

The configuration file can override tickers, strike percentages, expiry window,
volatility bands, and contract ratio.

### Daily scheduling

```bash
python -m options_trader --tickers AAPL MSFT --schedule-time 16:30 --timezone Asia/Dubai
```

The CLI waits until the next scheduled run (16:30 GST in the example), performs
the scan, writes the report, and sleeps for another 24 hours until interrupted
with `Ctrl+C`.

## Excel output

Each run produces a timestamped workbook named `options_YYYYMMDD_HHMMSS.xlsx`.
The summary sheet includes the query label, run time, and key metrics. Every
ticker with at least one idea gets a dedicated tab containing the full quote
context (bid/ask/IV) alongside the computed cash flows.

## Testing

```bash
pytest
```

The unit tests use deterministic fixtures so they do not hit the Yahoo Finance
API. When you make changes, run the tests to keep regressions out of your
branch.

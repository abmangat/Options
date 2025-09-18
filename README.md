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

An automated toolkit for evaluating a synthetic long underlying strategy (buy 1 call, sell 2 puts) on a basket of high-conviction stocks. The project downloads live option chains from Yahoo Finance, computes structure cashflows using quoted premiums, and highlights the best opportunities based on annualized yield and capital at risk.

## Features

- Download spot data and live option chains via [yfinance](https://github.com/ranaroussi/yfinance)
- Evaluate quoted premiums directly (no synthetic pricing) for ATM calls and configurable put-strike adjustments around 90% of spot
- Focus on expiries between 3 and 9 months (configurable) and automatically pick the closest available contracts
- Compute key metrics for the 1 call : 2 put structure:
  - Time to expiry (days and years)
  - Call/put premiums (per share and per structure)
  - Net premium, capital at risk, breakeven, and effective entry price
  - Annualized yield using actual cashflows
  - Implied volatility derived from the quoted contracts (with configurable bounds)
- Automatic mode surfaces the best trade per ticker while manual mode prints all qualifying expiries
- Optional daily scheduler to run scans at a specific local time (4:30 pm GST by default)
- Automatically export each run to a timestamped Excel workbook with query metadata and leg-level details
- Configurable via CLI flags or YAML configuration file

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

> **Tip:** When using shells such as `zsh` (the macOS default) make sure to quote
> the extras specifier (`".[full]"`) so the brackets are not interpreted as a
> glob. Use `pip install -e .` if you prefer installing only the core
> dependencies.

Python 3.9 or newer is required (the scheduler relies on the standard library
`zoneinfo` module introduced in 3.9).

pip install -e .[full]
```

This project relies on third-party packages for data access and configuration parsing:

- [`yfinance`](https://github.com/ranaroussi/yfinance) (pulls market data; installs `pandas`/`numpy`)
- [`PyYAML`](https://pyyaml.org/) (parses YAML configuration files)

## Usage

### Automatic mode

Provide tickers directly (defaults to Apple, Microsoft, Google, and Meta):

```bash
python -m options_trader --tickers AAPL MSFT NVDA
```

Use a configuration file:

```bash
python -m options_trader --config configs/sample.yaml
```

### Manual mode

Manual mode prints all qualifying expiries (3–9 months by default):

```bash
python -m options_trader --mode manual --tickers AAPL MSFT
```

Limit output to the top N opportunities (automatic mode):

```bash
python -m options_trader --tickers AAPL MSFT NVDA --top 5
```

### Excel reports

Every execution saves a structured workbook in the `reports/` directory (override with `--output-dir`).
The summary sheet lists the query, date, time, and the top-level metrics per ticker while each result
gets its own tab inspired by the provided layout (individual legs, premiums, and capital metrics).

### Customising parameters

CLI flags override defaults:

```bash
python -m options_trader \
  --tickers AAPL \
  --put-strike-pct 0.9 \
  --put-variation -0.05 0 0.05 \
  --call-strike-pct 1.0 \
  --min-days 120 \
  --max-days 240 \
  --risk-free-rate 0.045
```

### Daily automation (4:30 pm GST example)

The CLI can run automatically each day at a fixed time in a chosen timezone. For the requested 4:30 pm Gulf Standard Time schedule:

```bash
python -m options_trader --tickers AAPL MSFT GOOGL META --schedule-time 16:30 --timezone Asia/Dubai
```

The process waits until the next scheduled window, runs the scan, prints the results, and repeats every 24 hours. Press `Ctrl+C` to stop the scheduler.

## Testing

```bash
pytest
```

The unit tests use deterministic fixtures so they do not hit the Yahoo Finance
API. When you make changes, run the tests to keep regressions out of your
branch.

## Notes

- The engine requires network access to download data from Yahoo Finance. For offline usage, substitute the `MarketDataClient` and `OptionChainClient` with versions that source data locally.
- Notifications default to stdout; integrate your own notifier by implementing the `Notifier` protocol.
- Premiums printed in reports represent both per-share quotes and the total cash flow for the entire structure (contract size × number of contracts).

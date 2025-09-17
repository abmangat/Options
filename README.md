# Options Trader

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
- Configurable via CLI flags or YAML configuration file

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
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

## Notes

- The engine requires network access to download data from Yahoo Finance. For offline usage, substitute the `MarketDataClient` and `OptionChainClient` with versions that source data locally.
- Notifications default to stdout; integrate your own notifier by implementing the `Notifier` protocol.
- Premiums printed in reports represent both per-share quotes and the total cash flow for the entire structure (contract size × number of contracts).

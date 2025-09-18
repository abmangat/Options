"""Market data access helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, List, Optional, Protocol, Sequence

if TYPE_CHECKING:  # pragma: no cover - typing aid
    import pandas as pd  # type: ignore
    import yfinance as yf

try:  # pragma: no cover - optional dependency at runtime
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - fallback when pandas is unavailable
    pd = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency at runtime
    import yfinance as yf
except Exception:  # pragma: no cover - fallback when yfinance is unavailable
    yf = None  # type: ignore[assignment]


@dataclass(frozen=True)
class OptionQuote:
    """Represents a single option quote."""

    contract_symbol: str
    ticker: str
    expiry: date
    option_type: str  # "call" or "put"
    strike: float
    bid: float | None
    ask: float | None
    last: float | None
    implied_volatility: float | None

    @property
    def mid(self) -> Optional[float]:
        """Return a mid price derived from bid/ask/last quotes."""

        prices: List[float] = []
        for value in (self.bid, self.ask):
            if value is not None and value > 0:
                prices.append(value)
        if len(prices) == 2:
            return round((prices[0] + prices[1]) / 2, 4)
        if prices:
            return prices[0]
        if self.last is not None and self.last > 0:
            return round(self.last, 4)
        return None


@dataclass
class OptionChain:
    """Holds call and put quotes for an expiry."""

    expiry: date
    calls: Sequence[OptionQuote]
    puts: Sequence[OptionQuote]


class MarketDataClient(Protocol):
    """Protocol describing market data access."""

    def spot_price(self, ticker: str) -> float:
        ...

    def expirations(self, ticker: str) -> Sequence[date]:
        ...

    def option_chain(self, ticker: str, expiry: date) -> OptionChain:
        ...


class YahooFinanceClient(MarketDataClient):
    """Market data client backed by :mod:`yfinance`."""

    def __init__(self) -> None:
        if yf is None:  # pragma: no cover - runtime guard
            raise RuntimeError("yfinance is required for live market data access")
        self._tickers: dict[str, Any] = {}

    def _get_ticker(self, symbol: str):
        if symbol not in self._tickers:
            self._tickers[symbol] = yf.Ticker(symbol)
        return self._tickers[symbol]

    def spot_price(self, ticker: str) -> float:
        asset = self._get_ticker(ticker)
        info = getattr(asset, "fast_info", None)
        price = getattr(info, "last_price", None)
        if price is None:
            history = asset.history(period="1d")
            if history.empty:
                raise RuntimeError(f"No spot data for {ticker}")
            price = float(history["Close"].iloc[-1])
        return float(price)

    def expirations(self, ticker: str) -> Sequence[date]:
        asset = self._get_ticker(ticker)
        expiries = []
        for raw in asset.options:
            expiries.append(datetime.strptime(raw, "%Y-%m-%d").date())
        return expiries

    def option_chain(self, ticker: str, expiry: date) -> OptionChain:
        asset = self._get_ticker(ticker)
        chain = asset.option_chain(expiry.strftime("%Y-%m-%d"))
        calls = _quotes_from_frame(chain.calls, ticker, expiry, "call")
        puts = _quotes_from_frame(chain.puts, ticker, expiry, "put")
        return OptionChain(expiry=expiry, calls=calls, puts=puts)


def _quotes_from_frame(
    frame,
    ticker: str,
    expiry: date,
    option_type: str,
) -> List[OptionQuote]:
    if pd is None:  # pragma: no cover - runtime guard
        raise RuntimeError("pandas is required to parse option chains")
    quotes: List[OptionQuote] = []
    for _, row in frame.iterrows():
        quotes.append(
            OptionQuote(
                contract_symbol=str(row.get("contractSymbol", "")),
                ticker=ticker,
                expiry=expiry,
                option_type=option_type,
                strike=float(row["strike"]),
                bid=_coerce_float(row.get("bid")),
                ask=_coerce_float(row.get("ask")),
                last=_coerce_float(row.get("lastPrice")),
                implied_volatility=_coerce_float(row.get("impliedVolatility")),
            )
        )
    quotes.sort(key=lambda q: q.strike)
    return quotes


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd is not None and pd.isna(number):  # pragma: no cover - requires pandas
        return None
    return number


__all__ = [
    "OptionQuote",
    "OptionChain",
    "MarketDataClient",
    "YahooFinanceClient",
]

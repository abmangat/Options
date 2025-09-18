"""Data access helpers for spot and option chain information."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Union


def _clean_number(value: Optional[Union[float, int]]) -> Optional[float]:
    """Normalise numbers from pandas/numpy into Python floats."""

    if value is None:
        return None
    try:
        if math.isnan(value):  # type: ignore[arg-type]
            return None
    except TypeError:
        pass
    return float(value)


@dataclass(frozen=True)
class MarketData:
    """Container for market data required by the pricing engine."""

    ticker: str
    spot_price: float
    valuation_date: datetime
    historical_prices: Sequence[float]

    @property
    def last_price(self) -> float:
        if not self.historical_prices:
            raise ValueError("Historical prices series is empty.")
        return float(self.historical_prices[-1])


@dataclass(frozen=True)
class OptionQuote:
    """Single option quote for a given strike and expiry."""

    ticker: str
    expiry: datetime
    strike: float
    option_type: str
    bid: Optional[float]
    ask: Optional[float]
    last_price: Optional[float]
    implied_volatility: Optional[float]

    @property
    def mid_price(self) -> Optional[float]:
        if self.bid is None or self.ask is None:
            return None
        if self.bid <= 0 or self.ask <= 0:
            return None
        return (self.bid + self.ask) / 2

    @property
    def price_per_share(self) -> float:
        for value in (self.mid_price, self.last_price, self.bid, self.ask):
            if value is not None and value > 0:
                return float(value)
        return 0.0


@dataclass(frozen=True)
class OptionChainSlice:
    """Collections of call and put quotes for a specific expiry."""

    ticker: str
    expiry: datetime
    calls: Sequence[OptionQuote]
    puts: Sequence[OptionQuote]


class MarketDataClient:
    """Wrapper around yfinance spot and historical downloads."""

    def __init__(self, period: str = "6mo", interval: str = "1d") -> None:
        self.period = period
        self.interval = interval

    def _load_ticker(self, ticker: str):
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "yfinance is required to download market data. Install via 'pip install yfinance'."
            ) from exc

        return yf.Ticker(ticker)

    def fetch(self, ticker: str) -> MarketData:
        ticker = ticker.upper().strip()
        yf_ticker = self._load_ticker(ticker)
        hist = yf_ticker.history(period=self.period, interval=self.interval)
        if hist.empty:
            raise ValueError(f"No historical data returned for {ticker}.")
        close = hist["Close"].dropna()
        if close.empty:
            raise ValueError(f"Close prices missing for {ticker}.")
        prices = [float(price) for price in close.tolist()]
        spot_price = prices[-1]
        valuation_date = datetime.now(timezone.utc)
        return MarketData(
            ticker=ticker,
            spot_price=spot_price,
            valuation_date=valuation_date,
            historical_prices=prices,
        )

    def fetch_latest_price(self, ticker: str) -> float:
        data = self.fetch(ticker)
        return data.spot_price

    def fetch_historical_prices(self, ticker: str) -> Sequence[float]:
        data = self.fetch(ticker)
        return data.historical_prices


class OptionChainClient:
    """Access to Yahoo Finance option chains."""

    def __init__(self) -> None:
        self._ticker_cache: Dict[str, object] = {}

    def _load_ticker(self, ticker: str):
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "yfinance is required to download option data. Install via 'pip install yfinance'."
            ) from exc

        ticker = ticker.upper().strip()
        cached = self._ticker_cache.get(ticker)
        if cached is not None:
            return cached
        yf_ticker = yf.Ticker(ticker)
        self._ticker_cache[ticker] = yf_ticker
        return yf_ticker

    @staticmethod
    def _parse_expiry(expiry: str) -> datetime:
        return datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def list_expiries(self, ticker: str) -> List[datetime]:
        yf_ticker = self._load_ticker(ticker)
        expiries = getattr(yf_ticker, "options", [])
        return [self._parse_expiry(expiry) for expiry in expiries]

    def _build_quotes(
        self, ticker: str, expiry: datetime, rows: Iterable[dict], option_type: str
    ) -> List[OptionQuote]:
        quotes: List[OptionQuote] = []
        for row in rows:
            strike = _clean_number(row.get("strike"))
            if strike is None:
                continue
            quote = OptionQuote(
                ticker=ticker,
                expiry=expiry,
                strike=strike,
                option_type=option_type,
                bid=_clean_number(row.get("bid")),
                ask=_clean_number(row.get("ask")),
                last_price=_clean_number(row.get("lastPrice")),
                implied_volatility=_clean_number(row.get("impliedVolatility")),
            )
            quotes.append(quote)
        return quotes

    def fetch_chain(self, ticker: str, expiry: Union[datetime, str]) -> OptionChainSlice:
        yf_ticker = self._load_ticker(ticker)
        if isinstance(expiry, datetime):
            expiry_dt = expiry
            expiry_str = expiry.strftime("%Y-%m-%d")
        else:
            expiry_str = expiry
            expiry_dt = self._parse_expiry(expiry)

        chain = yf_ticker.option_chain(expiry_str)
        call_rows = chain.calls.to_dict("records")
        put_rows = chain.puts.to_dict("records")
        calls = self._build_quotes(ticker, expiry_dt, call_rows, "call")
        puts = self._build_quotes(ticker, expiry_dt, put_rows, "put")
        return OptionChainSlice(ticker=ticker, expiry=expiry_dt, calls=calls, puts=puts)

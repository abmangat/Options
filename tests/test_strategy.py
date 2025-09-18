from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Sequence

import pytest

from options_trader.data import OptionChain, OptionQuote
from options_trader.strategy import StrategyEngine, StrategyParameters


@dataclass
class StubDataClient:
    spot: Dict[str, float]
    chains: Dict[tuple[str, date], OptionChain]
    expiries: Dict[str, Sequence[date]]

    def spot_price(self, ticker: str) -> float:
        return self.spot[ticker]

    def expirations(self, ticker: str) -> Sequence[date]:
        return self.expiries[ticker]

    def option_chain(self, ticker: str, expiry: date) -> OptionChain:
        return self.chains[(ticker, expiry)]


@pytest.fixture
def stub_client() -> StubDataClient:
    today = date.today()
    expiry_short = today + timedelta(days=120)
    expiry_long = today + timedelta(days=210)

    def call_quote(expiry: date, strike: float, bid: float, ask: float, iv: float) -> OptionQuote:
        return OptionQuote(
            contract_symbol=f"{expiry:%Y%m%d}C{strike}",
            ticker="AAPL",
            expiry=expiry,
            option_type="call",
            strike=strike,
            bid=bid,
            ask=ask,
            last=(bid + ask) / 2,
            implied_volatility=iv,
        )

    def put_quote(expiry: date, strike: float, bid: float, ask: float, iv: float) -> OptionQuote:
        return OptionQuote(
            contract_symbol=f"{expiry:%Y%m%d}P{strike}",
            ticker="AAPL",
            expiry=expiry,
            option_type="put",
            strike=strike,
            bid=bid,
            ask=ask,
            last=(bid + ask) / 2,
            implied_volatility=iv,
        )

    chain_short = OptionChain(
        expiry=expiry_short,
        calls=[
            call_quote(expiry_short, 95.0, 6.8, 7.2, 0.28),
            call_quote(expiry_short, 100.0, 6.0, 6.4, 0.26),
        ],
        puts=[
            put_quote(expiry_short, 85.0, 3.8, 4.2, 0.25),
            put_quote(expiry_short, 90.0, 4.5, 4.7, 0.24),
            put_quote(expiry_short, 95.0, 5.4, 5.8, 0.23),
        ],
    )
    chain_long = OptionChain(
        expiry=expiry_long,
        calls=[
            call_quote(expiry_long, 100.0, 7.4, 7.8, 0.27),
            call_quote(expiry_long, 105.0, 6.8, 7.2, 0.27),
        ],
        puts=[
            put_quote(expiry_long, 90.0, 5.0, 5.4, 0.24),
            put_quote(expiry_long, 95.0, 5.8, 6.2, 0.23),
        ],
    )

    return StubDataClient(
        spot={"AAPL": 100.0},
        chains={
            ("AAPL", expiry_short): chain_short,
            ("AAPL", expiry_long): chain_long,
        },
        expiries={"AAPL": [expiry_short, expiry_long]},
    )


def test_best_result_prefers_higher_yield(stub_client: StubDataClient) -> None:
    engine = StrategyEngine(data_client=stub_client)
    params = StrategyParameters(min_days=100, max_days=250)
    results = engine.evaluate("AAPL", params)
    assert len(results) == 2
    best = engine.best_result("AAPL", params)
    assert best is not None
    assert best == results[0]
    assert results[0].days_to_expiry < results[1].days_to_expiry
    assert results[0].annualized_yield > results[1].annualized_yield


def test_put_variations_produce_distinct_strikes(stub_client: StubDataClient) -> None:
    engine = StrategyEngine(data_client=stub_client)
    params = StrategyParameters(
        min_days=100,
        max_days=150,
        put_strike_variation=(-0.05, 0.0, 0.05),
    )
    results = engine.evaluate("AAPL", params)
    strikes = {result.put_quote.strike for result in results}
    assert strikes == {85.0, 90.0, 95.0}


def test_volatility_filters_remove_trades(stub_client: StubDataClient) -> None:
    engine = StrategyEngine(data_client=stub_client)
    params = StrategyParameters(min_days=100, max_days=150, min_volatility=0.26)
    results = engine.evaluate("AAPL", params)
    assert results == []

from datetime import datetime, timedelta, timezone

import pytest

from options_trader.data import MarketData, MarketDataClient, OptionChainSlice, OptionQuote
from options_trader.strategy import StrategyEngine, StrategyParameters


class DummyMarketDataClient(MarketDataClient):
    def __init__(self) -> None:
        super().__init__()
        self.valuation_time = datetime(2024, 1, 2, tzinfo=timezone.utc)
        prices = [141 + i for i in range(10)]
        self._data = MarketData(
            ticker="ABC",
            spot_price=float(prices[-1]),
            valuation_date=self.valuation_time,
            historical_prices=prices,
        )

    def fetch(self, ticker: str) -> MarketData:  # type: ignore[override]
        return MarketData(
            ticker=ticker,
            spot_price=self._data.spot_price,
            valuation_date=self.valuation_time,
            historical_prices=list(self._data.historical_prices),
        )


class DummyOptionChainClient:
    def __init__(self, valuation_time: datetime) -> None:
        self.valuation_time = valuation_time
        self.expiry_1 = valuation_time + timedelta(days=120)
        self.expiry_2 = valuation_time + timedelta(days=150)

    def list_expiries(self, ticker: str):  # type: ignore[override]
        return [self.expiry_1, self.expiry_2]

    def fetch_chain(self, ticker: str, expiry: datetime):  # type: ignore[override]
        if expiry == self.expiry_1:
            calls = [
                OptionQuote(
                    ticker=ticker,
                    expiry=expiry,
                    strike=150.0,
                    option_type="call",
                    bid=5.5,
                    ask=6.5,
                    last_price=6.0,
                    implied_volatility=0.24,
                )
            ]
            puts = [
                OptionQuote(
                    ticker=ticker,
                    expiry=expiry,
                    strike=135.0,
                    option_type="put",
                    bid=9.5,
                    ask=10.5,
                    last_price=10.0,
                    implied_volatility=0.28,
                ),
                OptionQuote(
                    ticker=ticker,
                    expiry=expiry,
                    strike=130.0,
                    option_type="put",
                    bid=7.0,
                    ask=7.6,
                    last_price=7.3,
                    implied_volatility=0.27,
                ),
            ]
        else:
            calls = [
                OptionQuote(
                    ticker=ticker,
                    expiry=expiry,
                    strike=150.0,
                    option_type="call",
                    bid=4.8,
                    ask=5.2,
                    last_price=5.0,
                    implied_volatility=0.22,
                )
            ]
            puts = [
                OptionQuote(
                    ticker=ticker,
                    expiry=expiry,
                    strike=135.0,
                    option_type="put",
                    bid=8.0,
                    ask=8.6,
                    last_price=8.3,
                    implied_volatility=0.25,
                ),
            ]

        return OptionChainSlice(ticker=ticker, expiry=expiry, calls=calls, puts=puts)


def test_engine_uses_live_option_quotes():
    market_client = DummyMarketDataClient()
    option_client = DummyOptionChainClient(market_client.valuation_time)
    params = StrategyParameters(
        min_days=100,
        max_days=140,
        expiry_step=20,
        call_strike_pct=1.0,
        put_strike_pct=0.9,
        put_strike_variation=(0.0,),
        min_volatility=0.1,
        max_volatility=0.4,
    )
    engine = StrategyEngine(
        data_client=market_client, option_client=option_client, parameters=params
    )

    results = engine.evaluate("ABC")
    assert len(results) == 1
    result = results[0]

    assert result.call_strike == pytest.approx(150.0)
    assert result.put_strike == pytest.approx(135.0)
    assert result.call_price_per_share == pytest.approx(6.0)
    assert result.put_price_per_share == pytest.approx(10.0)
    assert result.call_premium == pytest.approx(6.0 * params.contract_size * params.call_contracts)
    assert result.put_premium == pytest.approx(10.0 * params.contract_size * params.put_contracts)
    assert result.net_premium == pytest.approx(result.put_premium - result.call_premium)
    assert result.capital_at_risk == pytest.approx(135.0 * params.contract_size * params.put_contracts)
    assert result.call_strike_pct == pytest.approx(1.0)
    assert result.put_strike_pct == pytest.approx(0.9)
    assert result.implied_volatility == pytest.approx((0.24 + 0.28) / 2)


def test_best_result_prefers_highest_yield():
    market_client = DummyMarketDataClient()
    option_client = DummyOptionChainClient(market_client.valuation_time)
    params = StrategyParameters(
        min_days=100,
        max_days=200,
        expiry_step=10,
        put_strike_variation=(0.0,),
        min_volatility=0.1,
        max_volatility=0.4,
    )
    engine = StrategyEngine(
        data_client=market_client, option_client=option_client, parameters=params
    )

    results = engine.evaluate("ABC")
    assert len(results) == 2

    best = engine.best_result("ABC")
    assert best is not None
    assert best.annualized_yield == max(r.annualized_yield for r in results)


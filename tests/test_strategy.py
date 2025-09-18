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

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

"""Synthetic long strategy implementation using live option quotes."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence

from .config import StrategyConfig
from .data import MarketDataClient, OptionChainClient, OptionQuote
from .notifications import ConsoleNotifier, Notifier


@dataclass(frozen=True)
class StrategyParameters:
    put_strike_pct: float = 0.9
    call_strike_pct: float = 1.0
    min_days: int = 90
    max_days: int = 270
    expiry_step: int = 30
    call_contracts: int = 1
    put_contracts: int = 2
    contract_size: int = 100
    risk_free_rate: float = 0.04
    min_volatility: float = 0.05
    max_volatility: float = 1.5
    put_strike_variation: Sequence[float] = (-0.05, 0.0, 0.05)


@dataclass(frozen=True)
class StrategyResult:
    ticker: str
    valuation_time: datetime
    expiry: datetime
    days_to_expiry: int
    call_strike: float
    put_strike: float
    call_strike_pct: float
    put_strike_pct: float
    call_price_per_share: float
    put_price_per_share: float
    call_premium: float
    put_premium: float
    net_premium: float
    annualized_yield: float
    implied_volatility: float | None
    spot_price: float
    breakeven_price: float
    effective_entry_price: float
    capital_at_risk: float
    call_contracts: int
    put_contracts: int
    contract_size: int
    call_quote: OptionQuote
    put_quote: OptionQuote

    @property
    def description(self) -> str:
        return (
            f"Buy {self.call_contracts}x {self.call_strike:.2f} call, "
            f"sell {self.put_contracts}x {self.put_strike:.2f} put "
            f"(contract size {self.contract_size}) expiring {self.expiry.date()}"
        )

    @property
    def years_to_expiry(self) -> float:
        return self.days_to_expiry / 365.0

    @property
    def call_bid(self) -> float | None:
        return self.call_quote.bid

    @property
    def call_ask(self) -> float | None:
        return self.call_quote.ask

    @property
    def call_last(self) -> float | None:
        return self.call_quote.last_price

    @property
    def call_mid(self) -> float | None:
        return self.call_quote.mid_price

    @property
    def put_bid(self) -> float | None:
        return self.put_quote.bid

    @property
    def put_ask(self) -> float | None:
        return self.put_quote.ask

    @property
    def put_last(self) -> float | None:
        return self.put_quote.last_price

    @property
    def put_mid(self) -> float | None:
        return self.put_quote.mid_price


class StrategyEngine:
    def __init__(
        self,
        data_client: MarketDataClient | None = None,
        option_client: OptionChainClient | None = None,
        notifier: Notifier | None = None,
        parameters: StrategyParameters | None = None,
    ) -> None:
        self.data_client = data_client or MarketDataClient()
        self.option_client = option_client or OptionChainClient()
        self.notifier = notifier or ConsoleNotifier()
        self.parameters = parameters or StrategyParameters()

    def _select_quote(self, quotes: Sequence[OptionQuote], target_strike: float) -> OptionQuote | None:
        if not quotes:
            return None
        ordered = sorted(quotes, key=lambda q: (abs(q.strike - target_strike), q.strike))
        for quote in ordered:
            if quote.price_per_share > 0:
                return quote
        return None

    def evaluate(self, ticker: str, parameters: StrategyParameters | None = None) -> List[StrategyResult]:
        params = parameters or self.parameters
        market_data = self.data_client.fetch(ticker)
        valuation_time = market_data.valuation_date
        spot_price = market_data.spot_price
        expiries = sorted(self.option_client.list_expiries(ticker))

        filtered_expiries: List[tuple[datetime, int]] = []
        last_selected_days: int | None = None
        for expiry in expiries:
            delta_seconds = (expiry - valuation_time).total_seconds()
            days = max(0, math.ceil(delta_seconds / 86400))
            if days < params.min_days or days > params.max_days:
                continue
            if params.expiry_step > 0 and last_selected_days is not None:
                if days - last_selected_days < params.expiry_step:
                    continue
            filtered_expiries.append((expiry, days))
            last_selected_days = days

        results: List[StrategyResult] = []
        for expiry, days in filtered_expiries:
            if days == 0:
                continue
            chain = self.option_client.fetch_chain(ticker, expiry)
            target_call_strike = params.call_strike_pct * spot_price
            call_quote = self._select_quote(chain.calls, target_call_strike)
            if call_quote is None:
                continue
            call_price_per_share = call_quote.price_per_share
            if call_price_per_share <= 0:
                continue
            call_strike = call_quote.strike
            call_premium = call_price_per_share * params.contract_size * params.call_contracts

            for variation in params.put_strike_variation:
                put_strike_pct = max(0.01, params.put_strike_pct * (1.0 + variation))
                target_put_strike = put_strike_pct * spot_price
                put_quote = self._select_quote(chain.puts, target_put_strike)
                if put_quote is None:
                    continue
                put_price_per_share = put_quote.price_per_share
                if put_price_per_share <= 0:
                    continue
                put_strike = put_quote.strike
                call_strike_pct = call_strike / spot_price if spot_price > 0 else 0.0
                put_strike_pct_actual = put_strike / spot_price if spot_price > 0 else 0.0
                put_premium = put_price_per_share * params.contract_size * params.put_contracts

                net_premium = put_premium - call_premium
                capital_at_risk = params.put_contracts * params.contract_size * put_strike
                if capital_at_risk <= 0:
                    continue
                annualized_yield = (net_premium / capital_at_risk) * (365.0 / days)
                shares_short_put = params.put_contracts * params.contract_size
                breakeven_price = put_strike - net_premium / shares_short_put
                effective_entry_price = breakeven_price

                implied_values = [
                    vol
                    for vol in (call_quote.implied_volatility, put_quote.implied_volatility)
                    if vol is not None and vol > 0
                ]
                implied_volatility = (
                    sum(implied_values) / len(implied_values) if implied_values else None
                )
                if implied_volatility is not None:
                    if implied_volatility < params.min_volatility:
                        continue
                    if implied_volatility > params.max_volatility:
                        continue

                results.append(
                    StrategyResult(
                        ticker=market_data.ticker,
                        valuation_time=valuation_time,
                        expiry=expiry,
                        days_to_expiry=days,
                        call_strike=call_strike,
                        put_strike=put_strike,
                        call_strike_pct=call_strike_pct,
                        put_strike_pct=put_strike_pct_actual,
                        call_price_per_share=call_price_per_share,
                        put_price_per_share=put_price_per_share,
                        call_premium=call_premium,
                        put_premium=put_premium,
                        net_premium=net_premium,
                        annualized_yield=annualized_yield,
                        implied_volatility=implied_volatility,
                        spot_price=market_data.spot_price,
                        breakeven_price=breakeven_price,
                        effective_entry_price=effective_entry_price,
                        capital_at_risk=capital_at_risk,
                        call_contracts=params.call_contracts,
                        put_contracts=params.put_contracts,
                        contract_size=params.contract_size,
                        call_quote=call_quote,
                        put_quote=put_quote,
                    )
                )
        results.sort(key=lambda r: r.annualized_yield, reverse=True)
        return results

    def best_result(self, ticker: str, parameters: StrategyParameters | None = None) -> StrategyResult | None:
        evaluated = self.evaluate(ticker, parameters)
        return evaluated[0] if evaluated else None

    def run(self, config: StrategyConfig | None = None) -> List[StrategyResult]:
        if config is None:
            tickers = ["AAPL", "MSFT", "GOOGL", "META"]
            params = self.parameters
        else:
            tickers = config.normalized_tickers()
            params = StrategyParameters(
                put_strike_pct=config.put_strike_pct,
                call_strike_pct=config.call_strike_pct,
                min_days=config.min_days,
                max_days=config.max_days,
                expiry_step=config.expiry_step,
                call_contracts=config.call_to_put_ratio[0],
                put_contracts=config.call_to_put_ratio[1],
                contract_size=config.contract_size,
                risk_free_rate=config.risk_free_rate,
                min_volatility=config.min_volatility,
                max_volatility=config.max_volatility,
                put_strike_variation=tuple(config.put_strike_variation),
            )

        results: List[StrategyResult] = []
        for ticker in tickers:
            try:
                ticker_results = self.evaluate(ticker, params)
            except Exception as exc:  # pragma: no cover - defensive
                self.notifier.notify(f"Failed to evaluate {ticker}: {exc}")
                continue
            if ticker_results:
                best = ticker_results[0]
                self.notifier.notify(
                    f"{ticker}: best expiry {best.expiry.date()} with annualized yield {best.annualized_yield:.2%}"
                )
                results.append(best)
        results.sort(key=lambda r: r.annualized_yield, reverse=True)
        return results

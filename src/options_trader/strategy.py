"""Core strategy evaluation logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable, List

from .data import MarketDataClient, OptionQuote, YahooFinanceClient


@dataclass(frozen=True)
class StrategyParameters:
    """Parameters controlling the synthetic long evaluation."""

    put_strike_pct: float = 0.9
    call_strike_pct: float = 1.0
    put_strike_variation: Sequence[float] = (0.0,)
    min_days: int = 90
    max_days: int = 270
    expiry_step: int = 30
    call_contracts: int = 1
    put_contracts: int = 2
    contract_size: int = 100
    risk_free_rate: float = 0.04
    min_volatility: float | None = None
    max_volatility: float | None = None


@dataclass(frozen=True)
class StrategyResult:
    """Captures the metrics for a trade candidate."""

    ticker: str
    spot: float
    expiry: date
    days_to_expiry: int
    call_quote: OptionQuote
    put_quote: OptionQuote
    put_variation: float
    net_premium: float
    net_premium_per_share: float
    capital_required: float
    annualized_yield: float
    effective_entry: float

    def summary_dict(self) -> dict[str, float | str]:
        return {
            "Ticker": self.ticker,
            "Expiry": self.expiry.isoformat(),
            "Days": self.days_to_expiry,
            "Spot": round(self.spot, 2),
            "Call Strike": round(self.call_quote.strike, 2),
            "Put Strike": round(self.put_quote.strike, 2),
            "Put Variation": self.put_variation,
            "Net Premium": round(self.net_premium, 2),
            "Capital Required": round(self.capital_required, 2),
            "Annualized Yield": round(self.annualized_yield * 100, 2),
            "Effective Entry": round(self.effective_entry, 2),
        }


class StrategyEngine:
    """Runs the synthetic long evaluation for the supplied tickers."""

    def __init__(
        self,
        data_client: MarketDataClient | None = None,
        parameters: StrategyParameters | None = None,
    ) -> None:
        self._data = data_client or YahooFinanceClient()
        self.parameters = parameters or StrategyParameters()

    def evaluate(
        self, ticker: str, parameters: StrategyParameters | None = None
    ) -> List[StrategyResult]:
        params = parameters or self.parameters
        spot = self._data.spot_price(ticker)
        expiries = self._eligible_expiries(ticker, params)
        results: List[StrategyResult] = []
        for expiry in expiries:
            chain = self._data.option_chain(ticker, expiry)
            result_set = self._evaluate_expiry(ticker, spot, chain, params)
            results.extend(result_set)
        results.sort(key=lambda r: r.annualized_yield, reverse=True)
        return results

    def best_result(
        self, ticker: str, parameters: StrategyParameters | None = None
    ) -> StrategyResult | None:
        results = self.evaluate(ticker, parameters)
        return results[0] if results else None

    def _eligible_expiries(
        self, ticker: str, params: StrategyParameters
    ) -> List[date]:
        today = datetime.now(timezone.utc).date()
        expiries = sorted(self._data.expirations(ticker))
        selected: List[date] = []
        last_added_days: int | None = None
        for expiry in expiries:
            days = (expiry - today).days
            if days < params.min_days or days > params.max_days:
                continue
            if last_added_days is None or days - last_added_days >= params.expiry_step:
                selected.append(expiry)
                last_added_days = days
        return selected

    def _evaluate_expiry(
        self,
        ticker: str,
        spot: float,
        chain,
        params: StrategyParameters,
    ) -> List[StrategyResult]:
        call_target = spot * params.call_strike_pct
        call_quote = _nearest_with_price(chain.calls, call_target)
        if call_quote is None:
            return []

        results: List[StrategyResult] = []
        for variation in params.put_strike_variation:
            put_target = spot * params.put_strike_pct * (1.0 + variation)
            put_quote = _nearest_with_price(chain.puts, put_target)
            if put_quote is None:
                continue
            if not _volatility_in_range(call_quote, put_quote, params):
                continue
            metrics = _compute_metrics(call_quote, put_quote, params)
            if metrics is None:
                continue
            result = StrategyResult(
                ticker=ticker,
                spot=spot,
                expiry=chain.expiry,
                days_to_expiry=metrics["days"],
                call_quote=call_quote,
                put_quote=put_quote,
                put_variation=variation,
                net_premium=metrics["net_premium"],
                net_premium_per_share=metrics["net_per_share"],
                capital_required=metrics["capital"],
                annualized_yield=metrics["annualized_yield"],
                effective_entry=metrics["effective_entry"],
            )
            results.append(result)
        return results


def _nearest_with_price(quotes: Iterable[OptionQuote], target: float) -> OptionQuote | None:
    candidates: List[OptionQuote] = []
    for quote in quotes:
        if quote.mid is None:
            continue
        candidates.append(quote)
    if not candidates:
        return None
    return min(candidates, key=lambda q: abs(q.strike - target))


def _volatility_in_range(
    call_quote: OptionQuote,
    put_quote: OptionQuote,
    params: StrategyParameters,
) -> bool:
    vols: List[float] = []
    for quote in (call_quote, put_quote):
        if quote.implied_volatility is not None:
            vols.append(float(quote.implied_volatility))
    if not vols:
        return True
    avg_vol = sum(vols) / len(vols)
    if params.min_volatility is not None and avg_vol < params.min_volatility:
        return False
    if params.max_volatility is not None and avg_vol > params.max_volatility:
        return False
    return True


def _compute_metrics(
    call_quote: OptionQuote,
    put_quote: OptionQuote,
    params: StrategyParameters,
) -> dict[str, float] | None:
    call_mid = call_quote.mid
    put_mid = put_quote.mid
    if call_mid is None or put_mid is None:
        return None

    call_contracts = params.call_contracts
    put_contracts = params.put_contracts
    contract_size = params.contract_size

    days = max((call_quote.expiry - datetime.now(timezone.utc).date()).days, 1)
    net_per_share = put_mid * put_contracts - call_mid * call_contracts
    net_premium = net_per_share * contract_size
    exposure_shares = contract_size * put_contracts
    capital = put_quote.strike * exposure_shares - net_premium
    if capital <= 0:
        return None
    annualized = (net_premium / capital) * (365.0 / days)
    effective_entry = put_quote.strike - (net_premium / exposure_shares)
    return {
        "days": days,
        "net_premium": net_premium,
        "net_per_share": net_per_share,
        "capital": capital,
        "annualized_yield": annualized,
        "effective_entry": effective_entry,
    }


__all__ = [
    "StrategyEngine",
    "StrategyParameters",
    "StrategyResult",
]

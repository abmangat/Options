"""Human readable reporting helpers."""
from __future__ import annotations

from typing import Iterable, List

from .strategy import StrategyResult


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    return f"{value * 100:.2f}%"


def format_optional_currency(value: float | None) -> str:
    if value is None:
        return "N/A"
    return format_currency(value)


def format_optional_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"
    return format_percentage(value)


def summarize_results(results: Iterable[StrategyResult]) -> str:
    lines: List[str] = []
    for result in results:
        lines.append(
            " | ".join(
                [
                    f"Ticker: {result.ticker}",
                    f"Spot: {format_currency(result.spot_price)}",
                    f"Valuation: {result.valuation_time.isoformat(timespec='minutes')}",
                    f"Expiry: {result.expiry.date()} ({result.days_to_expiry} days / {result.years_to_expiry:.2f}y)",
                    f"Call Strike: {format_currency(result.call_strike)}",
                    f"Put Strike: {format_currency(result.put_strike)}",
                    f"Call % Spot: {format_percentage(result.call_strike_pct)}",
                    f"Put % Spot: {format_percentage(result.put_strike_pct)}",
                    f"Structure: {result.call_contracts}C/{result.put_contracts}P @ {result.contract_size} shares",
                    f"Call Premium (per share/total): {format_currency(result.call_price_per_share)} / {format_currency(result.call_premium)}",
                    f"Put Premium (per share/total): {format_currency(result.put_price_per_share)} / {format_currency(result.put_premium)}",
                    f"Net Premium: {format_currency(result.net_premium)}",
                    f"Capital At Risk: {format_currency(result.capital_at_risk)}",
                    f"Annualized Yield: {format_percentage(result.annualized_yield)}",
                    f"Implied Volatility: {format_optional_percentage(result.implied_volatility)}",
                    f"Breakeven: {format_currency(result.breakeven_price)}",
                    f"Effective Entry: {format_currency(result.effective_entry_price)}",
                    f"Call Bid/Ask: {format_optional_currency(result.call_bid)} / {format_optional_currency(result.call_ask)}",
                    f"Put Bid/Ask: {format_optional_currency(result.put_bid)} / {format_optional_currency(result.put_ask)}",
                ]
            )
        )
    return "\n".join(lines)

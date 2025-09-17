"""Volatility estimators."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Sequence

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class VolatilityEstimate:
    annualized: float
    daily_std: float


def historical_volatility(
    prices: Sequence[float],
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> VolatilityEstimate:
    """Estimate historical volatility from a sequence of prices."""

    if len(prices) < 2:
        raise ValueError("Need at least two price points to estimate volatility.")

    log_returns = []
    for previous, current in zip(prices, prices[1:]):
        if previous <= 0 or current <= 0:
            raise ValueError("Prices must be positive to compute log returns.")
        log_returns.append(math.log(current / previous))

    if len(log_returns) < 2:
        daily_std = 0.0
    else:
        daily_std = float(statistics.stdev(log_returns))
    annualized = daily_std * math.sqrt(trading_days)
    return VolatilityEstimate(annualized=annualized, daily_std=daily_std)

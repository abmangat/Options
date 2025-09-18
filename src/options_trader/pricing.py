"""Black-Scholes pricing utilities."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class OptionPremium:
    call: float
    put: float


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _d1(spot: float, strike: float, time: float, rate: float, volatility: float) -> float:
    if spot <= 0 or strike <= 0:
        raise ValueError("Spot and strike must be positive numbers.")
    if time <= 0:
        raise ValueError("Time to expiry must be positive in years.")
    if volatility <= 0:
        raise ValueError("Volatility must be positive (annualized decimal).")
    numerator = math.log(spot / strike) + (rate + 0.5 * volatility**2) * time
    denominator = volatility * math.sqrt(time)
    return numerator / denominator


def _d2(d1: float, time: float, volatility: float) -> float:
    return d1 - volatility * math.sqrt(time)


def black_scholes_premium(
    spot: float,
    strike: float,
    time: float,
    rate: float,
    volatility: float,
) -> OptionPremium:
    """Return call and put prices using the Black-Scholes model."""

    d1 = _d1(spot, strike, time, rate, volatility)
    d2 = _d2(d1, time, volatility)
    call = spot * _norm_cdf(d1) - strike * math.exp(-rate * time) * _norm_cdf(d2)
    put = strike * math.exp(-rate * time) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)
    return OptionPremium(call=call, put=put)


def intrinsic_value_call(spot: float, strike: float) -> float:
    return max(0.0, spot - strike)


def intrinsic_value_put(spot: float, strike: float) -> float:
    return max(0.0, strike - spot)

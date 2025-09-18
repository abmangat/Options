"""Configuration helpers for the options trader application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import yaml


@dataclass
class AppConfig:
    """Represents the YAML configuration for a run."""

    tickers: List[str] = field(default_factory=list)
    put_strike_pct: float = 0.9
    call_strike_pct: float = 1.0
    put_strike_variation: Sequence[float] = field(default_factory=lambda: (0.0,))
    min_days: int = 90
    max_days: int = 270
    expiry_step: int = 30
    call_to_put_ratio: Tuple[int, int] = (1, 2)
    risk_free_rate: float = 0.04
    contract_size: int = 100
    min_volatility: float | None = None
    max_volatility: float | None = None

    def normalized_tickers(self) -> List[str]:
        """Return upper-cased tickers with duplicates removed preserving order."""

        seen: set[str] = set()
        ordered: List[str] = []
        for ticker in self.tickers:
            norm = ticker.strip().upper()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            ordered.append(norm)
        return ordered


def load_config(path: str | Path) -> AppConfig:
    """Load an :class:`AppConfig` from a YAML file."""

    resolved = Path(path).expanduser()
    data = yaml.safe_load(resolved.read_text())
    if data is None:
        return AppConfig()

    def _seq(name: str, default: Iterable[float]) -> Sequence[float]:
        raw = data.get(name, default)
        if isinstance(raw, (list, tuple)):
            return tuple(float(x) for x in raw)
        return tuple(default)

    config = AppConfig(
        tickers=[str(t) for t in data.get("tickers", [])],
        put_strike_pct=float(data.get("put_strike_pct", 0.9)),
        call_strike_pct=float(data.get("call_strike_pct", 1.0)),
        put_strike_variation=_seq("put_strike_variation", (0.0,)),
        min_days=int(data.get("min_days", 90)),
        max_days=int(data.get("max_days", 270)),
        expiry_step=int(data.get("expiry_step", 30)),
        call_to_put_ratio=tuple(int(x) for x in data.get("call_to_put_ratio", (1, 2))),
        risk_free_rate=float(data.get("risk_free_rate", 0.04)),
        contract_size=int(data.get("contract_size", 100)),
        min_volatility=(
            float(data["min_volatility"]) if data.get("min_volatility") is not None else None
        ),
        max_volatility=(
            float(data["max_volatility"]) if data.get("max_volatility") is not None else None
        ),
    )
    return config


__all__ = ["AppConfig", "load_config"]

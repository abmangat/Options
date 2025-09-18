"""Configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple, Union

from typing import List, Sequence

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


@dataclass
class StrategyConfig:
    tickers: List[str]
    mode: str = "automatic"
    risk_free_rate: float = 0.04
    put_strike_pct: float = 0.9
    call_strike_pct: float = 1.0
    min_days: int = 90
    max_days: int = 270
    expiry_step: int = 30
    call_to_put_ratio: Tuple[int, int] = (1, 2)

    call_to_put_ratio: Sequence[int] = (1, 2)
    contract_size: int = 100
    max_strikes: int = 6
    min_volatility: float = 0.1
    max_volatility: float = 1.0
    put_strike_variation: Sequence[float] = (-0.05, 0.0, 0.05)

    def normalized_tickers(self) -> List[str]:
        return sorted({t.upper().strip() for t in self.tickers if t})


def load_config(path: Union[str, Path]) -> StrategyConfig:
def load_config(path: str | Path) -> StrategyConfig:
    if yaml is None:  # pragma: no cover - optional dependency
        raise ImportError("PyYAML is required to load configuration files. Install via 'pip install pyyaml'.")
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return StrategyConfig(**data)

"""Module entry point for ``python -m options_trader``."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":  # pragma: no cover - direct execution
    raise SystemExit(main())

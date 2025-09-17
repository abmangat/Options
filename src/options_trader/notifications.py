"""Notification hooks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Notifier(Protocol):
    """Protocol for sending notifications."""

    def notify(self, message: str) -> None:  # pragma: no cover - interface
        ...


@dataclass
class ConsoleNotifier:
    prefix: str = "[OptionsTrader]"

    def notify(self, message: str) -> None:
        print(f"{self.prefix} {message}")

"""Reporting helpers for console and Excel output."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from .strategy import StrategyResult
from .xlsx import Workbook


SUMMARY_COLUMNS = [
    "Ticker",
    "Expiry",
    "Days",
    "Spot",
    "Call Strike",
    "Put Strike",
    "Put Variation",
    "Net Premium",
    "Capital Required",
    "Annualized Yield",
    "Effective Entry",
]


def summarize_results(results: Sequence[StrategyResult]) -> str:
    """Render a text table for console output."""

    if not results:
        return "No qualifying trades found."

    headers = SUMMARY_COLUMNS
    rows = []
    for result in results:
        summary = result.summary_dict()
        rows.append([
            summary["Ticker"],
            summary["Expiry"],
            summary["Days"],
            summary["Spot"],
            summary["Call Strike"],
            summary["Put Strike"],
            summary["Put Variation"],
            summary["Net Premium"],
            summary["Capital Required"],
            f"{summary['Annualized Yield']:.2f}%",
            summary["Effective Entry"],
        ])

    widths = [len(str(h)) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))

    def _format_row(row: Iterable[object]) -> str:
        return " | ".join(str(cell).ljust(widths[idx]) for idx, cell in enumerate(row))

    lines = [_format_row(headers), "-+-".join("-" * w for w in widths)]
    lines.extend(_format_row(row) for row in rows)
    return "\n".join(lines)


def export_results_to_excel(
    results: Sequence[StrategyResult],
    query_label: str,
    run_time: datetime,
    output_path: Path | str,
) -> Path:
    """Persist results to an Excel workbook."""

    path = Path(output_path)
    timestamp = run_time.isoformat(timespec="seconds")
    workbook = Workbook()

    if not results:
        workbook.add_sheet(
            "Summary",
            [
                ["Query", "Run Time", "Message"],
                [query_label, timestamp, "No qualifying trades found"],
            ],
        )
        return workbook.save(path)

    summary_header = ["Query", "Run Time", *SUMMARY_COLUMNS]
    summary_rows = [summary_header]
    for result in results:
        summary = result.summary_dict()
        summary_rows.append(
            [
                query_label,
                timestamp,
                summary["Ticker"],
                summary["Expiry"],
                summary["Days"],
                summary["Spot"],
                summary["Call Strike"],
                summary["Put Strike"],
                summary["Put Variation"],
                summary["Net Premium"],
                summary["Capital Required"],
                summary["Annualized Yield"],
                summary["Effective Entry"],
            ]
        )
    workbook.add_sheet("Summary", summary_rows)

    grouped: dict[str, List[StrategyResult]] = {}
    for result in results:
        grouped.setdefault(result.ticker, []).append(result)

    detail_header = summary_header + [
        "Call Bid",
        "Call Ask",
        "Put Bid",
        "Put Ask",
        "Call IV",
        "Put IV",
    ]
    for ticker, ticker_results in grouped.items():
        rows = [detail_header]
        for result in ticker_results:
            summary = result.summary_dict()
            rows.append(
                [
                    query_label,
                    timestamp,
                    summary["Ticker"],
                    summary["Expiry"],
                    summary["Days"],
                    summary["Spot"],
                    summary["Call Strike"],
                    summary["Put Strike"],
                    summary["Put Variation"],
                    summary["Net Premium"],
                    summary["Capital Required"],
                    summary["Annualized Yield"],
                    summary["Effective Entry"],
                    result.call_quote.bid,
                    result.call_quote.ask,
                    result.put_quote.bid,
                    result.put_quote.ask,
                    result.call_quote.implied_volatility,
                    result.put_quote.implied_volatility,
                ]
            )
        workbook.add_sheet(ticker, rows)

    return workbook.save(path)


__all__ = ["summarize_results", "export_results_to_excel", "SUMMARY_COLUMNS"]

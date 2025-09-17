"""Reporting helpers for console output and Excel exports."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from .strategy import StrategyResult
from .xlsx import Cell, WorkbookBuilder

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


def _sanitize_sheet_title(title: str) -> str:
    cleaned = "".join("_" if ch in ":\\/?*[]" else ch for ch in title).strip()
    cleaned = cleaned or "Sheet"
    if len(cleaned) > 31:
        cleaned = cleaned[:31]
    return cleaned


def _sheet_title_for(result: StrategyResult) -> str:
    base = f"{result.ticker}_{result.expiry:%Y%m%d}"
    return _sanitize_sheet_title(base)


def _build_summary_sheet(sheet, results: Sequence[StrategyResult], query: str, run_time: datetime) -> None:
    headers = [
        "Query",
        "Run Date",
        "Run Time",
        "Ticker",
        "Spot Price",
        "Expiry",
        "Days to Expiry",
        "Annualized Yield",
        "Net Premium",
        "Capital At Risk",
        "Breakeven Price",
        "Effective Entry",
    ]
    sheet.append([Cell(value, "header") for value in headers])

    if results:
        for result in results:
            sheet.append(
                [
                    Cell(query, "text_border"),
                    Cell(run_time.strftime("%Y-%m-%d"), "text_border"),
                    Cell(run_time.strftime("%H:%M:%S"), "text_border"),
                    Cell(result.ticker, "text_border"),
                    Cell(result.spot_price, "currency"),
                    Cell(result.expiry.strftime("%Y-%m-%d"), "text_border"),
                    Cell(result.days_to_expiry, "text_border"),
                    Cell(result.annualized_yield, "percent"),
                    Cell(result.net_premium, "currency"),
                    Cell(result.capital_at_risk, "currency"),
                    Cell(result.breakeven_price, "currency"),
                    Cell(result.effective_entry_price, "currency"),
                ]
            )
    else:
        sheet.append(
            [
                Cell(query, "text_border"),
                Cell(run_time.strftime("%Y-%m-%d"), "text_border"),
                Cell(run_time.strftime("%H:%M:%S"), "text_border"),
                Cell("No qualifying trades", "text_border"),
            ]
        )
    sheet.set_column_widths([20, 12, 12, 12, 14, 12, 14, 16, 16, 18, 16, 16])


def _build_detail_sheet(sheet, result: StrategyResult, query: str, run_time: datetime) -> None:
    sheet.append([Cell("Query", "metric_label"), Cell(query, "metric_text")])
    sheet.append([Cell("Run Date", "metric_label"), Cell(run_time.strftime("%Y-%m-%d"), "metric_text")])
    sheet.append([Cell("Run Time", "metric_label"), Cell(run_time.strftime("%H:%M:%S"), "metric_text")])
    sheet.append([Cell("", "metric_text")])
    sheet.append([Cell("Underlying", "metric_label"), Cell(result.ticker, "metric_text")])
    sheet.append([Cell("Current Price", "metric_label"), Cell(result.spot_price, "metric_currency")])
    sheet.append([Cell("Valuation Time", "metric_label"), Cell(result.valuation_time.strftime("%Y-%m-%d %H:%M"), "metric_text")])
    sheet.append([Cell("Expiry", "metric_label"), Cell(result.expiry.strftime("%Y-%m-%d"), "metric_text")])
    sheet.append(
        [
            Cell("Days to Expiry", "metric_label"),
            Cell(result.days_to_expiry, "metric_text"),
            Cell("Months to Expiry", "metric_label"),
            Cell(f"{result.years_to_expiry * 12:.2f}", "metric_text"),
        ]
    )
    sheet.append(
        [
            Cell("Call Strike", "metric_label"),
            Cell(result.call_strike, "metric_currency"),
            Cell("Put Strike", "metric_label"),
            Cell(result.put_strike, "metric_currency"),
        ]
    )
    sheet.append(
        [
            Cell("Call % Spot", "metric_label"),
            Cell(result.call_strike_pct, "metric_percent"),
            Cell("Put % Spot", "metric_label"),
            Cell(result.put_strike_pct, "metric_percent"),
        ]
    )

    sheet.append([Cell("", "metric_text")])
    headers = [
        "Leg",
        "Strike",
        "% From Spot",
        "Premium (per share)",
        "Expiry",
        "Time to Expiry (months)",
        "Buy/Sell",
        "Ratio",
        "Premium Collected (Paid)",
    ]
    sheet.append([Cell(value, "header") for value in headers])

    months = result.years_to_expiry * 12
    table_rows = [
        [
            Cell("Put Short", "text_border"),
            Cell(result.put_strike, "currency"),
            Cell((result.put_strike / result.spot_price - 1.0) if result.spot_price else 0.0, "percent"),
            Cell(result.put_price_per_share, "currency"),
            Cell(result.expiry.strftime("%Y-%m-%d"), "text_border"),
            Cell(months, "months"),
            Cell("Sell", "text_border"),
            Cell(result.put_contracts, "text_border"),
            Cell(result.put_premium, "currency"),
        ],
        [
            Cell("Call Long", "text_border"),
            Cell(result.call_strike, "currency"),
            Cell((result.call_strike / result.spot_price - 1.0) if result.spot_price else 0.0, "percent"),
            Cell(result.call_price_per_share, "currency"),
            Cell(result.expiry.strftime("%Y-%m-%d"), "text_border"),
            Cell(months, "months"),
            Cell("Buy", "text_border"),
            Cell(result.call_contracts, "text_border"),
            Cell(-result.call_premium, "currency"),
        ],
    ]
    for row in table_rows:
        sheet.append(row)

    net_per_share = (
        result.put_price_per_share * result.put_contracts
        - result.call_price_per_share * result.call_contracts
    )
    sheet.append(
        [
            Cell("Net Premium", "net_label"),
            Cell("", "net_value"),
            Cell("", "net_value"),
            Cell(net_per_share, "net_currency"),
            Cell("", "net_value"),
            Cell("", "net_value"),
            Cell("", "net_value"),
            Cell("", "net_value"),
            Cell(result.net_premium, "net_currency"),
        ]
    )

    sheet.append([Cell("", "metric_text")])
    metrics = [
        ("Capital At Risk", result.capital_at_risk, "metric_currency"),
        ("Annualized Yield", result.annualized_yield, "metric_percent"),
        ("Breakeven Price", result.breakeven_price, "metric_currency"),
        ("Effective Entry Price", result.effective_entry_price, "metric_currency"),
        (
            "Implied Volatility",
            result.implied_volatility if result.implied_volatility is not None else "N/A",
            "metric_percent" if result.implied_volatility is not None else "metric_text",
        ),
        (
            "Call Bid/Ask",
            f"{format_optional_currency(result.call_bid)} / {format_optional_currency(result.call_ask)}",
            "metric_text",
        ),
        (
            "Put Bid/Ask",
            f"{format_optional_currency(result.put_bid)} / {format_optional_currency(result.put_ask)}",
            "metric_text",
        ),
    ]
    for label, value, style in metrics:
        sheet.append([Cell(label, "metric_label"), Cell(value, style)])

    sheet.set_column_widths([18, 18, 16, 22, 14, 22, 12, 10, 24])


def export_results_to_excel(
    results: Sequence[StrategyResult],
    query: str,
    run_time: datetime,
    output_path: Path,
) -> Path:
    builder = WorkbookBuilder()
    summary_sheet = builder.add_sheet("Summary")
    _build_summary_sheet(summary_sheet, results, query, run_time)

    seen: set[str] = set()
    for result in results:
        base_title = _sheet_title_for(result)
        title = base_title
        counter = 2
        while title in seen:
            title = _sanitize_sheet_title(f"{base_title}_{counter}")
            counter += 1
        seen.add(title)
        sheet = builder.add_sheet(title)
        _build_detail_sheet(sheet, result, query, run_time)

    builder.save(output_path)
    return output_path

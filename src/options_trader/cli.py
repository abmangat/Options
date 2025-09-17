"""Command line interface for the options trader."""
from __future__ import annotations

import argparse
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
import time as time_module
from typing import List, Sequence

from zoneinfo import ZoneInfo

from .config import load_config
from .reporting import export_results_to_excel, summarize_results
from .strategy import StrategyEngine, StrategyParameters, StrategyResult


DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "META"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthetic long options strategy helper")
    parser.add_argument("--tickers", nargs="*", help="Tickers to evaluate", default=None)
    parser.add_argument("--config", help="Path to YAML configuration file", default=None)
    parser.add_argument(
        "--mode",
        choices=["automatic", "manual"],
        default="automatic",
        help="Automatic mode reports best trade per ticker; manual prints all expiries.",
    )
    parser.add_argument("--risk-free-rate", type=float, default=None)
    parser.add_argument("--put-strike-pct", type=float, default=None)
    parser.add_argument("--call-strike-pct", type=float, default=None)
    parser.add_argument(
        "--put-variation",
        type=float,
        nargs="*",
        default=None,
        help="Relative adjustments to apply to the base put strike percentage (e.g. -0.05 0 0.05)",
    )
    parser.add_argument("--min-days", type=int, default=None)
    parser.add_argument("--max-days", type=int, default=None)
    parser.add_argument("--expiry-step", type=int, default=30)
    parser.add_argument("--top", type=int, default=3, help="Number of top results to print in automatic mode")
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory where Excel reports will be saved.",
    )
    parser.add_argument(
        "--schedule-time",
        type=_parse_daily_time,
        help="Schedule the scan to run daily at HH:MM (24h clock) in the selected timezone.",
    )
    parser.add_argument(
        "--timezone",
        default="Asia/Dubai",
        help=(
            "IANA timezone name used for scheduled runs. Default aligns with Gulf Standard Time (Asia/Dubai)."
        ),
    )
    return parser


def _parse_daily_time(value: str) -> dt_time:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Time must be in HH:MM 24-hour format.") from exc
    return parsed.time()


def _params_from_args(args: argparse.Namespace, base: StrategyParameters) -> StrategyParameters:
    return StrategyParameters(
        put_strike_pct=args.put_strike_pct or base.put_strike_pct,
        call_strike_pct=args.call_strike_pct or base.call_strike_pct,
        min_days=args.min_days or base.min_days,
        max_days=args.max_days or base.max_days,
        expiry_step=args.expiry_step or base.expiry_step,
        call_contracts=base.call_contracts,
        put_contracts=base.put_contracts,
        risk_free_rate=args.risk_free_rate or base.risk_free_rate,
        min_volatility=base.min_volatility,
        max_volatility=base.max_volatility,
        put_strike_variation=tuple(args.put_variation) if args.put_variation else base.put_strike_variation,
    )


def _run_once(
    engine: StrategyEngine,
    tickers: Sequence[str],
    params: StrategyParameters,
    mode: str,
    top: int,
) -> List[StrategyResult]:
    collected: List[StrategyResult] = []
    if mode == "manual":
        for ticker in tickers:
            results = engine.evaluate(ticker, params)
            print(f"\n{ticker} - showing all qualifying expiries")
            print("-" * 80)
            if not results:
                print("No results.")
                continue
            print(summarize_results(results))
            collected.extend(results)
    else:
        results = []
        for ticker in tickers:
            best = engine.best_result(ticker, params)
            if best:
                results.append(best)
        collected.extend(results)
        if not results:
            print("No qualifying trades found.")
        for result in results[:top]:
            print(summarize_results([result]))

    return collected


def _export_report(
    results: Sequence[StrategyResult],
    tickers: Sequence[str],
    mode: str,
    output_dir: str,
    run_time: datetime,
) -> Path:
    if not tickers:
        query = "(no tickers)"
    else:
        query = ", ".join(tickers)
    mode_label = "Manual" if mode == "manual" else "Automatic"
    query_label = f"{query} [{mode_label}]"

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"options_{run_time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    path = directory / filename
    export_results_to_excel(results, query_label, run_time, path)
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    engine = StrategyEngine()
    params = engine.parameters

    tickers: List[str]
    if args.config:
        config = load_config(args.config)
        tickers = config.normalized_tickers()
        params = StrategyParameters(
            put_strike_pct=config.put_strike_pct,
            call_strike_pct=config.call_strike_pct,
            min_days=config.min_days,
            max_days=config.max_days,
            call_contracts=config.call_to_put_ratio[0],
            put_contracts=config.call_to_put_ratio[1],
            risk_free_rate=config.risk_free_rate,
            expiry_step=config.expiry_step,
            contract_size=config.contract_size,
            min_volatility=config.min_volatility,
            max_volatility=config.max_volatility,
            put_strike_variation=tuple(config.put_strike_variation),
        )
    else:
        tickers = [t.upper() for t in (args.tickers or DEFAULT_TICKERS)]
        params = _params_from_args(args, params)

    engine = StrategyEngine(parameters=params)

    if args.schedule_time:
        try:
            tz = ZoneInfo(args.timezone)
        except Exception as exc:  # pragma: no cover - invalid tz guard
            raise SystemExit(f"Invalid timezone '{args.timezone}': {exc}") from exc

        schedule_time: dt_time = args.schedule_time
        print(
            f"Scheduling daily run for {schedule_time.strftime('%H:%M')} in timezone {args.timezone}."
        )

        while True:
            now = datetime.now(tz)
            run_at = datetime.combine(now.date(), schedule_time, tzinfo=tz)
            if run_at <= now:
                run_at += timedelta(days=1)
            wait_seconds = max(0, (run_at - now).total_seconds())
            hours, remainder = divmod(wait_seconds, 3600)
            minutes = remainder // 60
            print(
                f"Next run at {run_at.isoformat(timespec='minutes')} (in {int(hours)}h{int(minutes)}m)."
            )
            try:
                time_module.sleep(wait_seconds)
            except KeyboardInterrupt:
                print("Scheduler interrupted before execution.")
                return 0

            try:
                run_time = datetime.now(tz)
                results = _run_once(engine, tickers, params, args.mode, args.top)
                report_path = _export_report(results, tickers, args.mode, args.output_dir, run_time)
                print(f"Excel report saved to {report_path}")
            except KeyboardInterrupt:
                print("Scheduler interrupted during execution.")
                return 0
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"Scheduled run failed: {exc}")
    else:
        run_time = datetime.now()
        results = _run_once(engine, tickers, params, args.mode, args.top)
        report_path = _export_report(results, tickers, args.mode, args.output_dir, run_time)
        print(f"Excel report saved to {report_path}")

    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())

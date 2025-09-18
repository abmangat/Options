from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from options_trader.data import OptionQuote
from options_trader.reporting import export_results_to_excel, summarize_results
from options_trader.strategy import StrategyResult


def _quote(option_type: str, strike: float, expiry: date) -> OptionQuote:
    return OptionQuote(
        contract_symbol=f"TEST{option_type}{strike}",
        ticker="AAPL",
        expiry=expiry,
        option_type=option_type,
        strike=strike,
        bid=5.0,
        ask=5.4,
        last=5.2,
        implied_volatility=0.25,
    )


def _result() -> StrategyResult:
    expiry = date.today() + timedelta(days=150)
    call_quote = _quote("C", 100.0, expiry)
    put_quote = _quote("P", 90.0, expiry)
    return StrategyResult(
        ticker="AAPL",
        spot=102.0,
        expiry=expiry,
        days_to_expiry=150,
        call_quote=call_quote,
        put_quote=put_quote,
        put_variation=0.0,
        net_premium=200.0,
        net_premium_per_share=2.0,
        capital_required=17800.0,
        annualized_yield=0.035,
        effective_entry=89.0,
    )


def test_summarize_results_formats_table() -> None:
    output = summarize_results([_result()])
    assert "Ticker" in output
    assert "AAPL" in output


def test_export_results_to_excel_creates_summary_and_detail(tmp_path: Path) -> None:
    result = _result()
    run_time = datetime(2025, 1, 15, 16, 30, 0)
    path = tmp_path / "report.xlsx"
    export_results_to_excel([result], "AAPL [Automatic]", run_time, path)
    summary_rows = _read_sheet(path, "Summary")
    assert summary_rows[0][2] == "Ticker"
    assert summary_rows[1][2] == "AAPL"
    assert summary_rows[1][0] == "AAPL [Automatic]"
    detail_rows = _read_sheet(path, "AAPL")
    assert detail_rows[0][2] == "Ticker"
    assert detail_rows[1][2] == "AAPL"


def test_export_results_handles_empty_results(tmp_path: Path) -> None:
    run_time = datetime(2025, 1, 15, 16, 30, 0)
    path = tmp_path / "empty.xlsx"
    export_results_to_excel([], "Empty Query", run_time, path)
    summary_rows = _read_sheet(path, "Summary")
    assert summary_rows[1][0] == "Empty Query"
    assert summary_rows[0][2] == "Message"


def _read_sheet(path: Path, sheet_name: str) -> list[list[str | float]]:
    with zipfile.ZipFile(path, "r") as zf:
        workbook_xml = ET.fromstring(zf.read("xl/workbook.xml"))
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet_element = None
        for sheet in workbook_xml.find("m:sheets", ns):
            if sheet.attrib.get("name") == sheet_name:
                sheet_element = sheet
                break
        if sheet_element is None:
            raise KeyError(sheet_name)
        sheet_id = sheet_element.attrib["sheetId"]
        sheet_xml = ET.fromstring(zf.read(f"xl/worksheets/sheet{sheet_id}.xml"))
        rows: list[list[str | float]] = []
        for row in sheet_xml.findall("m:sheetData/m:row", ns):
            cells: list[str | float] = []
            for cell in row.findall("m:c", ns):
                cell_type = cell.attrib.get("t")
                if cell_type == "inlineStr":
                    text_node = cell.find("m:is/m:t", ns)
                    cells.append(text_node.text if text_node is not None else "")
                else:
                    value = cell.find("m:v", ns)
                    if value is None:
                        cells.append("")
                    else:
                        try:
                            cells.append(float(value.text))
                        except (TypeError, ValueError):
                            cells.append(value.text or "")
            rows.append(cells)
    return rows

from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from options_trader.data import OptionQuote
from options_trader.reporting import export_results_to_excel
from options_trader.strategy import StrategyResult

_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _sheet_cells(path, index):
    with ZipFile(path) as archive:
        data = archive.read(f"xl/worksheets/sheet{index}.xml")
    root = ET.fromstring(data)
    cells: dict[str, object] = {}
    for cell in root.findall(".//x:sheetData/x:row/x:c", _NS):
        ref = cell.attrib.get("r", "")
        if cell.get("t") == "inlineStr":
            text = cell.find("x:is/x:t", _NS)
            cells[ref] = text.text if text is not None else ""
        else:
            value = cell.find("x:v", _NS)
            if value is None or value.text is None:
                cells[ref] = ""
            else:
                raw = value.text
                try:
                    cells[ref] = float(raw)
                except ValueError:
                    cells[ref] = raw
    return cells


def _sheet_names(path):
    with ZipFile(path) as archive:
        data = archive.read("xl/workbook.xml")
    root = ET.fromstring(data)
    return [sheet.attrib.get("name", "") for sheet in root.findall(".//x:sheet", _NS)]


def _sample_result() -> StrategyResult:
    valuation_time = datetime(2024, 1, 2, 15, 30, tzinfo=timezone.utc)
    expiry = datetime(2024, 6, 21, tzinfo=timezone.utc)
    call_quote = OptionQuote(
        ticker="AAPL",
        expiry=expiry,
        strike=150.0,
        option_type="call",
        bid=5.5,
        ask=6.5,
        last_price=6.0,
        implied_volatility=0.24,
    )
    put_quote = OptionQuote(
        ticker="AAPL",
        expiry=expiry,
        strike=135.0,
        option_type="put",
        bid=9.5,
        ask=10.5,
        last_price=10.0,
        implied_volatility=0.28,
    )

    call_contracts = 1
    put_contracts = 2
    contract_size = 100
    call_premium = call_quote.price_per_share * contract_size * call_contracts
    put_premium = put_quote.price_per_share * contract_size * put_contracts
    net_premium = put_premium - call_premium

    return StrategyResult(
        ticker="AAPL",
        valuation_time=valuation_time,
        expiry=expiry,
        days_to_expiry=170,
        call_strike=call_quote.strike,
        put_strike=put_quote.strike,
        call_strike_pct=call_quote.strike / 140.0,
        put_strike_pct=put_quote.strike / 140.0,
        call_price_per_share=call_quote.price_per_share,
        put_price_per_share=put_quote.price_per_share,
        call_premium=call_premium,
        put_premium=put_premium,
        net_premium=net_premium,
        annualized_yield=0.12,
        implied_volatility=0.26,
        spot_price=140.0,
        breakeven_price=128.0,
        effective_entry_price=128.0,
        capital_at_risk=put_quote.strike * contract_size * put_contracts,
        call_contracts=call_contracts,
        put_contracts=put_contracts,
        contract_size=contract_size,
        call_quote=call_quote,
        put_quote=put_quote,
    )


def test_export_results_creates_structured_workbook(tmp_path):
    result = _sample_result()
    run_time = datetime(2024, 1, 3, 16, 30, tzinfo=timezone.utc)
    path = tmp_path / "report.xlsx"

    export_results_to_excel([result], "AAPL [Automatic]", run_time, path)

    names = _sheet_names(path)
    assert names[0] == "Summary"
    assert any(name.startswith("AAPL_") for name in names[1:])

    summary = _sheet_cells(path, 1)
    assert summary["A2"] == "AAPL [Automatic]"
    assert summary["B2"] == "2024-01-03"
    assert summary["C2"] == "16:30:00"
    assert summary["D2"] == "AAPL"
    assert summary["H2"] == pytest.approx(0.12)
    assert summary["I2"] == pytest.approx(result.net_premium)

    detail = _sheet_cells(path, 2)
    assert detail["B5"] == "AAPL"
    assert detail["B6"] == pytest.approx(140.0)
    assert detail["I14"] == pytest.approx(result.put_premium)
    assert detail["I15"] == pytest.approx(-result.call_premium)
    assert detail["I16"] == pytest.approx(result.net_premium)
    assert detail["B18"] == pytest.approx(result.capital_at_risk)
    assert detail["B19"] == pytest.approx(0.12)


def test_export_results_handles_empty_runs(tmp_path):
    run_time = datetime(2024, 1, 3, 16, 30, tzinfo=timezone.utc)
    path = tmp_path / "empty.xlsx"

    export_results_to_excel([], "AAPL [Automatic]", run_time, path)

    names = _sheet_names(path)
    assert names == ["Summary"]

    summary = _sheet_cells(path, 1)
    assert summary["A2"] == "AAPL [Automatic]"
    assert summary["D2"] == "No qualifying trades"


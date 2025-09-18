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

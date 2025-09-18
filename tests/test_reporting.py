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

"""Very small helper for writing basic XLSX workbooks without external deps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence
from xml.sax.saxutils import escape
import zipfile


@dataclass
class Worksheet:
    name: str
    rows: Sequence[Sequence[object]]


class Workbook:
    """Minimal XLSX writer supporting only inline strings and numbers."""

    def __init__(self) -> None:
        self._worksheets: List[Worksheet] = []

    def add_sheet(self, name: str, rows: Sequence[Sequence[object]]) -> None:
        safe_name = name[:31] if len(name) > 31 else name
        self._worksheets.append(Worksheet(safe_name, rows))

    def save(self, path: Path | str) -> Path:
        if not self._worksheets:
            raise ValueError("Workbook must contain at least one worksheet")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", _content_types(len(self._worksheets)))
            zf.writestr("_rels/.rels", _root_rels())
            zf.writestr("xl/workbook.xml", _workbook_xml(self._worksheets))
            zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(self._worksheets))
            zf.writestr("xl/styles.xml", _styles_xml())
            for idx, worksheet in enumerate(self._worksheets, start=1):
                zf.writestr(
                    f"xl/worksheets/sheet{idx}.xml",
                    _worksheet_xml(worksheet.rows),
                )
        return output


def _content_types(sheet_count: int) -> str:
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        "<Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>"
        f"{overrides}"  # noqa: G001
        "</Types>"
    )


def _root_rels() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
        "</Relationships>"
    )


def _workbook_xml(sheets: Sequence[Worksheet]) -> str:
    sheet_entries = "".join(
        f'<sheet name="{escape(sheet.name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, sheet in enumerate(sheets, start=1)
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
        "<sheets>"
        f"{sheet_entries}"
        "</sheets>"
        "</workbook>"
    )


def _workbook_rels(sheets: Sequence[Worksheet]) -> str:
    relationships = "".join(
        f'<Relationship Id="rId{idx}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{idx}.xml"/>'
        for idx, _ in enumerate(sheets, start=1)
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        f"{relationships}"
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        "<fonts count=\"1\"><font/></fonts>"
        "<fills count=\"1\"><fill/></fills>"
        "<borders count=\"1\"><border/></borders>"
        "<cellStyleXfs count=\"1\"><xf/></cellStyleXfs>"
        "<cellXfs count=\"1\"><xf/></cellXfs>"
        "</styleSheet>"
    )


def _worksheet_xml(rows: Sequence[Sequence[object]]) -> str:
    lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">",
        "<sheetData>",
    ]
    for row_idx, row in enumerate(rows, start=1):
        lines.append(f'<row r="{row_idx}">')
        for col_idx, value in enumerate(row, start=1):
            cell_ref = f"{_column_name(col_idx)}{row_idx}"
            if value is None:
                continue
            if isinstance(value, (int, float)):
                lines.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
            else:
                escaped = escape(str(value))
                lines.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t>{escaped}</t></is></c>'
                )
        lines.append("</row>")
    lines.extend(["</sheetData>", "</worksheet>"])
    return "".join(lines)


def _column_name(idx: int) -> str:
    letters = ""
    while idx:
        idx, remainder = divmod(idx - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


__all__ = ["Workbook"]

"""Lightweight XLSX writer for formatted reports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union
from typing import List, Sequence
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass
class Cell:
    value: Optional[object]

    value: object | None
    style: str = "text"


class Sheet:
    def __init__(self, title: str) -> None:
        self.title = title
        self.rows: List[List[Cell]] = []
        self.column_widths: Dict[int, float] = {}

    def append(self, row: Sequence[Union[Cell, Tuple[object, str], object]]) -> None:

        self.column_widths: dict[int, float] = {}

    def append(self, row: Sequence[Cell | tuple | object]) -> None:
        processed: List[Cell] = []
        for item in row:
            if isinstance(item, Cell):
                processed.append(item)
            elif isinstance(item, tuple) and len(item) == 2:
                processed.append(Cell(item[0], item[1]))
            else:
                processed.append(Cell(item))
        self.rows.append(processed)

    def set_column_widths(self, widths: Sequence[float]) -> None:
        for index, width in enumerate(widths, start=1):
            self.column_widths[index] = width

    def computed_widths(self) -> Dict[int, float]:
    def computed_widths(self) -> dict[int, float]:
        widths = dict(self.column_widths)
        for row in self.rows:
            for index, cell in enumerate(row, start=1):
                text = "" if cell.value is None else str(cell.value)
                current = widths.get(index, 8.0)
                widths[index] = min(60.0, max(current, len(text) + 2))
        return widths


class WorkbookBuilder:
    def __init__(self) -> None:
        self.sheets: List[Sheet] = []

    def add_sheet(self, title: str) -> Sheet:
        sheet = Sheet(title)
        self.sheets.append(sheet)
        return sheet

    def save(self, path: Path) -> Path:
        write_workbook(self.sheets, path)
        return path


STYLE_ORDER = [
    "text",  # 0 default
    "header",  # 1 bold with fill and border
    "currency",  # 2 currency with border
    "percent",  # 3 percent with border
    "months",  # 4 months with border
    "net_currency",  # 5 currency with fill
    "net_value",  # 6 general text with fill
    "net_label",  # 7 bold text with fill
    "text_border",  # 8 general text with border
    "metric_label",  # 9 bold text (no border)
    "metric_currency",  # 10 currency without border
    "metric_percent",  # 11 percent without border
    "metric_text",  # 12 plain text without border
]

STYLE_IDS = {name: index for index, name in enumerate(STYLE_ORDER)}

HEADER_FILL = "FFDEEAF6"
NET_FILL = "FFFCE4D6"
BORDER_COLOR = "FFB7B7B7"


def style_id(name: str) -> int:
    return STYLE_IDS.get(name, 0)


def write_workbook(sheets: Sequence[Sheet], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("docProps/core.xml", _core_props())
        archive.writestr("docProps/app.xml", _app_props(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/theme/theme1.xml", THEME_XML)
        for index, sheet in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(sheet))


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _column_letter(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result or "A"


def _content_types(sheet_count: int) -> str:
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for idx in range(1, sheet_count + 1)
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        "<Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>"
        "<Override PartName=\"/xl/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>"
        "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>"
        "<Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>"
        f"{overrides}"
        "</Types>"
    )


def _root_rels() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
        "<Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>"
        "<Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>"
        "</Relationships>"
    )


def _core_props() -> str:
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" "
        "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:dcterms=\"http://purl.org/dc/terms/\" "
        "xmlns:dcmitype=\"http://purl.org/dc/dcmitype/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">"
        "<dc:creator>options-trader</dc:creator>"
        "<cp:lastModifiedBy>options-trader</cp:lastModifiedBy>"
        f"<dcterms:created xsi:type=\"dcterms:W3CDTF\">{timestamp}</dcterms:created>"
        f"<dcterms:modified xsi:type=\"dcterms:W3CDTF\">{timestamp}</dcterms:modified>"
        "</cp:coreProperties>"
    )


def _app_props(sheets: Sequence[Sheet]) -> str:
    titles = "".join(
        f"<vt:lpstr>{_xml_escape(sheet.title)}</vt:lpstr>" for sheet in sheets
    )
    count = len(sheets)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" "
        "xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">"
        f"<TitlesOfParts><vt:vector size=\"{count}\" baseType=\"lpstr\">{titles}</vt:vector></TitlesOfParts>"
        "</Properties>"
    )


def _workbook_rels(sheet_count: int) -> str:
    relationships = []
    for index in range(1, sheet_count + 1):
        relationships.append(
            f"<Relationship Id=\"rId{index}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet{index}.xml\"/>"
        )
    style_id = sheet_count + 1
    theme_id = sheet_count + 2
    relationships.append(
        f"<Relationship Id=\"rId{style_id}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>"
    )
    relationships.append(
        f"<Relationship Id=\"rId{theme_id}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" Target=\"theme/theme1.xml\"/>"
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        + "".join(relationships)
        + "</Relationships>"
    )


def _workbook_xml(sheets: Sequence[Sheet]) -> str:
    sheet_elements = []
    for index, sheet in enumerate(sheets, start=1):
        sheet_elements.append(
            f"<sheet name=\"{_xml_escape(sheet.title)}\" sheetId=\"{index}\" r:id=\"rId{index}\"/>"
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
        "<fileVersion appName=\"xl\"/>"
        "<workbookPr defaultThemeVersion=\"124226\"/>"
        "<bookViews><workbookView/></bookViews>"
        "<sheets>"
        + "".join(sheet_elements)
        + "</sheets>"
        "</workbook>"
    )


def _styles_xml() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        "<numFmts count=\"3\">"
        "<numFmt numFmtId=\"164\" formatCode=\"$#,##0.00\"/>"
        "<numFmt numFmtId=\"165\" formatCode=\"0.00%\"/>"
        "<numFmt numFmtId=\"166\" formatCode=\"0.00\"/>"
        "</numFmts>"
        "<fonts count=\"2\">"
        "<font><sz val=\"11\"/><color theme=\"1\"/><name val=\"Calibri\"/><family val=\"2\"/></font>"
        "<font><b/><sz val=\"11\"/><color theme=\"1\"/><name val=\"Calibri\"/><family val=\"2\"/></font>"
        "</fonts>"
        "<fills count=\"4\">"
        "<fill><patternFill patternType=\"none\"/></fill>"
        "<fill><patternFill patternType=\"gray125\"/></fill>"
        f"<fill><patternFill patternType=\"solid\"><fgColor rgb=\"{HEADER_FILL}\"/><bgColor indexed=\"64\"/></patternFill></fill>"
        f"<fill><patternFill patternType=\"solid\"><fgColor rgb=\"{NET_FILL}\"/><bgColor indexed=\"64\"/></patternFill></fill>"
        "</fills>"
        "<borders count=\"2\">"
        "<border><left/><right/><top/><bottom/><diagonal/></border>"
        f"<border><left style=\"thin\"><color rgb=\"{BORDER_COLOR}\"/></left>"
        f"<right style=\"thin\"><color rgb=\"{BORDER_COLOR}\"/></right>"
        f"<top style=\"thin\"><color rgb=\"{BORDER_COLOR}\"/></top>"
        f"<bottom style=\"thin\"><color rgb=\"{BORDER_COLOR}\"/></bottom><diagonal/></border>"
        "</borders>"
        "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
        "<cellXfs count=\"13\">"
        "<xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>"  # text
        "<xf numFmtId=\"0\" fontId=\"1\" fillId=\"2\" borderId=\"1\" xfId=\"0\" applyFont=\"1\" applyFill=\"1\" applyBorder=\"1\" applyAlignment=\"1\"><alignment horizontal=\"center\"/></xf>"  # header
        "<xf numFmtId=\"164\" fontId=\"0\" fillId=\"0\" borderId=\"1\" xfId=\"0\" applyNumberFormat=\"1\" applyBorder=\"1\"/>"  # currency
        "<xf numFmtId=\"165\" fontId=\"0\" fillId=\"0\" borderId=\"1\" xfId=\"0\" applyNumberFormat=\"1\" applyBorder=\"1\"/>"  # percent
        "<xf numFmtId=\"166\" fontId=\"0\" fillId=\"0\" borderId=\"1\" xfId=\"0\" applyNumberFormat=\"1\" applyBorder=\"1\"/>"  # months
        "<xf numFmtId=\"164\" fontId=\"0\" fillId=\"3\" borderId=\"1\" xfId=\"0\" applyNumberFormat=\"1\" applyBorder=\"1\" applyFill=\"1\"/>"  # net_currency
        "<xf numFmtId=\"0\" fontId=\"0\" fillId=\"3\" borderId=\"1\" xfId=\"0\" applyFill=\"1\" applyBorder=\"1\"/>"  # net_value
        "<xf numFmtId=\"0\" fontId=\"1\" fillId=\"3\" borderId=\"1\" xfId=\"0\" applyFont=\"1\" applyFill=\"1\" applyBorder=\"1\"/>"  # net_label
        "<xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"1\" xfId=\"0\" applyBorder=\"1\"/>"  # text_border
        "<xf numFmtId=\"0\" fontId=\"1\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/>"  # metric_label
        "<xf numFmtId=\"164\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyNumberFormat=\"1\"/>"  # metric_currency
        "<xf numFmtId=\"165\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyNumberFormat=\"1\"/>"  # metric_percent
        "<xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>"  # metric_text
        "</cellXfs>"
        "<cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>"
        "<dxfs count=\"0\"/>"
        "<tableStyles count=\"0\" defaultTableStyle=\"TableStyleMedium9\" defaultPivotStyle=\"PivotStyleLight16\"/>"
        "</styleSheet>"
    )


def _sheet_xml(sheet: Sheet) -> str:
    rows = sheet.rows
    if rows:
        max_cols = max(len(row) for row in rows)
        max_rows = len(rows)
        dimension = f"A1:{_column_letter(max_cols)}{max_rows}"
    else:
        max_cols = 1
        max_rows = 0
        dimension = "A1"

    width_map = sheet.computed_widths()
    cols_xml = "".join(
        f"<col min=\"{idx}\" max=\"{idx}\" width=\"{width:.2f}\" customWidth=\"1\"/>"
        for idx, width in sorted(width_map.items())
    )
    if cols_xml:
        cols_xml = f"<cols>{cols_xml}</cols>"

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells_xml = []
        for col_index, cell in enumerate(row, start=1):
            ref = f"{_column_letter(col_index)}{row_index}"
            sid = style_id(cell.style)
            value = cell.value
            if value is None or value == "":
                cells_xml.append(f'<c r="{ref}" s="{sid}"/>')
            elif isinstance(value, (int, float)):
                cells_xml.append(f'<c r="{ref}" s="{sid}"><v>{value}</v></c>')
            else:
                text = _xml_escape(str(value))
                cells_xml.append(
                    f'<c r="{ref}" t="inlineStr" s="{sid}"><is><t>{text}</t></is></c>'
                )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells_xml)}</row>')

    sheet_data = "".join(sheet_rows)

    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
        f"<dimension ref=\"{dimension}\"/>"
        "<sheetViews><sheetView workbookViewId=\"0\"/></sheetViews>"
        "<sheetFormatPr defaultRowHeight=\"15\"/>"
        f"{cols_xml}"
        f"<sheetData>{sheet_data}</sheetData>"
        "<pageMargins left=\"0.7\" right=\"0.7\" top=\"0.75\" bottom=\"0.75\" header=\"0.3\" footer=\"0.3\"/>"
        "</worksheet>"
    )


THEME_XML = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
    "<a:theme xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" name=\"Office Theme\">"
    "<a:themeElements>"
    "<a:clrScheme name=\"Office\">"
    "<a:dk1><a:sysClr val=\"windowText\" lastClr=\"000000\"/></a:dk1>"
    "<a:lt1><a:sysClr val=\"window\" lastClr=\"FFFFFF\"/></a:lt1>"
    "<a:dk2><a:srgbClr val=\"1F497D\"/></a:dk2>"
    "<a:lt2><a:srgbClr val=\"EEECE1\"/></a:lt2>"
    "<a:accent1><a:srgbClr val=\"4F81BD\"/></a:accent1>"
    "<a:accent2><a:srgbClr val=\"C0504D\"/></a:accent2>"
    "<a:accent3><a:srgbClr val=\"9BBB59\"/></a:accent3>"
    "<a:accent4><a:srgbClr val=\"8064A2\"/></a:accent4>"
    "<a:accent5><a:srgbClr val=\"4BACC6\"/></a:accent5>"
    "<a:accent6><a:srgbClr val=\"F79646\"/></a:accent6>"
    "<a:hlink><a:srgbClr val=\"0000FF\"/></a:hlink>"
    "<a:folHlink><a:srgbClr val=\"800080\"/></a:folHlink>"
    "</a:clrScheme>"
    "<a:fontScheme name=\"Office\">"
    "<a:majorFont><a:latin typeface=\"Cambria\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/></a:majorFont>"
    "<a:minorFont><a:latin typeface=\"Calibri\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/></a:minorFont>"
    "</a:fontScheme>"
    "<a:fmtScheme name=\"Office\">"
    "<a:fillStyleLst><a:solidFill><a:schemeClr val=\"accent1\"/></a:solidFill></a:fillStyleLst>"
    "<a:lnStyleLst><a:ln w=\"9525\"><a:solidFill><a:schemeClr val=\"accent1\"/></a:solidFill></a:ln></a:lnStyleLst>"
    "<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>"
    "<a:bgFillStyleLst><a:solidFill><a:schemeClr val=\"accent1\"/></a:solidFill></a:bgFillStyleLst>"
    "</a:fmtScheme>"
    "</a:themeElements>"
    "<a:objectDefaults/>"
    "<a:extraClrSchemeLst/>"
    "</a:theme>"
)

from __future__ import annotations

import csv
import io
import zipfile
from xml.etree import ElementTree as ET

from .normalizers import get_expected_import_fields

NAMESPACE = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def parse_import_job_file(import_job) -> list[dict]:
    if not import_job.file:
        raise ValueError("Import job has no file.")

    source_type = import_job.source_type
    if source_type == import_job.SourceType.CSV:
        rows = _parse_csv(import_job.file)
    elif source_type == import_job.SourceType.XLSX:
        rows = _parse_xlsx(import_job.file)
    else:
        raise ValueError(f"Unsupported source type for preview: {source_type}")

    _validate_columns(rows, import_job.import_mode)
    return rows


def _validate_columns(rows: list[dict], import_mode: str) -> None:
    if not rows:
        return
    expected = set(get_expected_import_fields(import_mode))
    actual = {str(key).strip() for key in rows[0].keys() if str(key).strip()}
    unknown = sorted(actual - expected)
    if unknown:
        raise ValueError(f"Unsupported columns for this import mode: {', '.join(unknown)}")


def _parse_csv(field_file) -> list[dict]:
    field_file.open("rb")
    try:
        wrapper = io.TextIOWrapper(field_file.file, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(wrapper)
        return [dict(row) for row in reader]
    finally:
        field_file.close()


def _xlsx_col_to_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    result = 0
    for char in letters:
        result = result * 26 + (ord(char.upper()) - ord("A") + 1)
    return result - 1


def _parse_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for si in root.findall("main:si", NAMESPACE):
        text = "".join(node.text or "" for node in si.findall(".//main:t", NAMESPACE))
        values.append(text)
    return values


def _first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    first_sheet = workbook.find("main:sheets/main:sheet", NAMESPACE)
    if first_sheet is None:
        raise ValueError("Workbook has no sheets.")
    relationship_id = first_sheet.attrib.get(f"{{{NAMESPACE['rel']}}}id")

    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for rel in rels.findall("pkgrel:Relationship", NAMESPACE):
        if rel.attrib.get("Id") == relationship_id:
            target = rel.attrib["Target"]
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = f"xl/{target}"
            return target
    raise ValueError("Unable to resolve first worksheet.")


def _cell_value(cell, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", NAMESPACE)
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NAMESPACE))
    if value_node is None:
        return ""
    raw = value_node.text or ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return ""
    return raw


def _parse_xlsx(field_file) -> list[dict]:
    field_file.open("rb")
    try:
        with zipfile.ZipFile(field_file.file) as archive:
            shared_strings = _parse_shared_strings(archive)
            sheet_path = _first_sheet_path(archive)
            worksheet = ET.fromstring(archive.read(sheet_path))

            rows = []
            for row in worksheet.findall(".//main:sheetData/main:row", NAMESPACE):
                row_values = {}
                for cell in row.findall("main:c", NAMESPACE):
                    ref = cell.attrib.get("r", "")
                    row_values[_xlsx_col_to_index(ref)] = _cell_value(cell, shared_strings)
                rows.append(row_values)

            if not rows:
                return []

            header_row = rows[0]
            headers = [header_row.get(index, "").strip() for index in range(max(header_row.keys()) + 1)]
            parsed_rows = []
            for row_values in rows[1:]:
                row = {}
                for index, header in enumerate(headers):
                    if not header:
                        continue
                    row[header] = row_values.get(index, "")
                if any(str(value).strip() for value in row.values()):
                    parsed_rows.append(row)
            return parsed_rows
    finally:
        field_file.close()

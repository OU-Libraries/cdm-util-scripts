import csv
import json

from cdm_util_scripts.cdm_api import sniff_csv_dialect


def csv2json(input_csv_path: str, output_json_path: str, drop_empty_cells: bool = True, show_progress: bool = False) -> None:
    """Transpose a CSV file into a list of JSON objects (cdm-catcher JSON edits)"""
    with open(input_csv_path, mode="r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp, dialect=sniff_csv_dialect(fp))
        rows = []
        for rownum, row in enumerate(reader, start=1):
            if not row.get("dmrecord"):
                raise ValueError(f"CSV row {rownum} is missing dmrecord number")
            if drop_empty_cells:
                json_row = {nick: value.strip() for nick, value in row.items() if value and not value.isspace()}
            else:
                json_row = {nick: value.strip() for nick, value in row.items()}
            rows.append(json_row)

    with open(output_json_path, mode="w", encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2)

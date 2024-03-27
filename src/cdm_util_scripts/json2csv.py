import csv
import json

from typing import List, Union


def json2csv(
    input_json_path: str,
    output_csv_path: str,
    csv_dialect: Union[str, csv.Dialect],
    show_progress: bool = False
) -> None:
    """Transpose a list of JSON objects (cdm-catcher JSON edits) into a CSV file."""
    with open(input_json_path, mode="r", encoding="utf-8") as fp:
        input_json = json.load(fp)
    if not isinstance(input_json, list):
        raise ValueError("invalid input JSON: must be a list of rows")
    fieldnames: List[str] = []
    for edit in input_json:
        if not isinstance(edit, dict):
            raise ValueError("invalid input JSON: rows must be JSON objects")
        for column_name in edit:
            if column_name not in fieldnames:
                fieldnames.append(column_name)
    with open(output_csv_path, mode="w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, dialect=csv_dialect, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(input_json)

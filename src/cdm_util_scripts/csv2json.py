import csv
import json

from cdm_api import sniff_csv_dialect


def csv2json(input_csv_path: str, output_json_path: str) -> None:
    with open(input_csv_path, mode="r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp, dialect=sniff_csv_dialect(fp))
        rows = [row for row in reader]

    with open(output_json_path, mode="w", encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2)

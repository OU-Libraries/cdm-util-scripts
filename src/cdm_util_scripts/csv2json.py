import csv
import json


def csv2json(input_csv_path: str, output_json_path: str, input_csv_dialect: str) -> None:
    with open(input_csv_path, mode='r', encoding="utf-8") as fp:
        reader = csv.DictReader(fp, dialect=input_csv_dialect)
        rows = [row for row in reader]

    with open(output_json_path, mode='w', encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2)

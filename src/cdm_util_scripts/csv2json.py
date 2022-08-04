import csv
import json
import argparse


def csv2json(input_csv_path: str, output_json_path: str, input_csv_dialect: str) -> None:
    with open(input_csv_path, mode='r', encoding="utf-8") as fp:
        reader = csv.DictReader(fp, dialect=input_csv_dialect)
        rows = [row for row in reader]

    with open(output_json_path, mode='w', encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Transpose CSV or TSV files into lists of JSON objects")
    parser.add_argument('input_csv_path',
                        type=str,
                        help="Path to delimited file")
    parser.add_argument('output_json_path',
                        type=str,
                        help="Path to output JSON file")
    parser.add_argument('--dialect',
                        action='store',
                        default='excel',
                        choices=csv.list_dialects(),
                        type=str,
                        help=f"Specify delimited file format")
    args = parser.parse_args()

    csv2json(
        input_csv_path=args.input_csv_path,
        output_json_path=args.output_json_path,
        input_csv_dialect=args.dialect,
    )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

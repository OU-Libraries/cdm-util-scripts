import csv
import json
import argparse


dialects = {
    'csv': 'excel',
    'tsv': 'excel-tab',
    'unix': 'unix'
}


def main():
    parser = argparse.ArgumentParser(description="Transpose CSV or TSV files into lists of JSON objects")
    parser.add_argument('input_path',
                        metavar='input_path',
                        type=str,
                        help="Path to delimited file")
    parser.add_argument('output_path',
                        metavar='output_path',
                        type=str,
                        help="Path to output JSON file")
    parser.add_argument('--format',
                        action='store',
                        default='csv',
                        choices=list(dialects.keys()),
                        type=str,
                        help=f"Specify delimited file format, default csv")
    parser.add_argument('--encoding',
                        action='store',
                        default='utf-8',
                        type=str,
                        help=f"Specify the delimited file format encoding, default utf-8")
    args = parser.parse_args()

    with open(args.input_path, mode='r', encoding=args.encoding) as fp:
        reader = csv.DictReader(fp, dialect=dialects[args.format])
        rows = [row for row in reader]

    with open(args.output_path, mode='w') as fp:
        json.dump(rows, fp, indent=2)


if __name__ == '__main__':
    main()

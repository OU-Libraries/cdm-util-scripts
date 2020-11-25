import csv
import json
import argparse

dialects = {
    'csv': 'excel',
    'tsv': 'excel-tab',
    'unix': 'unix'
}
dialect_default = 'csv'
encoding_default = 'utf-8'

def main():
    parser = argparse.ArgumentParser(description="Transform FromThePage csv or tsv exports to cdm-catcher edit JSON")
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
                        type=str,
                        help=f"Specify delimited file format, any of {', '.join(repr(key) for key in dialects.keys())}, default {dialect_default!r}")
    parser.add_argument('--encoding',
                        action='store',
                        type=str,
                        help=f"Specify the delimited file format encoding, default {encoding_default!r}")
    args = parser.parse_args()

    with open(args.input_path,
              mode='r',
              encoding=args.encoding or encoding_default) as fp:
        reader = csv.DictReader(fp,
                                dialect=dialects[args.format or dialect_default])
        rows = [row for row in reader]

    with open(args.output_path, mode='w') as fp:
        json.dump(rows, fp, indent=2)


if __name__ == '__main__':
    main()

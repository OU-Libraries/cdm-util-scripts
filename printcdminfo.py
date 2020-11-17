import requests

import argparse
import csv
import json
from io import StringIO
from typing import Dict, Sequence, Callable, Any


def print_as_table(rows: Sequence[dict]) -> None:
    widths = {name: col_max(rows, name) + 1 for name in rows[0].keys()}
    print(ljust_row({key: key for key in rows[0].keys()}, widths, serializer=str))
    print(ljust_row({key: '-' * len(key) for key in widths.keys()}, widths, serializer=str))
    for row in rows:
        print(ljust_row(row, widths))


def col_max(rows: Sequence[dict], col_name: str) -> int:
    return max(len(repr(col_name)),
               len(repr(max(rows, key=lambda row: len(repr(row[col_name])))[col_name])))


def ljust_row(row: dict,
              widths: Dict[str, int],
              default_width: int = 8,
              serializer: Callable[[Any], str] = repr) -> str:
    return ''.join(serializer(value).ljust(widths.get(key, default_width))
                   for key, value in row.items())


def print_as_csv(dm_json):
    with StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=dm_json[0].keys())
        writer.writeheader()
        writer.writerows(dm_json)
        print(output.getvalue(), end='')


def print_as_json(dm_json):
    print(dm_json.dumps(dm_json))


output_formats = {
    'json': print_as_json,
    'csv': print_as_csv,
    'table': print_as_table
}


def main():
    parser = argparse.ArgumentParser(description="Print CONTENTdm collection information")
    parser.add_argument('repository_url',
                        type=str,
                        help="CONTENTdm repository URL")
    parser.add_argument('--alias',
                        action='store',
                        type=str,
                        help="CONTENTdm collection alias")
    parser.add_argument('--output',
                        action='store',
                        help=f"Print output as any of {', '.join(repr(key) for key in output_formats.keys())}")
    parser.add_argument('--columns',
                        type=str,
                        action='store',
                        help="Specify columns to print in a column seperated string, as --columns 'nick,name'")
    args = parser.parse_args()
    base_url = args.repository_url.rstrip('/')
    if args.alias:
        query_url = '/'.join([base_url,
                              'digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldInfo',
                              args.alias,
                              'json'])
    else:
        query_url = '/'.join([base_url,
                              'digital/bl/dmwebservices/index.php?q=dmGetCollectionList/json'])
    response = requests.get(query_url)
    response.raise_for_status()
    dm_result = response.json()
    if 'code' in dm_result:
        print(dm_result['message'])
    else:
        if args.columns:
            columns = set(args.columns.split(','))
            dm_result = [{key: value for key, value in entry.items() if key in columns}
                         for entry in dm_result]
        output_formats[args.output or 'table'](dm_result)


if __name__ == '__main__':
    main()

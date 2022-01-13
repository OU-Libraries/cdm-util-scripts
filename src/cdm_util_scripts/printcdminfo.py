import requests
from rich.console import Console
from rich.table import Table

import argparse
import csv
import json
import sys
from io import StringIO
from typing import Dict, Sequence, Callable, Any

from cdm_util_scripts import cdm_api


def print_as_table(rows: Sequence[dict]) -> None:
    table = Table()
    column_names = list(rows[0])
    for name in column_names:
        table.add_column(name)
    for row in rows:
        table.add_row(*(repr(row[name]) for name in column_names))
    console = Console()
    console.print(table)


def print_as_csv(dm_json):
    with StringIO() as output:
        writer = csv.DictWriter(output, fieldnames=dm_json[0].keys())
        writer.writeheader()
        writer.writerows(dm_json)
        print(output.getvalue(), end="")


def print_as_json(dm_json):
    print(json.dumps(dm_json, indent=2))


output_formats = {"json": print_as_json, "csv": print_as_csv, "table": print_as_table}


def main():
    parser = argparse.ArgumentParser(
        description="Print CONTENTdm collection information",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("repository_url", type=str, help="CONTENTdm repository URL")
    parser.add_argument(
        "--alias", action="store", type=str, help="CONTENTdm collection alias"
    )
    parser.add_argument(
        "--output",
        type=str,
        action="store",
        choices=list(output_formats.keys()),
        default="table",
        help=f"Output format",
    )
    parser.add_argument(
        "--columns",
        type=str,
        action="store",
        help="Specify columns to print in a comma separated string, as --columns name,nick",
    )
    args = parser.parse_args()

    try:
        if args.alias:
            dm_result = cdm_api.get_collection_field_info(
                args.repository_url, args.alias, requests
            )
        else:
            dm_result = cdm_api.get_collection_list(args.repository_url, requests)
    except cdm_api.DmError as err:
        print(err, file=sys.stderr)
        sys.exit(1)

    if args.columns:
        columns = args.columns.split(",")
        try:
            dm_result = [
                {column: entry[column] for column in columns} for entry in dm_result
            ]
        except KeyError as err:
            print(f"{err.args[0]!r} is not a valid column name", file=sys.stderr)
            sys.exit(1)
    if args.output and args.output not in output_formats:
        print(f"{args.output!r} is not a valid output format", file=sys.stderr)
        sys.exit(1)
    output_formats[args.output](dm_result)


if __name__ == "__main__":
    main()

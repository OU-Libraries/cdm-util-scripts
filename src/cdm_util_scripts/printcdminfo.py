import requests

import argparse
import csv
import json
import sys

from typing import Dict, Iterable

from cdm_util_scripts import cdm_api


def print_as_records(dm_result: Iterable[Dict[str, str]]) -> None:
    max_key_len = max(len(key) for key in dm_result[0].keys())
    for record in dm_result:
        for key, value in record.items():
            print(f"{key.rjust(max_key_len)} : {value!r}")
        if record is not dm_result[-1]:
            print(end="\n")


def print_as_csv(dm_result: Iterable[Dict[str, str]]) -> None:
    writer = csv.DictWriter(sys.stdout, fieldnames=dm_result[0].keys())
    writer.writeheader()
    writer.writerows(dm_result)


def print_as_json(dm_result: Iterable[Dict[str, str]]) -> None:
    print(json.dumps(dm_result, indent=2))


OUTPUT_FORMATS = {"json": print_as_json, "csv": print_as_csv, "records": print_as_records}


def main() -> int:
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
        choices=list(OUTPUT_FORMATS.keys()),
        default="records",
        help="Output format",
    )
    parser.add_argument(
        "--columns",
        type=str,
        action="store",
        help="Specify columns to print in a comma separated string, as --columns name,nick",
    )
    args = parser.parse_args()

    with requests.Session() as session:
        if args.alias:
            dm_result = cdm_api.get_collection_field_info(
                repo_url=args.repository_url,
                collection_alias=args.alias,
                session=session,
            )
        else:
            dm_result = cdm_api.get_collection_list(
                repo_url=args.repository_url, session=session
            )

    if args.columns:
        columns = args.columns.split(",")
        dm_result = [
            {column: entry[column] for column in columns} for entry in dm_result
        ]

    OUTPUT_FORMATS[args.output](dm_result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

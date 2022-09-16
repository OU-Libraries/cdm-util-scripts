import argparse
import requests

import json
import csv
import sys

from typing import Optional, Sequence, Dict

from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api
from cdm_util_scripts import catcherdiff
from cdm_util_scripts import csv2json
from cdm_util_scripts import ftptransc2catcher
from cdm_util_scripts import ftpstruct2catcher
from cdm_util_scripts import scanftpfields
from cdm_util_scripts import gui


def main(test_args: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="cdm-util-scripts")
    subparsers = parser.add_subparsers()

    # catcherdiff
    catcherdiff_subparser = subparsers.add_parser(
        "catcherdiff",
        help=catcherdiff.catcherdiff.__doc__,
    )
    catcherdiff_subparser.add_argument(
        "cdm_instance_url", help="CONTENTdm instance URL"
    )
    catcherdiff_subparser.add_argument(
        "cdm_collection_alias", help="CONTENTdm collection alias"
    )
    catcherdiff_subparser.add_argument(
        "catcher_json_file_path", help="Path to cdm-catcher JSON file"
    )
    catcherdiff_subparser.add_argument(
        "report_file_path", help="Report output file path"
    )
    catcherdiff_subparser.add_argument(
        "-c",
        "--check-vocabs",
        action="store_const",
        const=True,
        help="Check controlled vocabulary terms",
    )
    catcherdiff_subparser.set_defaults(func=catcherdiff.catcherdiff)

    # csv2json
    csv2json_subparser = subparsers.add_parser(
        "csv2json", help=csv2json.csv2json.__doc__
    )
    csv2json_subparser.add_argument("input_csv_path", help="Path to delimited file")
    csv2json_subparser.add_argument("output_json_path", help="Path to output JSON file")
    csv2json_subparser.set_defaults(func=csv2json.csv2json)

    # ftptransc2catcher
    ftptransc2catcher_subparser = subparsers.add_parser(
        "ftptransc2catcher",
        help=ftptransc2catcher.ftptransc2catcher.__doc__,
    )
    ftptransc2catcher_subparser.add_argument(
        "manifests_listing_path",
        help="Path to file listing FromThePage manifest links",
    )
    ftptransc2catcher_subparser.add_argument(
        "transcript_nick",
        help="CONTENTdm field nickname for the transcript field",
    )
    ftptransc2catcher_subparser.add_argument(
        "output_file_path",
        help="Path to write cdm-catcher JSON file",
    )
    ftptransc2catcher_subparser.add_argument(
        "--transcript-type",
        default="Verbatim Plaintext",
        help="FromThePage transcript type",
    )
    ftptransc2catcher_subparser.set_defaults(func=ftptransc2catcher.ftptransc2catcher)

    # ftpstruct2catcher
    ftpstruct2catcher_subparser = subparsers.add_parser(
        "ftpstruct2catcher",
        help=ftpstruct2catcher.ftpstruct2catcher.__doc__,
    )
    ftpstruct2catcher_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    ftpstruct2catcher_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    ftpstruct2catcher_subparser.add_argument(
        "field_mapping_csv_path",
        help="CSV file of FromThePage field labels mapped to CONTENTdm field nicknames",
    )
    ftpstruct2catcher_subparser.add_argument(
        "output_file_path", help="Path to write cdm-catcher JSON file"
    )
    ftpstruct2catcher_subparser.add_argument(
        "-l",
        "--level",
        action="store",
        choices=[level.value for level in ftpstruct2catcher.Level],
        default=ftpstruct2catcher.Level.AUTO.value,
        help="Description level to use",
    )
    ftpstruct2catcher_subparser.set_defaults(func=ftpstruct2catcher.ftpstruct2catcher)

    # scanftpfields
    scanftpfields_subparser = subparsers.add_parser(
        "scanftpfields",
        help=scanftpfields.scanftpfields.__doc__,
    )
    scanftpfields_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    scanftpfields_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    scanftpfields_subparser.add_argument("report_path", help="Report file path")
    scanftpfields_subparser.set_defaults(func=scanftpfields.scanftpfields)

    # GUI
    gui_subparser = subparsers.add_parser(
        "gui",
        help="Launch a GUI version of this utility",
    )
    gui_subparser.set_defaults(func=gui.gui)

    # ftpinfo
    ftpinfo_subparser = subparsers.add_parser(
        "ftpinfo", help="Print FromThePage project information"
    )
    ftpinfo_subparser.add_argument("slug", help="FromThePage user slug")
    ftpinfo_subparser.add_argument(
        "-f",
        "--output-format",
        action="store",
        choices=list(OUTPUT_FORMATS),
        default="records",
        help="Output format",
    )
    ftpinfo_subparser.set_defaults(func=ftpinfo)

    # cdminfo
    cdminfo_subparser = subparsers.add_parser(
        "cdminfo",
        help="Print CONTENTdm instance or collection information",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cdminfo_subparser.add_argument("instance_url", help="CONTENTdm repository URL")
    cdminfo_subparser.add_argument(
        "-a", "--alias", action="store", help="CONTENTdm collection alias"
    )
    cdminfo_subparser.add_argument(
        "-f",
        "--output-format",
        action="store",
        choices=list(OUTPUT_FORMATS),
        default="records",
        help="Output format",
    )
    cdminfo_subparser.add_argument(
        "-c",
        "--columns",
        action="store",
        help="Specify columns to print in a comma separated string, as --columns name,nick",
    )
    cdminfo_subparser.set_defaults(func=cdminfo)

    args = parser.parse_args(test_args)
    args.func(**{key: value for key, value in vars(args).items() if key != "func"})

    return 0


def ftpinfo(slug: str, output_format: str) -> None:
    with requests.Session() as session:
        ftp_instance = ftp_api.FtpInstance(url=ftp_api.FTP_HOSTED_URL)
        ftp_projects = ftp_instance.request_projects(slug=slug, session=session)

    records = []
    for project in ftp_projects.projects:
        records.append(
            {
                "@id": project.url,
                "label": project.label,
            }
        )

    OUTPUT_FORMATS[output_format](records)


def cdminfo(
    instance_url: str,
    alias: Optional[str],
    columns: Optional[str],
    output_format: str,
) -> None:
    with requests.Session() as session:
        if alias is not None:
            dm_result = [
                field_info._asdict()
                for field_info in cdm_api.request_field_infos(
                    instance_url=instance_url,
                    collection_alias=alias,
                    session=session,
                )
            ]
        else:
            dm_result = [
                collection_info._asdict()
                for collection_info in cdm_api.request_collection_list(
                    instance_url=instance_url, session=session
                )
            ]

    if columns is not None:
        column_names = columns.split(",")
        dm_result = [
            {column: entry[column] for column in column_names} for entry in dm_result
        ]

    OUTPUT_FORMATS[output_format](dm_result)


def print_as_records(records: Sequence[Dict[str, str]]) -> None:
    max_key_len = max(len(key) for key in records[0])
    for record in records:
        for key, value in record.items():
            print(f"{key.rjust(max_key_len)} : {value!r}")
        if record is not records[-1]:
            print(end="\n")


def print_as_csv(records: Sequence[Dict[str, str]]) -> None:
    writer = csv.DictWriter(sys.stdout, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)


def print_as_json(records: Sequence[Dict[str, str]]) -> None:
    print(json.dumps(records, indent=2))


OUTPUT_FORMATS = {
    "json": print_as_json,
    "csv": print_as_csv,
    "records": print_as_records,
}


if __name__ == "__main__":
    raise SystemExit(main())

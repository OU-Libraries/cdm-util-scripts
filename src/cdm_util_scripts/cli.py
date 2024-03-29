import argparse
import requests

import json
import csv
import sys
import itertools

from typing import Optional, Sequence, Dict, List

from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api
from cdm_util_scripts import catcherdiff
from cdm_util_scripts import catchercombineterms
from cdm_util_scripts import catchertidy
from cdm_util_scripts import csv2json
from cdm_util_scripts import json2csv
from cdm_util_scripts import ftptransc2catcher
from cdm_util_scripts import ftpstruct2catcher
from cdm_util_scripts import scanftpschema
from cdm_util_scripts import gui


def catchertidy_compound_options():
    options = "wrls"
    combos: List[str] = []
    for r in range(2, len(options) + 1):
        combos.extend(
            "".join(combo) for combo in itertools.combinations(options, r)
        )
    return combos


def main(test_args: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="cdm-util-scripts")
    subparsers = parser.add_subparsers()

    # catcherdiff
    catcherdiff_subparser = subparsers.add_parser(
        "catcherdiff",
        help=catcherdiff.catcherdiff.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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

    # catchercombineterms
    catchercombineterms_subparser = subparsers.add_parser(
        "catchercombineterms",
        help=catchercombineterms.catchercombineterms.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    catchercombineterms_subparser.add_argument(
        "cdm_instance_url", help="CONTENTdm instance URL"
    )
    catchercombineterms_subparser.add_argument(
        "cdm_collection_alias", help="CONTENTdm collection alias"
    )
    catchercombineterms_subparser.add_argument(
        "catcher_json_file_path", help="Path to cdm-catcher JSON file"
    )
    catchercombineterms_subparser.add_argument(
        "output_file_path",
        help="Path to write combined cdm-catcher JSON file",
    )
    catchercombineterms_subparser.add_argument(
        "-u",
        "--unsorted",
        action="store_false",
        help="Do not sort combined terms",
    )

    def catchercombineterms_func(*args, unsorted, **kwargs):
        catchercombineterms.catchercombineterms(*args, sort_terms=unsorted, **kwargs)

    catchercombineterms_subparser.set_defaults(func=catchercombineterms_func)

    # catchertidy
    catchertidy_subparser = subparsers.add_parser(
        "catchertidy",
        help=catchertidy.catchertidy.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    catchertidy_subparser.add_argument(
        "-w", "--normalize-whitespace", action="append", metavar="CATCHER_NICK",
        help="catcher edit nicks to normalize whitespace"
    )
    catchertidy_subparser.add_argument(
        "-r", "--replace-smart-chars", action="append", metavar="CATCHER_NICK",
        help="catcher edit nicks to replace smart characters"
    )
    catchertidy_subparser.add_argument(
        "-l", "--normalize-lcsh", action="append", metavar="CATCHER_NICK",
        help="catcher edit nicks to normalize LC subjects"
    )
    catchertidy_subparser.add_argument(
        "-s", "--sort-terms", action="append", metavar="CATCHER_NICK",
        help="catcher edit nicks to sort controlled vocab terms"
    )
    for option in catchertidy_compound_options():
        help_list = ", ".join(f"-{o}" for o in option)
        catchertidy_subparser.add_argument(
            f"--{option}", action="append", metavar="CATCHER_NICK",
            help=f"Do all of {help_list} to edit nick"
        )
    catchertidy_subparser.add_argument(
        "-e", "--no-sep-space", action="store_true",
        help="Don't use spaces around subfield delimiters when normalizing LCSH"
    )
    catchertidy_subparser.add_argument(
        "catcher_json_file_path",
        help="Path to cdm-catcher JSON file",
    )
    catchertidy_subparser.add_argument(
        "output_file_path",
        help="Path to write tidied cdm-catcher JSON file",
    )

    def catchertidy_func(
            *,
            normalize_whitespace,
            replace_smart_chars,
            normalize_lcsh,
            sort_terms,
            no_sep_space,
            catcher_json_file_path,
            output_file_path,
            **kwargs
    ):
        normalize_whitespace = normalize_whitespace or []
        replace_smart_chars = replace_smart_chars or []
        normalize_lcsh = normalize_lcsh or []
        sort_terms = sort_terms or []
        for key, value in kwargs.items():
            if not value:
                continue
            if "w" in key:
                normalize_whitespace.extend(value)
            if "r" in key:
                replace_smart_chars.extend(value)
            if "l" in key:
                normalize_lcsh.extend(value)
            if "s" in key:
                sort_terms.extend(value)
        catchertidy.catchertidy(
            catcher_json_file_path=catcher_json_file_path,
            output_file_path=output_file_path,
            normalize_whitespace=normalize_whitespace,
            replace_smart_chars=replace_smart_chars,
            normalize_lcsh=normalize_lcsh,
            sort_terms=sort_terms,
            lcsh_separator_spaces=not no_sep_space,
        )

    catchertidy_subparser.set_defaults(func=catchertidy_func)

    # csv2json
    csv2json_subparser = subparsers.add_parser(
        "csv2json",
        help=csv2json.csv2json.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    csv2json_subparser.add_argument("input_csv_path", help="Path to delimited file")
    csv2json_subparser.add_argument("output_json_path", help="Path to output JSON file")
    csv2json_subparser.add_argument("-k", "--keep-empty-cells", action="store_false", help="Include edits for empty cells in CSV")
    csv2json_subparser.add_argument(
        "-d",
        "--csv-dialect",
        action="store",
        choices=csv.list_dialects(),  # TODO: offer a sniffer option?
        default="google-csv",
        help="Dialect of input CSV",
    )

    def csv2json_func(*args, keep_empty_cells, **kwargs):
        csv2json.csv2json(*args, drop_empty_cells=keep_empty_cells, **kwargs)

    csv2json_subparser.set_defaults(func=csv2json_func)

    # json2csv
    json2csv_subparser = subparsers.add_parser(
        "json2csv",
        help=json2csv.json2csv.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    json2csv_subparser.add_argument("input_json_path", help="Path to input JSON file")
    json2csv_subparser.add_argument("output_csv_path", help="Path to output CSV file")
    json2csv_subparser.add_argument(
        "-d",
        "--csv-dialect",
        action="store",
        choices=csv.list_dialects(),
        default="excel-tab",
        help="CSV dialect to use for output"
    )
    json2csv_subparser.set_defaults(func=json2csv.json2csv)

    # ftptransc2catcher
    ftptransc2catcher_subparser = subparsers.add_parser(
        "ftptransc2catcher",
        help=ftptransc2catcher.ftptransc2catcher.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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

    # scanftpschema
    scanftpschema_subparser = subparsers.add_parser(
        "scanftpschema",
        help=scanftpschema.scanftpschema.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    scanftpschema_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    scanftpschema_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    scanftpschema_subparser.add_argument("report_path", help="Report file path")
    scanftpschema_subparser.set_defaults(func=scanftpschema.scanftpschema)

    # GUI
    gui_subparser = subparsers.add_parser(
        "gui",
        help="Launch a GUI version of this utility",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    gui_subparser.set_defaults(func=gui.gui)

    # ftpinfo
    ftpinfo_subparser = subparsers.add_parser(
        "ftpinfo",
        help="Print FromThePage project information",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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

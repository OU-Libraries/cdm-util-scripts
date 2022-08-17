import argparse
import csv

from typing import Optional, Sequence

from cdm_util_scripts import ftp_api
from cdm_util_scripts import catcherdiff
from cdm_util_scripts import csv2catcher
from cdm_util_scripts import csv2json
from cdm_util_scripts import ftpfields2catcher
from cdm_util_scripts import ftptr2catcher
from cdm_util_scripts import ftpmdc2catcher
from cdm_util_scripts import scanftpfields
from cdm_util_scripts import scanftpvocabs


def main(test_args: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="cdm-util-scripts")
    subparsers = parser.add_subparsers()

    # catcherdiff
    catcherdiff_subparser = subparsers.add_parser(
        "catcherdiff",
        help="Generate a HTML report on what CONTENTdm field values will change if a cdm-catcher JSON edit is implemented",
    )
    catcherdiff_subparser.add_argument("cdm_instance_url", help="CONTENTdm instance URL")
    catcherdiff_subparser.add_argument(
        "cdm_collection_alias", help="CONTENTdm collection alias"
    )
    catcherdiff_subparser.add_argument(
        "catcher_json_file_path", help="Path to cdm-catcher JSON file"
    )
    catcherdiff_subparser.add_argument("report_file_path", help="Diff output file path")
    catcherdiff_subparser.add_argument(
        "--check-vocabs",
        action="store_const",
        const=True,
        help="Check controlled vocabulary terms",
    )
    catcherdiff_subparser.set_defaults(func=catcherdiff.catcherdiff)

    # csv2catcher
    csv2catcher_subparser = subparsers.add_parser(
        "csv2catcher",
        help="Reconcile and translate a CSV into cdm-catcher JSON edits",
    )
    csv2catcher_subparser.add_argument(
        "reconciliation_config_path",
        help="Path to a collection reconciliation JSON configuration file",
    )
    csv2catcher_subparser.add_argument(
        "column_mapping_csv_path",
        help="Path to CSV with columns 'name' and 'nick' mapping column names to CONTENTdm field nicknames",
    )
    csv2catcher_subparser.add_argument(
        "field_data_csv_path", help="Path to field data CSV"
    )
    csv2catcher_subparser.add_argument(
        "output_file_path", help="Path to output cdm-catcher JSON"
    )
    csv2catcher_subparser.set_defaults(func=csv2catcher.csv2catcher)

    # csv2json
    csv2json_subparser = subparsers.add_parser(
        "csv2json",
        help="Transpose CSV files into lists of JSON objects (cdm-catcher JSON edits)",
    )
    csv2json_subparser.add_argument("input_csv_path", help="Path to delimited file")
    csv2json_subparser.add_argument("output_json_path", help="Path to output JSON file")
    csv2json_subparser.add_argument(
        "--dialect",
        action="store",
        default="excel",
        choices=csv.list_dialects(),
        help="Input CSV delimited file format",
    )
    csv2json_subparser.set_defaults(func=csv2json.csv2json)

    # ftpfields2catcher
    ftpfields2catcher_subparser = subparsers.add_parser(
        "ftpfields2catcher",
        help="Get field-based transcription metadata from FromThePage as cdm-catcher JSON edits",
    )
    ftpfields2catcher_subparser.add_argument(
        "match_mode",
        choices=[
            ftpfields2catcher.MatchModes.by_object,
            ftpfields2catcher.MatchModes.by_page,
        ],
        help="Mode for matching FromThePage metadata to CONTENTdm objects",
    )
    ftpfields2catcher_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    ftpfields2catcher_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    ftpfields2catcher_subparser.add_argument(
        "field_mapping_csv_path",
        help="CSV file of FromThePage field labels mapped to CONTENTdm nicknames",
    )
    ftpfields2catcher_subparser.add_argument(
        "output_file_path", help="File name for cdm-catcher JSON output"
    )
    ftpfields2catcher_subparser.set_defaults(func=ftpfields2catcher.ftpfields2catcher)

    # ftptr2catcher
    ftptr2catcher_subparser = subparsers.add_parser(
        "ftptr2catcher",
        help="Get transcripts from a list of FromThePage manifests as cdm-catcher JSON edits",
    )
    ftptr2catcher_subparser.add_argument(
        "manifests_listing_path",
        help="Path to file listing FromThePage manifest links",
    )
    ftptr2catcher_subparser.add_argument(
        "transcript_nick",
        help="CONTENTdm field nickname for the transcript field",
    )
    ftptr2catcher_subparser.add_argument(
        "output_file_path",
        help="Path to write cdm-catcher JSON file",
    )
    ftptr2catcher_subparser.add_argument(
        "--transcript-type",
        default="Verbatim Plaintext",
        help="FromThePage transcript type",
    )
    ftptr2catcher_subparser.set_defaults(func=ftptr2catcher.ftptr2catcher)

    # ftpmdc2catcher
    ftpmdc2catcher_subparser = subparsers.add_parser(
        "ftpmdc2catcher",
        help="Get FromThePage Metadata Creation project data as cdm-catcher JSON edits",
    )
    ftpmdc2catcher_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    ftpmdc2catcher_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    ftpmdc2catcher_subparser.add_argument(
        "field_mapping_csv_path",
        help="CSV file of FromThePage field labels mapped to CONTENTdm field nicknames",
    )
    ftpmdc2catcher_subparser.add_argument(
        "output_file_path", help="Path to write cdm-catcher JSON file"
    )
    ftpmdc2catcher_subparser.set_defaults(func=ftpmdc2catcher.ftpmdc2catcher)

    # scanftpfields
    scanftpfields_subparser = subparsers.add_parser(
        "scanftpfields",
        help="Scan and report on a FromThePage collection's field-based transcription labels",
    )
    scanftpfields_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    scanftpfields_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    scanftpfields_subparser.add_argument(
        "--report-parent-path",
        default=".",
        help="Directory to put report in",
    )
    scanftpfields_subparser.set_defaults(func=scanftpfields.scanftpfields)

    # scanftpvocabs
    scanftpvocabs_subparser = subparsers.add_parser(
        "scanftpvocabs",
        help="Cross check a FromThePage collection against CONTENTdm controlled vocabs",
    )
    scanftpvocabs_subparser.add_argument("ftp_slug", help="FromThePage user slug")
    scanftpvocabs_subparser.add_argument(
        "ftp_project_name", help="FromThePage project name"
    )
    scanftpvocabs_subparser.add_argument(
        "cdm_repo_url", help="CONTENTdm repository URL"
    )
    scanftpvocabs_subparser.add_argument(
        "cdm_collection_alias", help="CONTENTdm collection alias"
    )
    scanftpvocabs_subparser.add_argument(
        "field_mapping_csv_path",
        help="CSV file of FromThePage field labels mapped to CONTENTdm nicknames",
    )
    scanftpvocabs_subparser.add_argument(
        "--label",
        choices=list(ftp_api.RENDERING_EXTRACTORS),
        default="XHTML Export",
        help="Choose the export to use for parsing fields",
    )
    scanftpvocabs_subparser.add_argument(
        "--report-parent",
        default=".",
        help="Directory to put report in",
    )
    scanftpvocabs_subparser.set_defaults(func=scanftpvocabs.scanftpvocabs)

    args = parser.parse_args(test_args)
    args.func(**{key: value for key, value in vars(args).items() if key != "func"})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

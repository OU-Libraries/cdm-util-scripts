from requests import Session
import jinja2

import argparse
import json
from datetime import datetime
from collections import defaultdict

from cdm_util_scripts import catcherdiff
from cdm_util_scripts import ftpfields2catcher
from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api

from typing import Dict, List, Tuple


def scan_vocabs(
        ftp_collection: ftp_api.FTPCollection,
        field_mapping: Dict[str, List[str]],
        vocabs_index: Dict[str, Dict[str, str]],
        vocabs: Dict[str, Dict[str, List[str]]]
) -> Tuple[Dict[str, Dict[str, ftp_api.FTPPage]], List[str]]:
    mapped_nicks = set()
    for nicks in field_mapping.values():
        mapped_nicks.update(nicks)
    mapped_controlled_fields = set(vocabs_index.keys()) & mapped_nicks
    unmapped_controlled_fields = set(vocabs_index.keys()) - mapped_controlled_fields

    # Follow vocabs_index order which is CONTENTdm field order
    mapped_controlled_fields = [nick for nick in vocabs_index.keys()
                                if nick in mapped_controlled_fields]
    unmapped_controlled_fields = [nick for nick in vocabs_index.keys()
                                  if nick in unmapped_controlled_fields]

    field_scans = {nick: defaultdict(list) for nick in mapped_controlled_fields}
    for ftp_work in ftp_collection.works:
        for ftp_page in ftp_work.pages:
            if not ftp_page.fields:
                continue
            item_info = ftpfields2catcher.apply_field_mapping(
                ftp_fields=ftp_page.fields,
                field_mapping=field_mapping,
            )
            for nick in mapped_controlled_fields:
                index = vocabs_index[nick]
                terms = item_info[nick].split('; ')
                vocab = vocabs[index['type']][index['name']]
                for term in terms:
                    if term and term not in vocab:
                        field_scans[nick][term].append(ftp_page)
    return field_scans, unmapped_controlled_fields


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template('scanftpvocabs-report.html.j2').render(report)


def scanftpvocabs(
        ftp_slug: str,
        ftp_project_name: str,
        cdm_repo_url: str,
        cdm_collection_alias: str,
        field_mapping_csv_path: str,
        report_format: str,
        rendering_label: str
) -> None:
    field_mapping = cdm_api.read_csv_field_mapping(field_mapping_csv_path)

    with Session() as session:
        ftp_collection = ftp_api.get_and_load_ftp_collection(
            slug=ftp_slug,
            collection_name=ftp_project_name,
            rendering_label=rendering_label,
            session=session
        )
        cdm_fields_info = cdm_api.get_collection_field_info(
            repo_url=cdm_repo_url,
            collection_alias=cdm_collection_alias,
            session=session
        )
        vocabs_index = catcherdiff.build_vocabs_index(cdm_fields_info=cdm_fields_info)
        vocabs = catcherdiff.get_vocabs(
            cdm_repo_url=cdm_repo_url,
            cdm_collection_alias=cdm_collection_alias,
            vocabs_index=vocabs_index,
            session=session
        )

    field_scans, unmapped_controlled_fields = scan_vocabs(
        ftp_collection=ftp_collection,
        field_mapping=field_mapping,
        vocabs_index=vocabs_index,
        vocabs=vocabs
    )

    print("Compiling report...")
    report_datetime = datetime.now()
    report = {
        "ftp_slug": ftp_slug,
        "ftp_project_name": ftp_project_name,
        "cdm_repo_url": cdm_repo_url,
        "cdm_collection_alias": cdm_collection_alias,
        "output": report_format,
        "label": rendering_label,
        "field_mapping_csv": field_mapping_csv_path,
        'report_datetime': report_datetime.isoformat(),
        'cdm_fields_info': cdm_fields_info,
        'vocabs_index': vocabs_index,
        'vocabs': vocabs,
        'field_mapping': field_mapping,
        'unmapped_controlled_fields': unmapped_controlled_fields,
        'field_scans': field_scans,
    }

    if report_format == 'json':
        report_str = json.dumps(report, indent=2)
    elif report_format == 'html':
        report_str = report_to_html({
            **report,
            'cdm_nick_to_name': {field_info['nick']: field_info['name']
                                 for field_info in cdm_fields_info},
        })
    else:
        raise ValueError(f"invalid output type {report_format!r}")

    date_str = report_datetime.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"vocab-report_{ftp_collection.alias}_{date_str}.{report_format}"
    print(f"Writing report as {filename!r}")
    with open(filename, mode='w', encoding='utf-8') as fp:
        fp.write(report_str)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross check a FromThePage collection against CONTENTdm controlled vocabs",
        fromfile_prefix_chars='@'
    )
    parser.add_argument(
        'ftp_slug',
        type=str,
        help="FromThePage user slug"
    )
    parser.add_argument(
        'ftp_project_name',
        type=str,
        help="FromThePage project name"
    )
    parser.add_argument(
        'cdm_repo_url',
        type=str,
        help="CONTENTdm repository URL"
    )
    parser.add_argument(
        'cdm_collection_alias',
        type=str,
        help="CONTENTdm collection alias"
    )
    parser.add_argument(
        'field_mapping_csv',
        type=str,
        help="CSV file of FromThePage field labels mapped to CONTENTdm nicknames"
    )
    parser.add_argument(
        '--output',
        choices=['html', 'json'],
        default='html',
        type=str,
        help="Specify report format"
    )
    parser.add_argument(
        '--label',
        choices=list(ftp_api.RENDERING_EXTRACTORS),
        default='XHTML Export',
        type=str,
        help="Choose the export to use for parsing fields"
    )
    args = parser.parse_args()

    scanftpvocabs(
        ftp_slug=args.ftp_slug,
        ftp_project_name=args.ftp_project_name,
        cdm_repo_url=args.cdm_repo_url,
        cdm_collection_alias=args.cdm_collection_alias,
        field_mapping_csv_path=args.field_mapping_csv,
        report_format=args.output,
        rendering_label=args.rendering_label,
    )

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

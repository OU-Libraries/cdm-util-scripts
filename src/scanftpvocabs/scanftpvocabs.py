from requests import Session
import jinja2

import argparse
import sys
import json
from datetime import datetime
from collections import defaultdict

import ftpfields2catcher
import catcherdiff
import cdm_api

from typing import Dict, List, Tuple


def scan_vocabs(
        ftp_collection: ftpfields2catcher.FTPCollection,
        field_mapping: Dict[str, List[str]],
        vocabs_index: Dict[str, Dict[str, str]],
        vocabs: Dict[str, Dict[str, List[str]]]
) -> Tuple[Dict[str, Dict[str, ftpfields2catcher.FTPPage]], List[str]]:
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


def main():
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
        choices=list(ftpfields2catcher.rendering_extractors.keys()),
        default='XHTML Export',
        type=str,
        help="Choose the export to use for parsing fields"
    )
    args = parser.parse_args()

    try:
        field_mapping = ftpfields2catcher.get_field_mapping(args.field_mapping_csv)
    except ValueError as err:
        print(f"{args.field_mapping_csv}: {err}")
        sys.exit(1)

    with Session() as session:
        try:
            ftp_collection = ftpfields2catcher.get_and_load_ftp_collection(
                slug=args.ftp_slug,
                collection_name=args.ftp_project_name,
                rendering_label='XHTML Export',
                session=session
            )
        except KeyError as err:
            print(f"Error: {err}")
            sys.exit(1)
        cdm_fields_info = cdm_api.get_collection_field_info(
            repo_url=args.cdm_repo_url,
            collection_alias=args.cdm_collection_alias,
            session=session
        )
        vocabs_index = catcherdiff.build_vocabs_index(cdm_fields_info=cdm_fields_info)
        vocabs = catcherdiff.get_vocabs(
            cdm_repo_url=args.cdm_repo_url,
            cdm_collection_alias=args.cdm_collection_alias,
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
    report_date = datetime.now()
    report = {
        **vars(args),
        'report_date': report_date.isoformat(),
        'cdm_fields_info': cdm_fields_info,
        'vocabs_index': vocabs_index,
        'vocabs': vocabs,
        'field_mapping': field_mapping,
        'unmapped_controlled_fields': unmapped_controlled_fields,
        'field_scans': field_scans,
    }

    if args.output == 'json':
        report_str = json.dumps(report, indent=2)
    elif args.output == 'html':
        report_str = report_to_html({
            **report,
            'cdm_nick_to_name': {field_info['nick']: field_info['name']
                                 for field_info in cdm_fields_info},
        })
    else:
        raise ValueError(f"invalid output type {args.output!r}")

    date_str = report_date.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"vocab-report_{ftp_collection.alias}_{date_str}.{args.output}"
    print(f"Writing report as {filename!r}")
    with open(filename, mode='w', encoding='utf-8') as fp:
        fp.write(report_str)


if __name__ == '__main__':
    main()

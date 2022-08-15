from requests import Session
import jinja2

from datetime import datetime
from collections import defaultdict

from cdm_util_scripts import catcherdiff
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
            item_info = cdm_api.apply_field_mapping(
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

    report_str = report_to_html({
        **report,
        'cdm_nick_to_name': {field_info['nick']: field_info['name']
                             for field_info in cdm_fields_info},
    })
    date_str = report_datetime.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"vocab-report_{ftp_collection.alias}_{date_str}.html"
    print(f"Writing report as {filename!r}")
    with open(filename, mode='w', encoding='utf-8') as fp:
        fp.write(report_str)

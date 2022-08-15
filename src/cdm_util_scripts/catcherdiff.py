from requests import Session
import jinja2

import json
from datetime import datetime
from pathlib import Path

from cdm_util_scripts import cdm_api

from typing import Dict, List, Tuple, Any


def get_cdm_items_info(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        cdm_catcher_edits: List[Dict[str, str]],
        session: Session,
        verbose: bool = True
) -> List[Dict[str, str]]:
    cdm_items_info = []
    for n, edit in enumerate(cdm_catcher_edits, start=1):
        if verbose:
            print(f"Requesting CONTENTdm item info {n}/{len(cdm_catcher_edits)}...", end='\r')
        cdm_items_info.append(
            cdm_api.get_cdm_item_info(
                cdm_repo_url=cdm_repo_url,
                cdm_collection_alias=cdm_collection_alias,
                dmrecord=edit['dmrecord'],
                session=session
            )
        )
    if verbose:
        print(end='\n')
    return cdm_items_info


def collate_deltas(
        cdm_catcher_edits: List[Dict[str, str]],
        cdm_items_info: List[Dict[str, str]]
) -> List[Tuple[dict, dict]]:
    return [
        (edit, {nick: item_info[nick] for nick in edit.keys()})
        for edit, item_info in zip(cdm_catcher_edits, cdm_items_info)
    ]


def count_changes(deltas: List[Tuple[dict, dict]]) -> int:
    edits_with_changes_count = 0
    for delta in deltas:
        for nick, value in delta[0].items():
            if value != delta[1][nick]:
                edits_with_changes_count += 1
                break
    return edits_with_changes_count


def report_to_html(report: Dict[str, Any]) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template('catcherdiff-report.html.j2').render(report)


def catcherdiff(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        catcher_json_file_path: str,
        report_file_path: str,
        check_vocabs: bool,
) -> None:
    with open(catcher_json_file_path, mode='r', encoding="utf-8") as fp:
        cdm_catcher_edits = json.load(fp)

    with Session() as session:
        print("Requesting CONTENTdm field info...")
        cdm_fields_info = cdm_api.get_collection_field_info(
            repo_url=cdm_repo_url,
            collection_alias=cdm_collection_alias,
            session=session
        )
        cdm_items_info = get_cdm_items_info(
            cdm_repo_url=cdm_repo_url,
            cdm_collection_alias=cdm_collection_alias,
            cdm_catcher_edits=cdm_catcher_edits,
            session=session
        )
        vocabs_index = cdm_api.build_vocabs_index(cdm_fields_info)
        if check_vocabs:
            cdm_field_vocabs = cdm_api.get_vocabs(
                cdm_repo_url=cdm_repo_url,
                cdm_collection_alias=cdm_collection_alias,
                vocabs_index=vocabs_index,
                session=session
            )
        else:
            cdm_field_vocabs = None

    deltas = collate_deltas(cdm_catcher_edits, cdm_items_info)
    edits_with_changes_count = count_changes(deltas)

    print(f"catcherdiff found {edits_with_changes_count} out of {len(deltas)} total edit actions would change at least one field.")

    report = {
        'cdm_repo_url': cdm_repo_url.rstrip('/'),
        'cdm_collection_alias': cdm_collection_alias,
        'cdm_fields_info': cdm_fields_info,
        'vocabs_index': vocabs_index,
        'vocabs': cdm_field_vocabs,
        'catcher_json_file': Path(catcher_json_file_path).name,
        'report_file': report_file_path,
        'report_datetime': datetime.now().isoformat(),
        'edits_with_changes_count': edits_with_changes_count,
        'deltas': deltas,
        'cdm_nick_to_name': {
            field_info['nick']: field_info['name'] for field_info in cdm_fields_info
        },
    }

    report_html = report_to_html(report)
    with open(report_file_path, mode='w', encoding='utf-8') as fp:
        fp.write(report_html)

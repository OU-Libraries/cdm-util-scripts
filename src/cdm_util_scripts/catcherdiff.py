import requests
import jinja2
import tqdm

import json
from datetime import datetime
from pathlib import Path

from cdm_util_scripts import cdm_api

from typing import Dict, List, Any, NamedTuple, Iterable, Optional


class Delta(NamedTuple):
    edit: Dict[str, str]
    item_info: cdm_api.CdmItemInfo


def catcherdiff(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    catcher_json_file_path: str,
    report_file_path: str,
    check_vocabs: bool,
) -> None:
    with open(catcher_json_file_path, mode="r", encoding="utf-8") as fp:
        catcher_edits = json.load(fp)

    with requests.Session() as session:
        print("Requesting CONTENTdm field info...")
        cdm_field_infos = cdm_api.request_field_infos(
            instance_url=cdm_instance_url,
            collection_alias=cdm_collection_alias,
            session=session,
        )
        print("Requesting CONTENTdm item info...")
        deltas = request_deltas(
            catcher_edits=catcher_edits,
            instance_url=cdm_instance_url,
            collection_alias=cdm_collection_alias,
            session=session,
        )
        if check_vocabs:
            print("Requesting CONTENTdm controlled vocabularies...")
            cdm_vocabs = cdm_api.request_vocabs(
                instance_url=cdm_instance_url,
                collection_alias=cdm_collection_alias,
                field_infos=cdm_field_infos,
                session=session,
            )
        else:
            cdm_vocabs = None

    edits_with_changes_count = count_changes(deltas)
    vocabs_by_nick = {
        field_info.nick: cdm_vocabs[field_info.get_vocab_info()] if cdm_vocabs else None
        for field_info in cdm_field_infos
        if field_info.vocab
    }
    identifier_field_info = find_dc_field(cdm_field_infos, "Identifier")
    identifier_nick = identifier_field_info.nick if identifier_field_info else None
    title_field_info = find_dc_field(cdm_field_infos, "Title")
    title_nick = title_field_info.nick if title_field_info else None

    print(
        f"catcherdiff found {edits_with_changes_count} out of {len(catcher_edits)} total edit actions would change at least one field."
    )

    report = {
        "cdm_repo_url": cdm_instance_url.rstrip("/"),
        "cdm_collection_alias": cdm_collection_alias,
        "cdm_field_infos": cdm_field_infos,
        "vocabs_by_nick": vocabs_by_nick,
        "catcher_json_file": Path(catcher_json_file_path).name,
        "report_file": report_file_path,
        "report_datetime": datetime.now().isoformat(),
        "edits_with_changes_count": edits_with_changes_count,
        "deltas": deltas,
        "identifier_nick": identifier_nick,
        "title_nick": title_nick,
        "cdm_nick_to_name": {
            field_info.nick: field_info.name for field_info in cdm_field_infos
        },
    }

    report_html = report_to_html(report)
    with open(report_file_path, mode="w", encoding="utf-8") as fp:
        fp.write(report_html)


def request_deltas(
    catcher_edits: List[Dict[str, str]],
    instance_url: str,
    collection_alias: str,
    session: requests.Session,
) -> List[Delta]:
    deltas: List[Delta] = []
    for edit in tqdm.tqdm(catcher_edits):
        item_info = cdm_api.request_item_info(
            instance_url=instance_url,
            collection_alias=collection_alias,
            dmrecord=edit["dmrecord"],
            session=session,
        )
        deltas.append(Delta(edit=edit, item_info=item_info))
    return deltas


def count_changes(deltas: List[Delta]) -> int:
    edits_with_changes_count = 0
    for delta in deltas:
        for nick, value in delta.edit.items():
            if value != delta.item_info[nick]:
                edits_with_changes_count += 1
                break
    return edits_with_changes_count


def find_dc_field(
    cdm_field_infos: Iterable[cdm_api.CdmFieldInfo], dc_name: str
) -> Optional[cdm_api.CdmFieldInfo]:
    try:
        return [info for info in cdm_field_infos if info.dc == dc_name][0]
    except IndexError:
        return None


def report_to_html(report: Dict[str, Any]) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template("catcherdiff-report.html.j2").render(report)

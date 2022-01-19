from requests import Session
import jinja2

import json
import argparse
import sys
from datetime import datetime
from pathlib import Path

from cdm_util_scripts.cdm_api import get_cdm_item_info, get_cdm_collection_field_vocab, get_collection_field_info

from typing import Dict, List, Union, Tuple


def build_vocabs_index(cdm_fields_info: List[Dict[str, Union[str, int]]]) -> Dict[str, Dict[str, str]]:
    vocabs_index = dict()
    for field_info in cdm_fields_info:
        if field_info['vocab']:
            nick = field_info['nick']
            vocdb = field_info['vocdb']
            vocabs_index[nick] = {
                'type': 'vocdb' if vocdb else 'vocab',
                'name': vocdb if vocdb else nick,
            }
    return vocabs_index


def get_vocabs(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        vocabs_index: Dict[str, Dict[str, str]],
        session: Session,
        verbose: bool = True
) -> Dict[str, Dict[str, List[str]]]:
    vocses = {
        'vocab': dict(),
        'vocdb': dict(),
    }
    for nick, index in vocabs_index.items():
        vocs = vocses[index['type']]
        if index['name'] in vocs:
            continue
        if verbose:
            print(f"Requesting {index['type']} for {nick!r}... ", end='')
        vocab = get_cdm_collection_field_vocab(
            cdm_repo_url=cdm_repo_url,
            cdm_collection_alias=cdm_collection_alias,
            cdm_field_nick=nick,
            session=session
        )
        if verbose:
            print(f"found {len(vocab)} terms.")
        vocs[index['name']] = vocab
    return vocses


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
            get_cdm_item_info(
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
    return [(edit, {nick: item_info[nick] for nick in edit.keys()})
            for edit, item_info in zip(cdm_catcher_edits, cdm_items_info)]


def count_changes(deltas: List[Tuple[dict, dict]]) -> int:
    edits_with_changes_count = 0
    for delta in deltas:
        for nick, value in delta[0].items():
            if value != delta[1][nick]:
                edits_with_changes_count += 1
                break
    return edits_with_changes_count


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template('catcherdiff-report.html.j2').render(report)


def main():
    parser = argparse.ArgumentParser(
        description=""
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
        'catcher_json_file',
        type=str,
        help="cdm-catcher JSON file"
    )
    parser.add_argument(
        'report_file',
        type=str,
        help="Diff output file name"
    )
    parser.add_argument(
        '--check_vocabs',
        action='store_const',
        const=True,
        help="Check controlled vocabulary terms"
    )
    args = parser.parse_args()

    with open(args.catcher_json_file, mode='r', encoding="utf-8") as fp:
        cdm_catcher_edits = json.load(fp)

    with Session() as session:
        print("Requesting CONTENTdm field info...")
        cdm_fields_info = get_collection_field_info(
            repo_url=args.cdm_repo_url,
            collection_alias=args.cdm_collection_alias,
            session=session
        )
        cdm_items_info = get_cdm_items_info(
            cdm_repo_url=args.cdm_repo_url,
            cdm_collection_alias=args.cdm_collection_alias,
            cdm_catcher_edits=cdm_catcher_edits,
            session=session
        )
        vocabs_index = build_vocabs_index(cdm_fields_info)
        if args.check_vocabs:
            cdm_field_vocabs = get_vocabs(
                cdm_repo_url=args.cdm_repo_url,
                cdm_collection_alias=args.cdm_collection_alias,
                vocabs_index=vocabs_index,
                session=session
            )
        else:
            cdm_field_vocabs = None

    try:
        deltas = collate_deltas(cdm_catcher_edits, cdm_items_info)
    except KeyError as err:
        print(f"Error: field nick not found in field info: {err}")
        sys.exit(1)

    edits_with_changes_count = count_changes(deltas)
    print(f"catcherdiff found {edits_with_changes_count} out of {len(deltas)} total edit actions would change at least one field.")

    report = {
        'cdm_repo_url': args.cdm_repo_url.rstrip('/'),
        'cdm_collection_alias': args.cdm_collection_alias,
        'cdm_fields_info': cdm_fields_info,
        'vocabs_index': vocabs_index,
        'vocabs': cdm_field_vocabs,
        'catcher_json_file': Path(args.catcher_json_file).name,
        'report_file': args.report_file,
        'report_datetime': datetime.now().isoformat(),
        'edits_with_changes_count': edits_with_changes_count,
        'deltas': deltas,
        'cdm_nick_to_name': {
            field_info['nick']: field_info['name'] for field_info in cdm_fields_info
        },
    }

    report_html = report_to_html(report)
    with open(args.report_file, mode='w', encoding='utf-8') as fp:
        fp.write(report_html)


if __name__ == '__main__':
    main()

from requests import Session
import jinja2

import json
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from sys import platform

from printcdminfo import get_collection_field_info, get_dm

from typing import Dict, List, Union, Optional


def get_cdm_item_info(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        dmrecord: str,
        session: Session
) -> Dict[str, str]:
    url = f"{cdm_repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/{cdm_collection_alias}/{dmrecord}/json"
    item_info = get_dm(url, session)
    return {nick: value or '' for nick, value in item_info.items()}


def get_cdm_collection_field_vocab(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        cdm_field_nick: str,
        session: Session
) -> List[str]:
    url = f"{cdm_repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldVocabulary/{cdm_collection_alias}/{cdm_field_nick}/0/1/json"
    return get_dm(url, session)


def get_cdm_collection_vocabs(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        session: Session,
        cdm_fields_info: Optional[List[Dict[str, Union[str, int]]]] = None,
        verbose: bool = True
) -> Dict[str, List[str]]:
    if not cdm_fields_info:
        cdm_fields_info = get_collection_field_info(
            cdm_repo_url,
            cdm_collection_alias,
            session
        )
    fields_with_vocabs = [field_info
                          for field_info in cdm_fields_info
                          if field_info['vocab']]
    vocdbs = dict()
    vocabs = dict()
    for field_info in fields_with_vocabs:
        nick = field_info['nick']
        vocdb = field_info['vocdb']
        if verbose:
            print(f"Requesting vocab for {nick!r}... ", end='')
        if vocdb and vocdb in vocdbs:
            if verbose:
                print(f"{nick!r} matched to {vocdb!r}.")
            vocabs[nick] = vocdbs[vocdb]
            continue
        vocab = get_cdm_collection_field_vocab(
            cdm_repo_url=cdm_repo_url,
            cdm_collection_alias=cdm_collection_alias,
            cdm_field_nick=nick,
            session=session
        )
        if vocdb:
            vocdbs[vocdb] = vocab
            vocabs[nick] = vocab
            if verbose:
                print(f"matched to {vocdb!r} ({len(vocab)} terms)")
        else:
            vocabs[nick] = vocab
            if verbose:
                print(f"found {len(vocab)} terms.")
    return vocabs


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
):
    return [(edit, {nick: item_info[nick] for nick in edit.keys()})
            for edit, item_info in zip(cdm_catcher_edits, cdm_items_info)]


def report_to_html(report: dict) -> str:
    path = os.path.dirname(os.path.abspath(__file__))
    # https://github.com/pallets/jinja/issues/767
    if platform == 'win32':
        path = path.replace('\\', '/')
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(path))
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

    with open(args.catcher_json_file, mode='r') as fp:
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
        if args.check_vocabs:
            cdm_field_vocabs = get_cdm_collection_vocabs(
                cdm_repo_url=args.cdm_repo_url,
                cdm_collection_alias=args.cdm_collection_alias,
                session=session,
                cdm_fields_info=cdm_fields_info
            )
        else:
            cdm_field_vocabs = {field_info['nick']
                                for field_info in cdm_fields_info
                                if field_info['vocab']}

    try:
        deltas = collate_deltas(cdm_catcher_edits, cdm_items_info)
    except KeyError as err:
        print(f"Error: field nick not found in field info: {err}")
        sys.exit(1)

    edits_with_changes_count = 0
    for delta in deltas:
        for nick, value in delta[0].items():
            if value != delta[1][nick]:
                edits_with_changes_count += 1
                break
    print(f"catcherdiff found {edits_with_changes_count} out of {len(deltas)} total edit actions would change at least one field.")

    report = {
        'cdm_repo_url': args.cdm_repo_url.rstrip('/'),
        'cdm_collection_alias': args.cdm_collection_alias,
        'cdm_fields_info': cdm_fields_info,
        'vocabs': cdm_field_vocabs,
        'catcher_json_file': Path(args.catcher_json_file).name,
        'report_file': args.report_file,
        'report_datetime': datetime.now().isoformat(),
        'edits_with_changes_count': edits_with_changes_count,
        'deltas': deltas,
    }

    report_html = report_to_html(report)
    with open(args.report_file, mode='w', encoding='utf-8') as fp:
        fp.write(report_html)


if __name__ == '__main__':
    main()

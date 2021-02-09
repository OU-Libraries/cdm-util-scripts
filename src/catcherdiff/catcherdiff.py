from requests import Session
import jinja2

import json
import argparse
import os
from datetime import datetime
from pathlib import Path

from typing import Dict, List


def get_cdm_item_info(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        dmrecord: str,
        session: Session
) -> Dict[str, str]:
    response = session.get(f"{cdm_repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/{cdm_collection_alias}/{dmrecord}/json")
    response.raise_for_status()
    item_info = response.json()
    return {nick: value or '' for nick, value in item_info.items()}


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


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
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
    args = parser.parse_args()

    with open(args.catcher_json_file, mode='r') as fp:
        cdm_catcher_edits = json.load(fp)

    with Session() as session:
        cdm_items_info = get_cdm_items_info(
            cdm_repo_url=args.cdm_repo_url,
            cdm_collection_alias=args.cdm_collection_alias,
            cdm_catcher_edits=cdm_catcher_edits,
            session=session
        )

    deltas = []
    for edit, item_info in zip(cdm_catcher_edits, cdm_items_info):
        deltas.append((edit, {nick: item_info[nick] for nick in edit.keys()}))

    report = {
        'cdm_repo_url': args.cdm_repo_url,
        'cdm_collection_alias': args.cdm_collection_alias,
        'catcher_json_file': Path(args.catcher_json_file).name,
        'report_file': args.report_file,
        'report_datetime': datetime.now().isoformat(),
        'deltas': deltas,
    }

    report_html = report_to_html(report)
    with open(args.report_file, mode='w') as fp:
        fp.write(report_html)


if __name__ == '__main__':
    main()
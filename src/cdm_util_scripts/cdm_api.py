from requests import Session

import csv
import collections

from typing import Dict, List, Union, Tuple, Sequence


class DmError(Exception):
    pass


def get_dm(url: str, session: Session):
    response = session.get(url)
    response.raise_for_status()
    dm_result = response.json()
    if 'code' in dm_result and 'message' in dm_result:
        raise DmError(dm_result['message'])
    return dm_result


def get_collection_field_info(repo_url: str, collection_alias: str, session: Session) -> dict:
    url = '/'.join([
        repo_url.rstrip('/'),
        'digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldInfo',
        collection_alias,
        'json'
    ])
    return get_dm(url, session)


def get_collection_list(repo_url: str, session: Session) -> list:
    url = '/'.join([
        repo_url.rstrip('/'),
        'digital/bl/dmwebservices/index.php?q=dmGetCollectionList/json'
    ])
    return get_dm(url, session)


def get_cdm_item_info(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        dmrecord: str,
        session: Session
) -> Dict[str, str]:
    cdm_repo_url = cdm_repo_url.rstrip('/')
    url = f"{cdm_repo_url}/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/{cdm_collection_alias}/{dmrecord}/json"
    item_info = get_dm(url, session)
    return {nick: value or '' for nick, value in item_info.items()}


def get_cdm_collection_field_vocab(
        cdm_repo_url: str,
        cdm_collection_alias: str,
        cdm_field_nick: str,
        session: Session
) -> List[str]:
    cdm_repo_url = cdm_repo_url.rstrip('/')
    url = f"{cdm_repo_url}/digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldVocabulary/{cdm_collection_alias}/{cdm_field_nick}/0/1/json"
    return get_dm(url, session)


def get_cdm_page_pointers(repo_url: str, alias: str, dmrecord: str, session: Session) -> List[str]:
    repo_url = repo_url.rstrip('/')
    url = f"{repo_url}/digital/bl/dmwebservices/index.php?q=dmGetCompoundObjectInfo/{alias}/{dmrecord}/json"
    cpd_object_info = get_dm(url, session)
    if cpd_object_info["type"] == "Monograph":
        _, page_pointers = _destructure_nodes(cpd_object_info["node"])
    else:
        page_pointers = [page['pageptr'] for page in cpd_object_info['page']]
    return page_pointers


def _destructure_nodes(
    node: Union[dict, list]
) -> Tuple[List[Tuple[int, str]], List[str]]:
    pages_index = []
    page_pointers = []

    def walk_nodes(node: Union[dict, list], depth: int = 0,) -> None:
        if "page" not in node:
            node_pages = []
        elif isinstance(node["page"], dict):
            node_pages = [node["page"]]
        else:
            node_pages = node["page"]

        for page in node_pages:
            page_pointers.append(page["pageptr"])
            pages_index.append(
                (depth, node["nodetitle"] if node["nodetitle"] != {} else "")
            )

        if "node" in node:
            next_nodes = (
                [node["node"]] if isinstance(node["node"], dict) else node["node"]
            )
            for n in next_nodes:
                walk_nodes(n, depth + 1)

    walk_nodes(node)
    return pages_index, page_pointers


def read_csv_field_mapping(filename: str) -> Dict[str, List[str]]:
    with open(filename, mode='r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            raise ValueError("column mapping CSV must have 'name' and 'nick' column titles in that order")
        field_mapping = collections.defaultdict(list)
        for row in reader:
            field_mapping[row['name']].append(row['nick'].strip())
    return dict(field_mapping)


def apply_field_mapping(ftp_fields: Dict[str, str], field_mapping: Dict[str, Sequence[str]]) -> Dict[str, str]:
    accumulator: Dict[str, str] = dict()
    for label, nicks in field_mapping.items():
        ftp_field = ftp_fields[label]
        for nick in nicks:
            if nick in accumulator:
                if ftp_field:
                    if accumulator[nick]:
                        accumulator[nick] = '; '.join([
                            accumulator[nick],
                            ftp_field
                        ])
                    else:
                        accumulator[nick] = ftp_field
            else:
                accumulator[nick] = ftp_field
    return accumulator


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

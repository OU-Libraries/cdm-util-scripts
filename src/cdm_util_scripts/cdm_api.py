from requests import Session

from typing import Dict, List


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
    query_url = '/'.join([
        repo_url.rstrip('/'),
        'digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldInfo',
        collection_alias,
        'json'
    ])
    return get_dm(query_url, session)


def get_collection_list(repo_url: str, session: Session) -> list:
    query_url = '/'.join([
        repo_url.rstrip('/'),
        'digital/bl/dmwebservices/index.php?q=dmGetCollectionList/json'
    ])
    return get_dm(query_url, session)


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


def get_cdm_page_pointers(repo_url: str, alias: str, dmrecord: str, session: Session) -> List[str]:
    response = session.get(f"{repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmGetCompoundObjectInfo/{alias}/{dmrecord}/json")
    response.raise_for_status()
    dmGetCompoundObjectInfo = response.json()
    if 'code' in dmGetCompoundObjectInfo:
        raise ValueError(f"CONTENTdm error {dmGetCompoundObjectInfo['message']!r}")
    # print(f"{alias!r} dmrecord {dmrecord!r} is type {dmGetCompoundObjectInfo['type']!r}")
    return [page['pageptr'] for page in dmGetCompoundObjectInfo['page']]

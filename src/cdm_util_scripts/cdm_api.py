from requests import Session

import csv
import collections
import enum

from typing import Dict, List, Union, Tuple, NamedTuple, Optional, Any


class DmError(Exception):
    pass


def request_dm(url: str, session: Session):
    response = session.get(url)
    response.raise_for_status()
    dm_result = response.json()
    if "code" in dm_result and "message" in dm_result:
        raise DmError(dm_result["message"])
    return dm_result


class CdmCollectionInfo(NamedTuple):
    alias: str
    name: str
    path: str
    secondary_alias: str


def request_collection_list(
    instance_url: str, session: Session
) -> List[CdmCollectionInfo]:
    instance_url = instance_url.rstrip("/")
    url = "/".join(
        [instance_url, "digital/bl/dmwebservices/index.php?q=dmGetCollectionList/json"]
    )
    return [CdmCollectionInfo(**info) for info in request_dm(url=url, session=session)]


class CdmVocabType(enum.Enum):
    builtin = enum.auto()
    custom = enum.auto()


class CdmVocabInfo(NamedTuple):
    vocab_type: CdmVocabType
    key: str


class CdmFieldInfo(NamedTuple):
    name: str
    nick: str
    type: str
    size: int
    find: str
    req: int
    search: int
    hide: int
    vocdb: str
    vocab: int
    dc: str
    admin: int
    readonly: int

    def get_vocab_info(self) -> Optional[CdmVocabInfo]:
        if not self.vocab:
            return None
        vocab_type = CdmVocabType.builtin if self.vocdb else CdmVocabType.custom
        key = self.vocdb if self.vocdb else self.nick
        return CdmVocabInfo(
            vocab_type=vocab_type,
            key=key,
        )


def request_field_infos(
    instance_url: str, collection_alias: str, session: Session
) -> List[CdmFieldInfo]:
    instance_url = instance_url.rstrip("/")
    url = "/".join(
        [
            instance_url,
            "digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldInfo",
            collection_alias,
            "json",
        ]
    )
    return [CdmFieldInfo(**info) for info in request_dm(url=url, session=session)]


CdmItemInfo = Dict[str, str]


def request_item_info(
    instance_url: str, collection_alias: str, dmrecord: str, session: Session
) -> CdmItemInfo:
    instance_url = instance_url.rstrip("/")
    url = f"{instance_url}/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/{collection_alias}/{dmrecord}/json"
    item_info = request_dm(url=url, session=session)
    return {nick: value or "" for nick, value in item_info.items()}


CdmFieldVocab = List[str]


def request_field_vocab(
    instance_url: str, collection_alias: str, field_nick: str, session: Session
) -> CdmFieldVocab:
    instance_url = instance_url.rstrip("/")
    url = f"{instance_url}/digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldVocabulary/{collection_alias}/{field_nick}/0/1/json"
    return request_dm(url=url, session=session)


def request_page_pointers(
    instance_url: str, collection_alias: str, dmrecord: str, session: Session
) -> List[str]:
    instance_url = instance_url.rstrip("/")
    url = f"{instance_url}/digital/bl/dmwebservices/index.php?q=dmGetCompoundObjectInfo/{collection_alias}/{dmrecord}/json"
    cpd_object_info = request_dm(url=url, session=session)
    if cpd_object_info["type"] == "Monograph":
        _, page_pointers = _destructure_nodes(cpd_object_info["node"])
    else:
        page_pointers = [page["pageptr"] for page in cpd_object_info["page"]]
    return page_pointers


def _destructure_nodes(
    node: Union[Dict[str, Any], List[Any]]
) -> Tuple[List[Tuple[int, str]], List[str]]:
    pages_index = []
    page_pointers = []

    def walk_nodes(
        node: Union[Dict[str, Any], List[Any]],
        depth: int = 0,
    ) -> None:
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


CdmFieldMapping = Dict[str, List[str]]


def read_csv_field_mapping(filename: str) -> CdmFieldMapping:
    with open(filename, mode="r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ["name", "nick"]:
            raise ValueError(
                "column mapping CSV must have 'name' and 'nick' column titles in that order"
            )
        field_mapping = collections.defaultdict(list)
        for row in reader:
            field_mapping[row["name"]].append(row["nick"].strip())
    return dict(field_mapping)


def apply_field_mapping(
    fields: Dict[str, str], field_mapping: CdmFieldMapping
) -> Dict[str, str]:
    accumulator: Dict[str, str] = dict()
    for label, nicks in field_mapping.items():
        field = fields[label]
        for nick in nicks:
            if nick in accumulator:
                if field:
                    if accumulator[nick]:
                        accumulator[nick] = "; ".join([accumulator[nick], field])
                    else:
                        accumulator[nick] = field
            else:
                accumulator[nick] = field
    return accumulator


def request_vocabs(
    instance_url: str,
    collection_alias: str,
    field_infos: List[CdmFieldInfo],
    session: Session,
) -> Dict[CdmVocabInfo, List[str]]:
    vocabs = dict()
    for field_info in field_infos:
        vocab_info = field_info.get_vocab_info()
        if vocab_info is None or vocab_info in vocabs:
            continue
        print(
            f"Requesting {field_info.name if vocab_info.vocab_type is CdmVocabType.custom else vocab_info.key!r} vocab..."
        )
        vocabs[vocab_info] = request_field_vocab(
            instance_url=instance_url,
            collection_alias=collection_alias,
            field_nick=field_info.nick,
            session=session,
        )
    return vocabs

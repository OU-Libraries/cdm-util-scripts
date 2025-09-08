import requests

import csv
import collections
import enum

from typing import (
    Any,
    Iterable,
    Iterator,
    NamedTuple,
    Optional,
    TextIO,
    Union,
)


class DmError(Exception):
    pass


def request_dm(
    url: str,
    session: requests.Session,
) -> Any:
    response = session.get(url)
    response.raise_for_status()
    dm_result = response.json()
    if (
        isinstance(dm_result, dict)
        and "code" in dm_result
        and "message" in dm_result
    ):
        raise DmError(dm_result["message"])
    return dm_result


class CdmCollectionInfo(NamedTuple):
    alias: str
    name: str
    path: str
    secondary_alias: str


def request_collection_list(
    instance_url: str,
    session: requests.Session
) -> list[CdmCollectionInfo]:
    url = (
        f"{instance_url.rstrip('/')}/digital/bl/dmwebservices/index.php"
        "?q=dmGetCollectionList/json"
    )
    return [
        CdmCollectionInfo(**info)
        for info in request_dm(url=url, session=session)
    ]


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
    dc: Optional[str]
    admin: int
    readonly: int

    def get_vocab_info(self) -> Optional[CdmVocabInfo]:
        if not self.vocab:
            return None
        vocab_type = (
            CdmVocabType.builtin if self.vocdb else CdmVocabType.custom
        )
        key = self.vocdb if self.vocdb else self.nick
        return CdmVocabInfo(
            vocab_type=vocab_type,
            key=key,
        )


def request_field_infos(
    instance_url: str,
    collection_alias: str,
    session: requests.Session,
) -> list[CdmFieldInfo]:
    infos_url = "/".join(
        [
            instance_url.rstrip("/"),
            "digital/bl/dmwebservices/index.php?q=dmGetCollectionFieldInfo",
            collection_alias,
            "json",
        ]
    )
    raw_infos = request_dm(url=infos_url, session=session)
    dc_mappings_url = (
        f"{instance_url.rstrip('/')}/digital/bl/dmwebservices/index.php"
        "?q=dmGetDublinCoreFieldInfo/json"
    )
    raw_dc_mappings = request_dm(url=dc_mappings_url, session=session)
    dc_nicks_to_names = {
        dc_info["nick"]: dc_info["name"] for dc_info in raw_dc_mappings
    }
    infos = []
    for info in raw_infos:
        if info["dc"] in {"BLANK", False, None, ""}:
            dc_name = None
        else:
            dc_name = dc_nicks_to_names[info["dc"]]
        infos.append(CdmFieldInfo(**{**info, "dc": dc_name}))
    return infos


CdmItemInfo = dict[str, str]


def request_item_info(
    instance_url: str,
    collection_alias: str,
    dmrecord: str,
    session: requests.Session,
) -> CdmItemInfo:
    url = "/".join(
        [
            instance_url.rstrip("/"),
            "digital/bl/dmwebservices/index.php?q=dmGetItemInfo",
            collection_alias,
            dmrecord,
            "json",
        ]
    )
    item_info = request_dm(url=url, session=session)
    return {nick: value or "" for nick, value in item_info.items()}


CdmFieldVocab = list[str]


def request_field_vocab(
    instance_url: str,
    collection_alias: str,
    field_nick: str,
    session: requests.Session,
) -> CdmFieldVocab:
    url = (
        f"{instance_url.rstrip('/')}/digital/bl/dmwebservices/index.php"
        f"?q=dmGetCollectionFieldVocabulary/{collection_alias}/{field_nick}"
        "/0/1/json"
    )
    return request_dm(url=url, session=session)


def request_page_pointers(
    instance_url: str,
    collection_alias: str,
    dmrecord: str,
    session: requests.Session,
) -> list[str]:
    url = "/".join(
        [
            instance_url.rstrip("/"),
            "digital/bl/dmwebservices/index.php?q=dmGetCompoundObjectInfo",
            collection_alias,
            dmrecord,
            "json",
        ]
    )
    cpd_object_info = request_dm(url=url, session=session)
    if cpd_object_info["type"] == "Monograph":
        root = MonographNode(**cpd_object_info["node"])
        page_pointers = list(root.iter_page_pointers())
    else:
        page_pointers = [page["pageptr"] for page in cpd_object_info["page"]]
    return page_pointers


class MonographNode:
    nodetitle: str
    pages: list["MonographPage"]
    nodes: list["MonographNode"]

    def __init__(
        self,
        nodetitle: Union[str, dict[Any, Any]],  # {} is CONTENTdm's None
        page: Optional[Union[dict[str, str], list[dict[str, str]]]] = None,
        node: Optional[Union[dict[str, Any], list[dict[str, Any]]]] = None,
    ) -> None:
        self.nodetitle = nodetitle if isinstance(nodetitle, str) else ""
        if page is None:
            pages = []
        elif isinstance(page, dict):
            pages = [page]
        else:
            pages = page
        self.pages = [MonographPage(**page_) for page_ in pages]
        if node is None:
            nodes = []
        elif isinstance(node, dict):
            nodes = [node]
        else:
            nodes = node
        self.nodes = [MonographNode(**node_) for node_ in nodes]

    def iter_pages(
        self,
        depth: int = 0,
    ) -> Iterator[tuple[int, str, "MonographPage"]]:
        for page in self.pages:
            yield (depth, self.nodetitle, page)
        for node in self.nodes:
            yield from node.iter_pages(depth=depth + 1)

    def iter_page_pointers(self) -> Iterator[str]:
        for _, _, page in self.iter_pages():
            yield page.pageptr


class MonographPage(NamedTuple):
    pagetitle: str
    pagefile: str
    pageptr: str


class CdmObjectRecord:
    collection: str
    pointer: int
    filetype: str
    parentobject: int
    find: str
    fields: dict[str, Any]

    def __init__(
        self,
        *,
        collection: str,
        pointer: int,
        filetype: str,
        parentobject: int,
        find: str,
        **kwargs,
    ) -> None:
        self.collection = collection
        self.pointer = pointer
        self.filetype = filetype
        self.parentobject = parentobject
        self.find = find
        self.fields = kwargs

    def is_compound(self) -> bool:
        return self.find.endswith(".cpd")


def request_collection_object_records(
    instance_url: str,
    collection_alias: str,
    field_nicks: Iterable[str],
    session: requests.Session,
) -> list[CdmObjectRecord]:
    cdm_records: list[CdmObjectRecord] = []
    total = 1
    start = 1
    maxrecs = 1024
    while len(cdm_records) < total:
        result = request_dm(
            url="/".join(
                [
                    instance_url.rstrip("/"),
                    "digital/bl/dmwebservices/index.php?q=dmQuery",
                    collection_alias,
                    "CISOSEARCHALL",
                    "!".join(field_nicks),
                    "pointer",
                    str(maxrecs),
                    str(start),
                    "1/0/0/0/0/1/json",
                ]
            ),
            session=session,
        )
        total = int(result["pager"]["total"])
        start += maxrecs
        cdm_records.extend(
            CdmObjectRecord(**record) for record in result["records"]
        )
    return cdm_records


CdmFieldMapping = dict[str, list[str]]


def read_csv_field_mapping(filename: str) -> CdmFieldMapping:
    with open(filename, mode="r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp, dialect=sniff_csv_dialect(fp))
        if not {"name", "nick"}.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                "column mapping CSV must include 'name' and 'nick' column "
                "names"
            )
        field_mapping = collections.defaultdict(list)
        for row in reader:
            field_mapping[row["name"]].append(row["nick"].strip())
    return dict(field_mapping)


def write_csv_field_mapping(
    filename: str,
    field_mapping: CdmFieldMapping,
) -> None:
    with open(filename, mode="w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["name", "nick"])
        writer.writeheader()
        for name, nicks in field_mapping.items():
            for nick in nicks:
                writer.writerow({"name": name, "nick": nick})


def apply_field_mapping(
    fields: dict[str, str],
    field_mapping: CdmFieldMapping,
) -> dict[str, str]:
    accumulator: dict[str, str] = dict()
    for label, nicks in field_mapping.items():
        field = fields[label]
        for nick in nicks:
            if nick in accumulator:
                if field:
                    if accumulator[nick]:
                        accumulator[nick] = "; ".join(
                            [accumulator[nick], field]
                        )
                    else:
                        accumulator[nick] = field
            else:
                accumulator[nick] = field
    return accumulator


def sniff_csv_dialect(fp: TextIO) -> type[csv.Dialect]:
    dialect = csv.Sniffer().sniff(fp.read(1024))
    fp.seek(0)
    return dialect


def request_vocabs(
    instance_url: str,
    collection_alias: str,
    field_infos: list[CdmFieldInfo],
    session: requests.Session,
) -> dict[CdmVocabInfo, CdmFieldVocab]:
    vocabs: dict[CdmVocabInfo, CdmFieldVocab] = {}
    for field_info in field_infos:
        vocab_info = field_info.get_vocab_info()
        if vocab_info is None or vocab_info in vocabs:
            continue
        vocab_name = (
            field_info.name
            if vocab_info.vocab_type is CdmVocabType.custom
            else vocab_info.key
        )
        print(f"Requesting {vocab_name!r} vocab...")
        vocabs[vocab_info] = request_field_vocab(
            instance_url=instance_url,
            collection_alias=collection_alias,
            field_nick=field_info.nick,
            session=session,
        )
    return vocabs

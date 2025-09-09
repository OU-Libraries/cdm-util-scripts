import csv
import functools
import json
import os
import sys
import xml.etree.ElementTree as ET

import zeep

from typing import Any, Literal, Iterator, NamedTuple, Callable, Optional


JsonObject = dict[str, Any]


CATCHER_SERVICE_URL = (
    "https://worldcat.org/webservices/contentdm/catcher/6.0/CatcherService.wsdl"
)


# Catcher operations


# getWSVersion() -> return: xsd:string


def catcher_ws_version() -> str:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    return catcher.service.getWSVersion()


# getCONTENTdmHTTPTransferVersion(
#   cdmurl: xsd:string,
#   username: xsd:string,
#   password: xsd:string
# ) -> return: xsd:string


def catcher_http_transfer_version(
    cdm_instance_url: str,
    username: str,
    password: str,
    license: str,
) -> str:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    return catcher.service.getCONTENTdmHTTPTransferVersion(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
    )


# getCONTENTdmCatalog(
#   cdmurl: xsd:string,
#   username: xsd:string,
#   password: xsd:string,
#   license: xsd:string
# ) -> return: xsd:string


def catcher_catalog(
    cdm_instance_url: str,
    username: str,
    password: str,
    license: str,
) -> str:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    return catcher.service.getCONTENTdmCatalog(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
        license=license,
    )


# getCONTENTdmCollectionConfig(
#   cdmurl: xsd:string,
#   username: xsd:string,
#   password: xsd:string,
#   license: xsd:string,
#   collection: xsd:string
# ) -> return: xsd:string


def catcher_collection(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    username: str,
    password: str,
    license: str,
) -> str:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    return catcher.service.getCONTENTdmCollectionConfig(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
        license=license,
        collection=f"/{cdm_collection_alias.lstrip('/')}",
    )


# getCONTENTdmControlledVocabTerms(
#   cdmurl: xsd:string,
#   username: xsd:string,
#   password: xsd:string,
#   license: xsd:string,
#   collection: xsd:string,
#   field: xsd:string
# ) -> return: xsd:string


def catcher_terms(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    cdm_field_nickname: str,
    username: str,
    password: str,
    license: str,
) -> str:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    return catcher.service.getCONTENTdmControlledVocabTerms(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
        license=license,
        collection=f"/{cdm_collection_alias.lstrip('/')}",
        field=cdm_field_nickname,
    )


# processCONTENTdm(
#   action: xsd:string,
#   cdmurl: xsd:string,
#   username: xsd:string,
#   password: xsd:string,
#   license: xsd:string,
#   collection: xsd:string,
#   disableValidation: xsd:string,
#   metadata: ns0:metadataWrapper
# ) -> return: xsd:string


def catcher_process(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    action: Literal["add", "edit", "delete"],
    catcher_json_file_path: str,
    username: str,
    password: str,
    license: str,
) -> None:
    """Implement Catcher addition, deletion, and edit actions"""
    with open(catcher_json_file_path, mode="r", encoding="utf-8") as fp:
        additions: list[JsonObject] = json.load(fp=fp)
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    factory = catcher.type_factory("ns0")
    for json_object in additions:
        process_args = {
            "action": action,
            "cdmurl": cdm_instance_url,
            "username": username,
            "password": password,
            "license": license,
            "collection": f"/{cdm_collection_alias.lstrip('/')}",
            "metadata": factory.metadataWrapper(
                metadataList={
                    "metadata": [
                        factory.metadata(field=field, value=value)
                        for field, value in sorted_metadata_json_object(
                            json_object
                        ).items()
                    ],
                },
            ),
        }
        if action == "edit":
            process_args["disableValidation"] = "true"
        response = catcher.service.processCONTENTdm(**process_args)
        print(response, file=sys.stderr)


def sorted_metadata_json_object(obj: JsonObject) -> JsonObject:
    sort_order: list[str] = []
    if "dmrecord" in obj:
        sort_order.append("dmrecord")
    if "title" in obj:
        sort_order.append("title")
    sort_order.extend(key for key in obj if key not in ["dmrecord", "title"])
    return {key: obj[key] for key in sort_order}


# CLI utilities


def credentials_from_environ(func: Callable[..., str]) -> Callable[..., str]:

    def run_func_with_credentials(*args, **kwargs) -> str:
        return func(
            *args,
            **kwargs,
            cdm_instance_url=os.environ["CATCHER_URL"].rstrip(" /"),
            username=os.environ["CATCHER_USERNAME"],
            password=os.environ["CATCHER_PASSWORD"],
            license=os.environ["CATCHER_LICENSE"],
        )

    return run_func_with_credentials


def print_result(func: Callable[..., str]) -> Callable[..., None]:

    def result_printer(*args, **kwargs) -> None:
        result = func(*args, **kwargs)
        print(result)

    return result_printer


def print_namedtuples_as_tsv(
    func: Callable[..., str],
    namedtuple_type: type[NamedTuple],
    parser: Callable[[str], Iterator[NamedTuple]]
) -> Callable[..., None]:

    def tsv_printer(*args, **kwargs) -> None:
        xml_str = func(*args, **kwargs)
        writer = csv.DictWriter(
            f=sys.stdout,
            fieldnames=namedtuple_type._fields,
            dialect="excel-tab",
        )
        writer.writeheader()
        for nt in parser(xml_str):
            writer.writerow(nt._asdict())

    return tsv_printer


class CatalogCollectionInfo(NamedTuple):
    alias: Optional[str]
    name: Optional[str]
    fullres_enabled: Optional[bool]


def parse_catalog(catalog: str) -> Iterator[CatalogCollectionInfo]:
    root = ET.fromstring(catalog)
    for collection_elem in root.iter("collection"):
        fullres_value = get_elem_text_or_none(
            collection_elem,
            "collection_fullres",
            "fullres_enabled",
        )
        yield CatalogCollectionInfo(
            alias=get_elem_text_or_none(collection_elem, "collection_alias"),
            name=get_elem_text_or_none(collection_elem, "collection_name"),
            fullres_enabled=fullres_value != "no",
        )


print_catalog_as_tsv = functools.partial(
    print_namedtuples_as_tsv,
    namedtuple_type=CatalogCollectionInfo,
    parser=parse_catalog,
)


class CollectionFieldInfo(NamedTuple):
    admin: Optional[bool]
    nickname: Optional[str]
    name: Optional[str]
    type: Optional[str]
    size: Optional[bool]
    search: Optional[bool]
    hidden: Optional[bool]
    vocab: Optional[bool]
    vocdb: Optional[str]
    dcmap: Optional[str]
    req: Optional[bool]
    readonly: Optional[bool]
    tag: Optional[str]


def parse_collection_config(
    collection_config: str,
) -> Iterator[CollectionFieldInfo]:
    root = ET.fromstring(collection_config)
    for field_elem in root.iter("field"):
        admin = get_elem_text_or_none(field_elem, "admin")
        size = get_elem_text_or_none(field_elem, "size")
        search = get_elem_text_or_none(field_elem, "search")
        hidden = get_elem_text_or_none(field_elem, "hidden")
        vocab = get_elem_text_or_none(field_elem, "vocab")
        req = get_elem_text_or_none(field_elem, "req")
        readonly = get_elem_text_or_none(field_elem, "readonly")
        yield CollectionFieldInfo(
            admin=None if admin is None else int_str_to_bool(admin),
            nickname=get_elem_text_or_none(field_elem, "nickname"),
            name=get_elem_text_or_none(field_elem, "name"),
            type=get_elem_text_or_none(field_elem, "type"),
            size=None if size is None else int_str_to_bool(size),
            search=None if search is None else int_str_to_bool(search),
            hidden=None if hidden is None else int_str_to_bool(hidden),
            vocab=None if vocab is None else int_str_to_bool(vocab),
            vocdb=get_elem_text_or_none(field_elem, "vocdb"),
            dcmap=get_elem_text_or_none(field_elem, "dcmap"),
            req=None if req is None else int_str_to_bool(req),
            readonly=None if readonly is None else int_str_to_bool(readonly),
            tag=get_elem_text_or_none(field_elem, "tag"),
        )


def int_str_to_bool(int_str: str) -> bool:
    if "0" == int_str:
        return False
    if "1" == int_str:
        return True
    raise ValueError(int_str)


print_collection_config_as_tsv = functools.partial(
    print_namedtuples_as_tsv,
    namedtuple_type=CollectionFieldInfo,
    parser=parse_collection_config,
)


def print_terms_as_text(func: Callable[..., str]) -> Callable[..., None]:

    def text_printer(*args, **kwargs) -> None:
        terms_xml = func(*args, **kwargs)
        print("\n".join(parse_terms(terms_xml)))

    return text_printer


def parse_terms(terms: str) -> list[str]:
    root = ET.fromstring(terms)
    return [
        term for term_elem in root.iter("term") if (term := term_elem.text)
    ]


def get_elem_text_or_none(elem: ET.Element, *tag: str) -> Optional[str]:
    if not tag:
        raise ValueError("no tags given")
    result: Optional[ET.Element] = elem
    for t in tag:
        result = result.find(t)
        if result is None:
            return None
    return result.text

import json
import os
import sys

import zeep

from typing import Any, Literal
from typing_extensions import TypeAlias


JsonObject: TypeAlias = dict[str, Any]


def credentials_from_environ(func):

    def run_func_with_credentials(*args, **kwargs) -> None:
        func(
            *args,
            **kwargs,
            cdm_instance_url=os.environ["CATCHER_URL"].rstrip(" /"),
            username=os.environ["CATCHER_USERNAME"],
            password=os.environ["CATCHER_PASSWORD"],
            license=os.environ["CATCHER_LICENSE"],
        )

    return run_func_with_credentials


CATCHER_SERVICE_URL = (
    "https://worldcat.org/webservices/contentdm/catcher/6.0/CatcherService.wsdl"
)


# getWSVersion() -> return: xsd:string


def catcher_ws_version() -> None:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    ws_version = catcher.service.getWSVersion()
    print(ws_version)


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
) -> None:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    http_version = catcher.service.getCONTENTdmHTTPTransferVersion(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
    )
    print(http_version)


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
) -> None:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    catalog = catcher.service.getCONTENTdmCatalog(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
        license=license,
    )
    print(catalog)


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
) -> None:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    collection_config = catcher.service.getCONTENTdmCollectionConfig(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
        license=license,
        collection=f"/{cdm_collection_alias.lstrip('/')}",
    )
    print(collection_config)


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
) -> None:
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    terms = catcher.service.getCONTENTdmControlledVocabTerms(
        cdmurl=cdm_instance_url,
        username=username,
        password=password,
        license=license,
        collection=f"/{cdm_collection_alias.lstrip('/')}",
        field=cdm_field_nickname,
    )
    print(terms)


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
    with open(catcher_json_file_path, mode="r", encoding="utf-8") as fp:
        additions: list[JsonObject] = json.load(fp=fp)
    catcher = zeep.Client(CATCHER_SERVICE_URL)
    factory = catcher.type_factory("ns0")
    for json_object in additions:
        response = catcher.service.processCONTENTdm(
            action=action,
            cdmurl=cdm_instance_url,
            username=username,
            password=password,
            license=license,
            collection=f"/{cdm_collection_alias.lstrip('/')}",
            disableValidation="true",
            metadata=factory.metadataWrapper(
                metadataList={
                    "metadata": [
                        factory.metadata(field=field, value=value)
                        for field, value in sort_metadata_json_object(
                            json_object
                        ).items()
                    ],
                },
            ),
        )
        print(response, file=sys.stderr)


def sort_metadata_json_object(obj: JsonObject) -> JsonObject:
    sort_order: list[str] = []
    if "dmrecord" in obj:
        sort_order.append("dmrecord")
    if "title" in obj:
        sort_order.append("title")
    sort_order.extend(key for key in obj if key not in ["dmrecord", "title"])
    return {key: obj[key] for key in sort_order}

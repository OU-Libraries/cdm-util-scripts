import requests
import tqdm

import json
import re

from typing import List, Dict, Any

from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api


def config_ids_to_cdm_nicks(
    config: List[Dict[str, Any]], field_mapping: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    labels_to_config_ids = {
        field_config["label"]: field_config["@id"] for field_config in config
    }
    return {labels_to_config_ids[name]: nicks for name, nicks in field_mapping.items()}


def structured_data_to_catcher_edit(
    dmrecord: str, data: List[Dict[str, Any]], ids_to_nicks: Dict[str, List[str]]
) -> Dict[str, str]:
    edit = {"dmrecord": dmrecord}
    for field_data in data:
        config_id = field_data["config"]
        nicks = ids_to_nicks[config_id]
        value = field_data["value"]
        value = value if isinstance(value, str) else "; ".join(value)
        for nick in nicks:
            edit[nick] = value
    return edit


def ftpmdc2catcher(
    ftp_slug: str,
    ftp_project_name: str,
    field_mapping_csv_path: str,
    output_file_path: str,
) -> None:
    field_mapping = cdm_api.read_csv_field_mapping(field_mapping_csv_path)

    with requests.Session() as session:
        print("Locating collection manifest...")
        manifest_url = ftp_api.get_collection_manifest_url(
            slug=ftp_slug,
            collection_name=ftp_project_name,
            session=session,
        )

        print("Getting structured data configuration...")
        work_configuration = ftp_api.get_project_structured_data_work_config(
            manifest_url, session=session
        )
        page_configuration = ftp_api.get_project_structured_data_page_config(
            manifest_url, session=session
        )
        if work_configuration is None and page_configuration is None:
            raise ValueError("project has no Metadata Fields configuration")

        work_config_ids_to_cdm_nicks = (
            config_ids_to_cdm_nicks(work_configuration["config"], field_mapping)
            if work_configuration
            else None
        )
        page_config_ids_to_cdm_nicks = (
            config_ids_to_cdm_nicks(page_configuration["config"], field_mapping)
            if page_configuration
            else None
        )

        print("Gathering project metadata...")
        ftp_collection = ftp_api.get_ftp_collection(
            manifest_url=manifest_url, session=session
        )
        edits = []
        for ftp_work in tqdm.tqdm(ftp_collection.works):
            # Keep page-level edits before object-level edits to avoid locking CONTENTdm objects
            if page_configuration:
                manifest = ftp_api.get_ftp_manifest(
                    ftp_work.ftp_manifest_url, session=session
                )
                for canvas in manifest["sequences"]["canvases"]:
                    dmrecord = re.match(
                        r".*/iiif/[^:]+:(\d+)/canvas/c\d+$", canvas["@id"]
                    ).groups()[0]
                    canvas_structured = [
                        seeAlso
                        for seeAlso in canvas["seeAlso"]
                        if seeAlso["label"].startswith("Structured data")
                    ][0]
                    response = session.get(canvas_structured["@id"])
                    response.raise_for_status()
                    page_data = response.json()
                    edit = structured_data_to_catcher_edit(
                        dmrecord, page_data["data"], page_config_ids_to_cdm_nicks
                    )
                    edits.append(edit)
            if work_configuration:
                work_structured_url = (
                    ftp_work.ftp_manifest_url.rpartition("/")[0] + "/structured"
                )
                response = session.get(work_structured_url)
                response.raise_for_status()
                result = response.json()
                edit = structured_data_to_catcher_edit(
                    ftp_work.dmrecord, result["data"], work_config_ids_to_cdm_nicks
                )
                edits.append(edit)

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(edits, fp, indent=2)

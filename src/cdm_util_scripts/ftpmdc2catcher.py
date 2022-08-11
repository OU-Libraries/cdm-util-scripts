import requests
import tqdm

import json

from typing import List, Dict

from cdm_util_scripts import ftp_api2 as ftp_api
from cdm_util_scripts import cdm_api


def config_ids_to_cdm_nicks(
    config: ftp_api.FtpStructuredDataConfig, field_mapping: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    if not config.fields:
        return {}
    labels_to_config_ids = {
        field_config.label: field_config.url for field_config in config.fields
    }
    return {labels_to_config_ids[name]: nicks for name, nicks in field_mapping.items()}


def structured_data_to_catcher_edit(
    dmrecord: str, data: ftp_api.FtpStructuredData, ids_to_nicks: Dict[str, List[str]]
) -> Dict[str, str]:
    edit = {"dmrecord": dmrecord}
    for field_data in data.data:
        config_id = field_data.config
        nicks = ids_to_nicks[config_id]
        value = field_data.value
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
        print("Requesting project information...")
        ftp_project = ftp_api.request_ftp_project(
            base_url=ftp_api.FTP_HOSTED_BASE_URL,
            slug=ftp_slug,
            project_label=ftp_project_name,
            session=session
        )

        print("Requesting structured data configuration...")
        work_configuration = ftp_project.request_work_structured_data_config(session=session)
        page_configuration = ftp_project.request_page_structured_data_config(session=session)
        if not work_configuration.fields and not page_configuration.fields:
            raise ValueError("project has no Metadata Fields configuration")

        work_config_ids_to_cdm_nicks = config_ids_to_cdm_nicks(work_configuration, field_mapping)
        page_config_ids_to_cdm_nicks = config_ids_to_cdm_nicks(page_configuration, field_mapping)

        if page_configuration.fields:
            print("Requesting project works...")
            ftp_project.request_works(session=session)

        edits = []
        for ftp_work in tqdm.tqdm(ftp_project.works):
            # Keep page-level edits before object-level edits to avoid locking CONTENTdm objects
            if page_configuration.fields:
                for ftp_page in ftp_work.pages:
                    edit = structured_data_to_catcher_edit(
                        dmrecord=ftp_page.cdm_page_dmrecord,
                        data=ftp_page.request_structured_data(session=session),
                        ids_to_nicks=page_config_ids_to_cdm_nicks,
                    )
                    edits.append(edit)
            if work_configuration:
                edit = structured_data_to_catcher_edit(
                    dmrecord=ftp_work.cdm_object_dmrecord,
                    data=ftp_work.request_structured_data(session=session),
                    ids_to_nicks=work_config_ids_to_cdm_nicks
                )
                edits.append(edit)

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(edits, fp, indent=2)

import requests
import tqdm

import json

from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api


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
        work_configuration = ftp_api.get_collection_structured_data_configuration(
            manifest_url=manifest_url,
            level="work",
            session=session,
        )
        work_labels_to_config_ids = {
            field_config["label"]: field_config["@id"] for field_config in work_configuration["config"]
        }
        config_ids_to_cdm_nicks = {
            work_labels_to_config_ids[name]: nicks for name, nicks in field_mapping.items()
        }
        page_configuration = ftp_api.get_collection_structured_data_configuration(
            manifest_url=manifest_url,
            level="page",
            session=session,
        )
        assert not page_configuration["config"], "page-level structured metadata unimplemented"
        print("Gathering work metadata...")
        ftp_collection = ftp_api.get_ftp_collection(
            manifest_url=manifest_url,
            session=session
        )
        edits = []
        for ftp_work in tqdm.tqdm(ftp_collection.works):
            work_structured_url = ftp_work.ftp_manifest_url.rpartition("/")[0] + "/structured"
            response = session.get(work_structured_url)
            response.raise_for_status()
            result = response.json()
            edit = {"dmrecord": ftp_work.dmrecord}
            for field_data in result["data"]:
                config_id = field_data["config"]
                nicks = config_ids_to_cdm_nicks[config_id]
                value = field_data["value"]
                value = value if isinstance(value, str) else "; ".join(value)
                for nick in nicks:
                    edit[nick] = value
            edits.append(edit)

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(edits, fp, indent=2)

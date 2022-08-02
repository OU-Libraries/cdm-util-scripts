import requests
import tqdm

import json
import argparse

from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api

from typing import Optional, Iterable


def main(test_args: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Get FromThePage Metadata Creation data as cdm-catcher JSON edits",
    )
    parser.add_argument("slug", type=str, help="FromThePage user slug")
    parser.add_argument("collection_name", type=str, help="CONTENTdm collection name used by FromThePage")
    parser.add_argument("field_mapping_csv", type=str, help="CSV file of FromThePage field labels mapped to CONTENTdm field nicknames")
    parser.add_argument("output_file", type=str, help="Path to write cdm-catcher JSON file")
    args = parser.parse_args(test_args)

    field_mapping = cdm_api.read_csv_field_mapping(args.field_mapping_csv)

    with requests.Session() as session:
        print("Locating collection manifest...")
        manifest_url = ftp_api.get_collection_manifest_url(
            slug=args.slug,
            collection_name=args.collection_name,
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

    with open(args.output_file, mode="w", encoding="utf-8") as fp:
        json.dump(edits, fp, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

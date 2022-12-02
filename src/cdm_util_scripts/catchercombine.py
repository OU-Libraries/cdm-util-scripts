import requests
import tqdm

import json

from cdm_util_scripts import cdm_api

from typing import List, Dict


def catchercombine(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    catcher_json_file_path: str,
    output_file_path: str,
    prepend: bool = False,
    show_progress: bool = True,
) -> None:
    """Combine a cdm-catcher JSON edit with data currently in CONTENTdm."""
    progress_bar = tqdm.tqdm if show_progress else (lambda obj: obj)
    with open(catcher_json_file_path, mode="r", encoding="utf-8") as fp:
        catcher_edits = json.load(fp)

    combined_edits: List[Dict[str, str]] = []
    with requests.Session() as session:
        print("Requesting CONTENTdm field info...")
        cdm_field_infos = cdm_api.request_field_infos(
            instance_url=cdm_instance_url,
            collection_alias=cdm_collection_alias,
            session=session,
        )
        nick_is_controlled = {
            field_info.nick: bool(field_info.vocab) for field_info in cdm_field_infos
        }
        print("Requesting CONTENTdm item info...")
        for edit in progress_bar(catcher_edits):
            item_info = cdm_api.request_item_info(
                instance_url=cdm_instance_url,
                collection_alias=cdm_collection_alias,
                dmrecord=edit["dmrecord"],
                session=session,
            )
            combined_edit = {"dmrecord": edit["dmrecord"]}
            for nick, edit_value in edit.items():
                if nick == "dmrecord":
                    continue
                cdm_value = item_info[nick]
                join_str = "; " if nick_is_controlled[nick] else " "
                values = [cdm_value, edit_value]
                values = [value for value in values if value]
                if prepend:
                    values.reverse()
                combined_edit[nick] = join_str.join(values)
            combined_edits.append(combined_edit)

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(combined_edits, fp, indent=2)

import requests
import tqdm

import json

from cdm_util_scripts import cdm_api

from typing import List, Dict


def catchercombineterms(
    cdm_instance_url: str,
    cdm_collection_alias: str,
    catcher_json_file_path: str,
    output_file_path: str,
    sort_terms: bool = True,
    show_progress: bool = True,
) -> None:
    """Combine a cdm-catcher JSON edit of controlled vocabulary fields with terms currently in CONTENTdm"""
    progress_bar = tqdm.tqdm if show_progress else (lambda obj: obj)
    with open(catcher_json_file_path, mode="r", encoding="utf-8") as fp:
        catcher_edits = json.load(fp)

    combined_edits: List[Dict[str, str]] = []
    with requests.Session() as session:
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
                cdm_terms = split_terms(cdm_value)
                edit_terms = split_terms(edit_value)
                combined_terms = cdm_terms + [
                    term for term in edit_terms if term not in cdm_terms
                ]
                if sort_terms:
                    combined_terms.sort()
                combined_edit[nick] = "; ".join(combined_terms)
            combined_edits.append(combined_edit)

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(combined_edits, fp, indent=2)


def split_terms(value: str) -> List[str]:
    return [term.strip() for term in value.split(";") if term and not term.isspace()]

import requests
import tqdm

import json

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api

from typing import Optional, List, Iterable, Dict, Callable, Tuple


class MatchModes:
    by_object = "object"
    by_page = "page"


PagePicker = Callable[[ftp_api.FtpFieldBasedTranscription], Optional[Dict[str, str]]]


class PagePickers:
    @staticmethod
    def first_page(pages: ftp_api.FtpFieldBasedTranscription) -> Optional[Dict[str, str]]:
        if pages:
            return pages[0]
        return None

    @staticmethod
    def first_filled_page(pages: ftp_api.FtpFieldBasedTranscription) -> Optional[Dict[str, str]]:
        for page in pages:
            if page and any(page.values()):
                return page
        return None


def ftpfields2catcher(
    match_mode: str,
    ftp_slug: str,
    ftp_project_name: str,
    field_mapping_csv_path: str,
    output_file_path: str,
) -> None:
    field_mapping = cdm_api.read_csv_field_mapping(field_mapping_csv_path)

    with requests.Session() as session:
        ftp_project = ftp_api.request_ftp_project_and_works(
            base_url=ftp_api.FTP_HOSTED_BASE_URL,
            slug=ftp_slug,
            project_label=ftp_project_name,
            session=session,
        )
        field_transcriptions = []
        for ftp_work in tqdm.tqdm(ftp_project.works):
            field_transcriptions.append(
                ftp_work.request_transcript_fields(session=session)
            )

        if match_mode == MatchModes.by_object:
            catcher_data, dropped_works = map_ftp_works_as_cdm_objects(
                ftp_works=ftp_project.works,
                field_transcriptions=field_transcriptions,
                field_mapping=field_mapping,
                page_picker=PagePickers.first_filled_page,
            )
            print(
                f"Collected {len(catcher_data)} CONTENTdm object edits from {len(ftp_project.works)} FromThePage works."
            )
        elif match_mode == MatchModes.by_page:
            catcher_data, dropped_works = map_ftp_works_as_cdm_pages(
                ftp_works=ftp_project.works,
                field_transcriptions=field_transcriptions,
                field_mapping=field_mapping,
                session=session,
            )
            print(
                f"Collected {len(catcher_data)} CONTENTdm page edits from {len(ftp_project.works)} FromThePage works."
            )
        else:
            raise ValueError(f"invalid match mode {match_mode!r}")

    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(catcher_data, fp, indent=2)


def map_ftp_works_as_cdm_objects(
    ftp_works: Iterable[ftp_api.FtpWork],
    field_transcriptions: Iterable[ftp_api.FtpFieldBasedTranscription],
    field_mapping: cdm_api.CdmFieldMapping,
    page_picker: PagePicker,
) -> Tuple[List[Dict[str, str]], List[ftp_api.FtpWork]]:
    catcher_data = []
    dropped_works = []
    for ftp_work, field_transcription in tqdm.tqdm(
        list(zip(ftp_works, field_transcriptions))
    ):
        cdm_object = map_ftp_work_as_cdm_object(
            ftp_work=ftp_work,
            field_transcription=field_transcription,
            field_mapping=field_mapping,
            page_picker=page_picker,
        )
        if cdm_object:
            catcher_data.append(cdm_object)
        else:
            dropped_works.append(ftp_work)
    return catcher_data, dropped_works


def map_ftp_work_as_cdm_object(
    ftp_work: ftp_api.FtpWork,
    field_transcription: ftp_api.FtpFieldBasedTranscription,
    field_mapping: cdm_api.CdmFieldMapping,
    page_picker: PagePicker,
) -> Optional[Dict[str, str]]:
    object_page = page_picker(field_transcription)
    if not object_page:
        return None
    return {
        "dmrecord": ftp_work.cdm_object_dmrecord,
        **cdm_api.apply_field_mapping(fields=object_page, field_mapping=field_mapping),
    }


def map_ftp_works_as_cdm_pages(
    ftp_works: Iterable[ftp_api.FtpWork],
    field_transcriptions: Iterable[ftp_api.FtpFieldBasedTranscription],
    field_mapping: cdm_api.CdmFieldMapping,
    session: requests.Session,
) -> Tuple[List[Dict[str, str]], List[ftp_api.FtpWork]]:
    catcher_data = []
    dropped_works = []
    for ftp_work, field_transcription in tqdm.tqdm(
        list(zip(ftp_works, field_transcriptions))
    ):
        pages = map_ftp_work_as_cdm_pages(
            ftp_work=ftp_work,
            field_transcription=field_transcription,
            field_mapping=field_mapping,
            session=session,
        )
        if pages:
            catcher_data.extend(pages)
        else:
            dropped_works.append(ftp_work)
    return catcher_data, dropped_works


def map_ftp_work_as_cdm_pages(
    ftp_work: ftp_api.FtpWork,
    field_transcription: ftp_api.FtpFieldBasedTranscription,
    field_mapping: cdm_api.CdmFieldMapping,
    session: requests.Session,
) -> List[Dict[str, str]]:
    if not any(page for page in field_transcription):
        return []
    if all(ftp_page.cdm_page_dmrecord is None for ftp_page in ftp_work.pages):
        # There can be 1 page compound objects, so a check is necessary
        item_info = get_ftp_work_cdm_item_info(ftp_work=ftp_work, session=session)
        if item_info["find"].endswith(".cpd"):
            load_cdm_page_pointers(ftp_work, session)
        else:
            # It's a simple object, the object is its own page
            ftp_work.pages[0].cdm_page_dmrecord = ftp_work.cdm_object_dmrecord
    page_data = []
    for ftp_page, fields in zip(ftp_work.pages, field_transcription):
        if fields:
            page_data.append(
                {
                    "dmrecord": ftp_page.cdm_page_dmrecord,
                    **cdm_api.apply_field_mapping(
                        fields=fields, field_mapping=field_mapping
                    ),
                }
            )
    return page_data


def get_ftp_work_cdm_item_info(
    ftp_work: ftp_api.FtpWork, session: requests.Session
) -> cdm_api.CdmItemInfo:
    return cdm_api.request_item_info(
        instance_url=ftp_work.cdm_instance_base_url,
        collection_alias=ftp_work.cdm_collection_alias,
        dmrecord=ftp_work.cdm_object_dmrecord,
        session=session,
    )


def load_cdm_page_pointers(
    ftp_work: ftp_api.FtpWork, session: requests.Session
) -> None:
    page_pointers = cdm_api.request_page_pointers(
        instance_url=ftp_work.cdm_instance_base_url,
        collection_alias=ftp_work.cdm_collection_alias,
        dmrecord=ftp_work.cdm_object_dmrecord,
        session=session,
    )
    for ftp_page, pointer in zip(ftp_work.pages, page_pointers):
        ftp_page.cdm_page_dmrecord = pointer

import requests
import tqdm

import json
import enum

from typing import List, Dict, Iterator, Tuple

from cdm_util_scripts import ftp_api
from cdm_util_scripts import cdm_api


class Level(str, enum.Enum):
    WORK = "work"
    PAGE = "page"
    BOTH = "both"
    AUTO = "auto"


def ftpstruct2catcher(
    ftp_slug: str,
    ftp_project_name: str,
    field_mapping_csv_path: str,
    level: Level,
    output_file_path: str,
    show_progress: bool = True,
) -> None:
    """Request FromThePage Metadata Fields and/or Transcription Fields data as cdm-catcher JSON edits"""
    progress_bar = tqdm.tqdm if show_progress else (lambda obj: obj)
    field_mapping = cdm_api.read_csv_field_mapping(field_mapping_csv_path)

    with requests.Session() as session:
        print("Requesting project information...")
        ftp_project = ftp_api.request_ftp_project_and_works(
            instance_url=ftp_api.FTP_HOSTED_URL,
            slug=ftp_slug,
            project_label=ftp_project_name,
            session=session,
            show_progress=show_progress,
        )

        works_count = len(ftp_project.works)
        pages_count = sum(len(ftp_work.pages) for ftp_work in ftp_project.works)
        works_described_count, pages_with_transcripts_count = count_statuses(ftp_project)
        print(f"{ftp_project.label} has {works_count} works with {pages_count} total pages")
        if level is not Level.PAGE:
            print(f"Found {works_described_count} works described")
        if level is not Level.WORK:
            print(f"Found {pages_with_transcripts_count} pages with transcripts")

        print("Requesting structured data configuration...")
        if level in (Level.AUTO, Level.BOTH, Level.WORK):
            work_configuration = ftp_project.request_work_structured_data_config(
                session=session
            )
            work_config_ids_to_cdm_nicks = config_ids_to_cdm_nicks(
                work_configuration, field_mapping
            )
            has_work_configuration = bool(work_configuration.fields)
        else:
            work_configuration = None
            work_config_ids_to_cdm_nicks = None
            has_work_configuration = None

        if level in (Level.AUTO, Level.BOTH, Level.PAGE):
            page_configuration = ftp_project.request_page_structured_data_config(
                session=session
            )
            page_config_ids_to_cdm_nicks = config_ids_to_cdm_nicks(
                page_configuration, field_mapping
            )
            has_page_configuration = bool(page_configuration.fields)
        else:
            page_configuration = None
            page_config_ids_to_cdm_nicks = None
            has_page_configuration = None

        if level in (Level.BOTH, Level.WORK) or (
            level is Level.AUTO and has_work_configuration
        ):
            unmapped_work_fields = list(unmapped_fields(work_configuration, field_mapping))
            if unmapped_work_fields:
                print(f"Warning: {len(unmapped_work_fields)} unmapped work-level field(s):")
                for field_config in unmapped_work_fields:
                    print(f"  {field_config.label!r}")

        if level in (Level.BOTH, Level.PAGE) or (
            level is Level.AUTO and has_page_configuration
        ):
            unmapped_page_fields = list(unmapped_fields(page_configuration, field_mapping))
            if unmapped_page_fields:
                print(f"Warning: {len(unmapped_page_fields)} unmapped page-level field(s):")
                for field_config in unmapped_page_fields:
                    print(f"  {field_config.label!r}")

        if level in (Level.BOTH, Level.WORK) and not work_config_ids_to_cdm_nicks:
            raise ValueError(
                "unable to map FromThePage work-level fields to CONTENTdm nicks"
            )
        if level in (Level.BOTH, Level.PAGE) and not page_config_ids_to_cdm_nicks:
            raise ValueError(
                "unable to map FromThePage page-level fields to CONTENTdm nicks"
            )
        if not work_config_ids_to_cdm_nicks and not page_config_ids_to_cdm_nicks:
            raise ValueError("unable to map any FromThePage fields to CONTENTdm nicks")

        print("Requesting structured data...")
        edits = []
        for ftp_work in progress_bar(ftp_project.works):
            # Keep page-level edits before object-level edits to avoid locking CONTENTdm objects
            if page_config_ids_to_cdm_nicks:
                for ftp_page in ftp_work.pages:
                    if not ftp_page.has_transcript:
                        continue
                    edit = structured_data_to_catcher_edit(
                        dmrecord=ftp_page.cdm_page_dmrecord,
                        data=ftp_page.request_structured_data(session=session),
                        ids_to_nicks=page_config_ids_to_cdm_nicks,
                    )
                    edits.append(edit)
            if work_config_ids_to_cdm_nicks:
                if not ftp_work.metadata_status == "described":
                    continue
                edit = structured_data_to_catcher_edit(
                    dmrecord=ftp_work.cdm_object_dmrecord,
                    data=ftp_work.request_structured_data(session=session),
                    ids_to_nicks=work_config_ids_to_cdm_nicks,
                )
                edits.append(edit)

    print(f"Writing {len(edits)} catcher edits...")
    with open(output_file_path, mode="w", encoding="utf-8") as fp:
        json.dump(edits, fp, indent=2)


def config_ids_to_cdm_nicks(
    config: ftp_api.FtpStructuredDataConfig, field_mapping: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    if not config.fields:
        return {}
    labels_to_config_ids = {
        field_config.label: field_config.url for field_config in config.fields
    }
    return {labels_to_config_ids[name]: nicks for name, nicks in field_mapping.items()}


def unmapped_fields(
    config: ftp_api.FtpStructuredDataConfig, field_mapping: Dict[str, List[str]]
) -> Iterator[ftp_api.FtpStructuredDataFieldConfig]:
    mapped_labels = set(label for label, nicks in field_mapping.items() if nicks)
    for field_config in config.fields:
        if field_config.label not in mapped_labels:
            yield field_config


def count_statuses(ftp_project: ftp_api.FtpProject) -> Tuple[int, int]:
    works_described = 0
    pages_with_transcripts = 0
    for ftp_work in ftp_project.works:
        works_described += 1 if ftp_work.metadata_status == "described" else 0
        for ftp_page in ftp_work.pages:
            pages_with_transcripts += 1 if ftp_page.has_transcript else 0
    return works_described, pages_with_transcripts


def structured_data_to_catcher_edit(
    dmrecord: str, data: ftp_api.FtpStructuredData, ids_to_nicks: Dict[str, List[str]]
) -> Dict[str, str]:
    edit = {"dmrecord": dmrecord}
    for field_data in data.data:
        config_id = field_data.config
        if config_id not in ids_to_nicks:
            continue
        nicks = ids_to_nicks[config_id]
        if isinstance(field_data.value, str):
            value = field_data.value
        else:
            value = "; ".join(field_data.value)
        value = normalize_cdm_edit_str(value)
        for nick in nicks:
            edit[nick] = value
    return edit


# CONTENTdm seems to use LF exclusively
# While FromThePage provides CRLF
def normalize_cdm_edit_str(s: str) -> str:
    return s.strip().replace("\r\n", "\n")

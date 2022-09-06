import requests
import jinja2
import tqdm

from datetime import datetime
from pathlib import Path

from cdm_util_scripts import cdm_api
from cdm_util_scripts import ftp_api

from typing import Dict, List, FrozenSet, Tuple


def scanftpvocabs(
    ftp_slug: str,
    ftp_project_name: str,
    cdm_instance_url: str,
    cdm_collection_alias: str,
    field_mapping_csv_path: str,
    report_path: str,
) -> None:
    cdm_field_mapping = cdm_api.read_csv_field_mapping(field_mapping_csv_path)

    with requests.Session() as session:
        print("Requesting FromThePage project data...")
        ftp_project = ftp_api.request_ftp_project_and_works(
            instance_url=ftp_api.FTP_HOSTED_URL,
            slug=ftp_slug,
            project_label=ftp_project_name,
            session=session,
        )
        print("Requesting FromThePage transcriptions...")
        ftp_transcriptions = []
        for ftp_work in tqdm.tqdm(ftp_project.works):
            ftp_transcriptions.append(
                ftp_work.request_transcript_fields(session=session)
            )
        print("Requesting CONTENTdm collection data...")
        cdm_field_infos = cdm_api.request_field_infos(
            instance_url=cdm_instance_url,
            collection_alias=cdm_collection_alias,
            session=session,
        )
        cdm_vocabs = {
            vocab_info: frozenset(vocab)
            for vocab_info, vocab in cdm_api.request_vocabs(
                instance_url=cdm_instance_url,
                collection_alias=cdm_collection_alias,
                field_infos=cdm_field_infos,
                session=session,
            ).items()
        }

    (
        uncontrolled_terms_by_field_nick,
        controlled_cdm_field_infos,
        mapped_controlled_cdm_field_infos,
        unmapped_controlled_cdm_field_infos,
    ) = scan_vocabs(
        cdm_field_mapping=cdm_field_mapping,
        cdm_field_infos=cdm_field_infos,
        cdm_vocabs=cdm_vocabs,
        ftp_project=ftp_project,
        ftp_transcriptions=ftp_transcriptions,
    )

    print("Compiling report...")
    report = {
        "ftp_slug": ftp_slug,
        "ftp_project_name": ftp_project_name,
        "cdm_instance_url": cdm_instance_url,
        "cdm_collection_alias": cdm_collection_alias,
        "report_datetime": datetime.now().isoformat(),
        "cdm_field_infos": cdm_field_infos,
        "cdm_field_mapping": cdm_field_mapping,
        "controlled_cdm_field_infos": controlled_cdm_field_infos,
        "unmapped_controlled_cdm_field_infos": unmapped_controlled_cdm_field_infos,
        "mapped_controlled_cdm_field_infos": mapped_controlled_cdm_field_infos,
        "cdm_vocabs": cdm_vocabs,
        "uncontrolled_terms_by_field_nick": uncontrolled_terms_by_field_nick,
    }

    report_str = report_to_html(
        {
            **report,
            "cdm_nick_to_name": {
                field_info.nick: field_info.name for field_info in cdm_field_infos
            },
        }
    )
    with open(report_path, mode="w", encoding="utf-8") as fp:
        fp.write(report_str)


def scan_vocabs(
    cdm_field_mapping: cdm_api.CdmFieldMapping,
    cdm_field_infos: List[cdm_api.CdmFieldInfo],
    cdm_vocabs: Dict[cdm_api.CdmVocabInfo, FrozenSet[str]],
    ftp_project: ftp_api.FtpProject,
    ftp_transcriptions: List[ftp_api.FtpFieldBasedTranscription],
) -> Tuple[
    Dict[str, Dict[str, List[ftp_api.FtpPage]]],
    List[cdm_api.CdmFieldInfo],
    List[cdm_api.CdmFieldInfo],
    List[cdm_api.CdmFieldInfo],
]:
    mapped_cdm_nicks = {nick for nicks in cdm_field_mapping.values() for nick in nicks}
    controlled_cdm_field_infos = [
        field_info for field_info in cdm_field_infos if field_info.vocab
    ]
    mapped_controlled_cdm_field_infos = []
    unmapped_controlled_cdm_field_infos = []
    for field_info in controlled_cdm_field_infos:
        if field_info.nick in mapped_cdm_nicks:
            mapped_controlled_cdm_field_infos.append(field_info)
        else:
            unmapped_controlled_cdm_field_infos.append(field_info)

    uncontrolled_terms_by_field_nick: Dict[str, Dict[str, List[ftp_api.FtpPage]]] = {
        field_info.nick: dict() for field_info in mapped_controlled_cdm_field_infos
    }
    for ftp_work, ftp_transcription in zip(ftp_project.works, ftp_transcriptions):
        for ftp_page, ftp_fields in zip(ftp_work.pages, ftp_transcription):
            if not ftp_fields:
                continue
            ftp_item_info = cdm_api.apply_field_mapping(
                ftp_fields, field_mapping=cdm_field_mapping
            )
            for field_info in mapped_controlled_cdm_field_infos:
                vocab = cdm_vocabs[field_info.get_vocab_info()]
                terms = [
                    term.strip()
                    for term in ftp_item_info[field_info.nick].split(";")
                    if term.strip()
                ]
                for term in terms:
                    if term not in vocab:
                        uncontrolled_terms_by_field_nick[field_info.nick].setdefault(
                            term, []
                        ).append(ftp_page)
    return (
        uncontrolled_terms_by_field_nick,
        controlled_cdm_field_infos,
        mapped_controlled_cdm_field_infos,
        unmapped_controlled_cdm_field_infos,
    )


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template("scanftpvocabs-report.html.j2").render(report)

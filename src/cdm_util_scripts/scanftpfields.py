import jinja2
from requests import Session
import tqdm

from datetime import datetime
import collections

import typing
from typing import List, Dict, Any, Tuple, Iterable, Iterator, Optional, FrozenSet

from cdm_util_scripts import ftp_api


def scanftpfields(
    ftp_slug: str,
    ftp_project_name: str,
    report_path: str,
) -> None:
    with Session() as session:
        print("Requesting project data...")
        ftp_project = ftp_api.request_ftp_project_and_works(
            instance_url=ftp_api.FTP_HOSTED_URL,
            slug=ftp_slug,
            project_label=ftp_project_name,
            session=session,
        )
        print("Requesting transcripts...")
        field_transcriptions = []
        for ftp_work in tqdm.tqdm(ftp_project.works):
            field_transcriptions.append(
                ftp_work.request_transcript_fields(session=session)
            )

    print("Compiling report...")
    pages_by_schema = collate_ftp_pages_by_schema(
        zip(ftp_project.works, field_transcriptions)
    )
    blank_pages = pages_by_schema.pop(None, [])
    report = {
        "report_datetime": datetime.now().isoformat(),
        "slug": ftp_slug,
        "project_id": ftp_project.project_id,
        "project_label": ftp_project.label,
        "project_manifest_url": ftp_project.url,
        "works_count": len(ftp_project.works),
        "filled_pages_count": count_filled_pages(field_transcriptions),
        "field_label_frequencies": dict(
            compile_field_frequencies(field_transcriptions)
        ),
        "pages_by_schema": pages_by_schema,
        "blank_pages": blank_pages,
    }

    report_str = report_to_html(report)
    with open(report_path, mode="w", encoding="utf-8") as fp:
        fp.write(report_str)


def collate_ftp_pages_by_schema(
    works_and_fields: Iterable[
        Tuple[ftp_api.FtpWork, ftp_api.FtpFieldBasedTranscription]
    ]
) -> Dict[Optional[FrozenSet[str]], List[Tuple[ftp_api.FtpPage, ftp_api.FtpWork]]]:
    by_schema = collections.defaultdict(list)
    for ftp_work, field_transcription in works_and_fields:
        for ftp_page, field_transcript in zip(ftp_work.pages, field_transcription):
            schema = frozenset(field_transcript) if field_transcript else None
            by_schema[schema].append((ftp_page, ftp_work))
    return dict(by_schema)


def count_filled_pages(
    field_transcriptions: Iterable[ftp_api.FtpFieldBasedTranscription],
) -> int:
    return sum(
        1
        for field_transcription in field_transcriptions
        for page_fields in field_transcription
        if page_fields
    )


def compile_field_frequencies(
    field_transcriptions: Iterable[ftp_api.FtpFieldBasedTranscription],
) -> typing.Counter[str]:
    return collections.Counter(iter_labels(field_transcriptions))


def iter_labels(
    field_transcriptions: Iterable[ftp_api.FtpFieldBasedTranscription],
) -> Iterator[str]:
    for field_transcription in field_transcriptions:
        for page_fields in field_transcription:
            if page_fields:
                yield from page_fields


def report_to_html(report: Dict[str, Any]) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template("scanftpfields-report.html.j2").render(report)

import jinja2
import requests
import tqdm

import datetime
from typing import List, FrozenSet, Dict, overload, Union, NamedTuple

from cdm_util_scripts import ftp_api


class WorkAndFields(NamedTuple):
    work: ftp_api.FtpWork
    fields: ftp_api.FtpStructuredData


class PageAndFields(NamedTuple):
    page: ftp_api.FtpPage
    fields: ftp_api.FtpStructuredData


def scanftpfields(
    ftp_slug: str,
    ftp_project_name: str,
    report_path: str,
) -> None:
    with requests.Session() as session:
        print("Requesting project data...")
        ftp_project = ftp_api.request_ftp_project(
            instance_url=ftp_api.FTP_HOSTED_URL,
            slug=ftp_slug,
            project_label=ftp_project_name,
            session=session,
        )

        print("Requesting project structured data configurations...")
        work_config = ftp_project.request_work_structured_data_config(session=session)
        page_config = ftp_project.request_page_structured_data_config(session=session)

        has_work_level_description = bool(work_config.fields)
        has_page_level_description = bool(page_config.fields)
        if not has_work_level_description and not has_page_level_description:
            print("Project has no structured data entry configured, exiting...")
            return None

        print("Requesting work data...")
        ftp_project.request_works(session=session)

        print("Requesting structured descriptions...")
        project_works_and_fields: List[WorkAndFields] = []
        project_pages_and_fields: List[PageAndFields] = []
        for work in tqdm.tqdm(ftp_project.works):
            if has_work_level_description:
                project_works_and_fields.append(
                    (work, work.request_structured_data(session=session))
                )
            if has_page_level_description:
                for page in work.pages:
                    project_pages_and_fields.append(
                        (page, page.request_structured_data(session=session))
                    )

    print("Collating field sets...")
    works_by_field_set = collate_field_sets(project_works_and_fields)
    pages_by_field_set = collate_field_sets(project_pages_and_fields)

    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    report_html = env.get_template("scanftpfields-report.html.j2").render(
        slug=ftp_slug,
        project_label=ftp_project_name,
        project_manifest_url=ftp_project.url,
        report_datetime=datetime.datetime.now().isoformat(),
        work_config=work_config,
        page_config=page_config,
        works_by_field_set=works_by_field_set,
        pages_by_field_set=pages_by_field_set,
        work_field_labels_by_config_id={
            field_config.url: field_config.label
            for field_config in work_config.fields
        },
        page_field_labels_by_config_id={
            field_config.url: field_config.label
            for field_config in page_config.fields
        },
    )

    with open(report_path, mode="w", encoding="utf-8") as fp:
        fp.write(report_html)


@overload
def collate_field_sets(
    ftp_objects_and_fields: List[WorkAndFields],
) -> Dict[FrozenSet[str], List[ftp_api.FtpWork]]:
    ...


@overload
def collate_field_sets(
    ftp_objects_and_fields: List[PageAndFields],
) -> Dict[FrozenSet[str], List[ftp_api.FtpPage]]:
    ...


def collate_field_sets(
    ftp_objects_and_fields: Union[List[PageAndFields], List[WorkAndFields]]
) -> Union[
    Dict[FrozenSet[str], List[ftp_api.FtpPage]],
    Dict[FrozenSet[str], List[ftp_api.FtpWork]],
]:
    objects_by_field_set: Union[
        Dict[FrozenSet[str], List[ftp_api.FtpPage]],
        Dict[FrozenSet[str], List[ftp_api.FtpWork]],
    ] = {}
    for ftp_object, fields in ftp_objects_and_fields:
        field_set = frozenset(field.config for field in fields.data)
        objects_by_field_set.setdefault(field_set, []).append(ftp_object)
    return objects_by_field_set

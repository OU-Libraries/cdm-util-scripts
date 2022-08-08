import jinja2
from requests import Session

from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

from typing import List, Dict, Any, Tuple

from cdm_util_scripts import ftp_api


def count_filled_pages(ftp_collection: ftp_api.FTPCollection) -> int:
    return sum(1
               for ftp_work in ftp_collection.works
               for ftp_page in ftp_work.pages if ftp_page.fields)


def compile_field_frequencies(ftp_collection: ftp_api.FTPCollection) -> Counter:
    return Counter(label
                   for ftp_work in ftp_collection.works
                   for ftp_page in ftp_work.pages if ftp_page.fields
                   for label in ftp_page.fields.keys())


def make_work_record(ftp_work: ftp_api.FTPWork) -> Dict[str, Any]:
    return {
        'ftp_manifest_url': ftp_work.ftp_manifest_url,
        'ftp_work_label': ftp_work.ftp_work_label,
        'ftp_work_url': ftp_work.ftp_work_url,
        'page_count': len(ftp_work.pages),
        'filled_pages': [],
    }


def make_page_record(ftp_page: ftp_api.FTPPage) -> Dict[str, str]:
    return {
        'ftp_page_label': ftp_page.label,
        'ftp_page_display_url': ftp_page.display_url,
        'transcription_url': ftp_page.transcription_url,
    }


def compile_field_sets(ftp_collection: ftp_api.FTPCollection) -> Tuple[List[dict], List[dict]]:
    field_sets_accumulator = defaultdict(dict)
    blank_works = []
    for ftp_work in ftp_collection.works:
        if not any(ftp_page.fields for ftp_page in ftp_work.pages):
            blank_works.append(make_work_record(ftp_work))
        else:
            for ftp_page in ftp_work.pages:
                if not ftp_page.fields:
                    continue
                field_set = frozenset(ftp_page.fields.keys())
                if ftp_work.ftp_manifest_url not in field_sets_accumulator[field_set]:
                    field_sets_accumulator[field_set][ftp_work.ftp_manifest_url] = make_work_record(ftp_work)
                field_sets_accumulator[field_set][ftp_work.ftp_manifest_url]['filled_pages'].append(make_page_record(ftp_page))
    field_sets = []
    for field_set, works in field_sets_accumulator.items():
        work_entries = list(works.values())
        work_entries.sort(key=lambda w: w['ftp_manifest_url'])
        for work in work_entries:
            work['filled_pages'].sort(key=lambda p: p['ftp_page_label'])
        field_sets.append({
            'field_set': sorted(list(field_set)),
            'number_of_works': len(works),
            'number_of_pages': sum(len(work['filled_pages']) for work in works.values()),
            'works': work_entries,
        })
    blank_works.sort(key=lambda w: w['ftp_manifest_url'])
    return field_sets, blank_works


def compile_report(ftp_collection: ftp_api.FTPCollection):
    field_sets, blank_works = compile_field_sets(ftp_collection)
    report = {
        'slug': ftp_collection.slug,
        'collection_alias': ftp_collection.alias,
        'collection_label': ftp_collection.label,
        'collection_manifest': ftp_collection.manifest_url,
        'works_count': len(ftp_collection.works),
        'filled_pages_count': count_filled_pages(ftp_collection),
        'field_label_frequencies': dict(compile_field_frequencies(ftp_collection)),
        'field_sets': field_sets,
        'bank_works': blank_works,
    }
    return report


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
    return env.get_template('scanftpfields-report.html.j2').render(report)


def scanftpfields(
        ftp_slug: str,
        ftp_project_name: str,
        rendering_label: str,
        report_parent_path: str,
) -> None:
    report_parent = Path(report_parent_path)
    with Session() as session:
        ftp_collection = ftp_api.get_and_load_ftp_collection(
            slug=ftp_slug,
            collection_name=ftp_project_name,
            rendering_label=rendering_label,
            session=session
        )

    print("Compiling report...")
    report_date = datetime.now()
    report = compile_report(ftp_collection)
    report['export_label_used'] = rendering_label
    report['report_date'] = report_date.isoformat()

    report_str = report_to_html(report)
    date_str = report_date.strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"field-label-report_{ftp_collection.alias}_{date_str}.html"
    print(f"Writing report as {filename!r}")
    with open(report_parent / filename, mode='w', encoding='utf-8') as fp:
        fp.write(report_str)

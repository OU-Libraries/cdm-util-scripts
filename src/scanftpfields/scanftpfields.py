from requests import Session
import jinja2

import json
from datetime import datetime
from collections import Counter, defaultdict
import argparse
import os

import ftpmd2catcher

from typing import List


def collection_as_filled_pages(ftp_collection: ftpmd2catcher.FTPCollection) -> List[dict]:
    filled_pages = []
    for ftp_work in ftp_collection.works:
        for ftp_page in ftp_work.pages:
            if not ftp_page.fields:
                continue
            filled_pages.append({
                'fields': frozenset(ftp_page.fields.keys()),
                'ftp_page': ftp_page,
                'ftp_work': ftp_work,
            })
    return filled_pages


def compile_field_frequencies(filled_pages: List[dict]) -> Counter:
    return Counter(label for page in filled_pages for label in page['fields'])


def compile_field_sets(filled_pages: List[dict]) -> List[dict]:
    field_sets_accumulator = defaultdict(dict)
    for filled_page in filled_pages:
        ftp_work = filled_page['ftp_work']
        ftp_page = filled_page['ftp_page']
        field_set = field_sets_accumulator[filled_page['fields']]
        if ftp_work.ftp_manifest_url not in field_set:
            field_set[ftp_work.ftp_manifest_url] = {
                'ftp_manifest_url': ftp_work.ftp_manifest_url,
                'ftp_work_label': ftp_work.ftp_work_label,
                'ftp_work_url': ftp_work.ftp_work_url,
                'pages': [],
            }
        field_set[ftp_work.ftp_manifest_url]['pages'].append({
            'ftp_page_label': ftp_page.label,
            'ftp_page_display_url': ftp_page.display_url,
            'transcription_url': ftp_page.transcription_url,
        })
    field_sets = []
    for field_set, works in field_sets_accumulator.items():
        work_entries = list(works.values())
        work_entries.sort(key=lambda w: w['ftp_manifest_url'])
        for work in work_entries:
            work['pages'].sort(key=lambda p: p['ftp_page_label'])
        field_sets.append({
            'field_set': sorted(list(field_set)),
            'number_of_works': len(works),
            'number_of_pages': sum(len(work['pages']) for work in works.values()),
            'works': work_entries,
        })
    return field_sets


def compile_report(ftp_collection: ftpmd2catcher.FTPCollection):
    filled_pages = collection_as_filled_pages(ftp_collection)
    report = {
        'slug': ftp_collection.slug,
        'collection_alias': ftp_collection.alias,
        'collection_label': ftp_collection.label,
        'collection_manifest': ftp_collection.manifest_url,
        'works_count': len(ftp_collection.works),
        'filled_pages_count': len(filled_pages),
        'field_label_frequencies': dict(compile_field_frequencies(filled_pages)),
        'field_sets': compile_field_sets(filled_pages),
    }
    return report


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
    return env.get_template('scanftpfields-report.html.j2').render(report)


def main():
    parser = argparse.ArgumentParser(description="Scan and report on a FromThePage collection's field-based transcription labels")
    parser.add_argument(
        'slug',
        type=str,
        help="FromThePage user slug"
    )
    parser.add_argument(
        'collection_name',
        type=str,
        help="Exact FromThePage project name"
    )
    parser.add_argument(
        '--output',
        choices=['html', 'json'],
        default='html',
        type=str,
        help="Specify report format"
    )
    parser.add_argument(
        '--label',
        choices=list(ftpmd2catcher.rendering_extractors.keys()),
        default='XHTML Export',
        type=str,
        help="Choose the export to use for parsing fields"
    )
    args = parser.parse_args()

    with Session() as session:
        ftp_collection = ftpmd2catcher.get_and_load_ftp_collection(
            slug=args.slug,
            collection_name=args.collection_name,
            rendering_label=args.label,
            session=session
        )

    print("Compiling report...")
    report_date = datetime.now()
    report = compile_report(ftp_collection)
    report['export_label_used'] = args.label
    report['report_date'] = report_date.isoformat()

    if args.output == 'json':
        report_str = json.dumps(report, indent=2)
    elif args.output == 'html':
        report_str = report_to_html(report)
    else:
        raise ValueError(f"invalid output type {args.output!r}")

    date_str = report_date.strftime('%Y-%m-%d_%I-%M-%S%p')
    filename = f"field-label-report_{ftp_collection.alias}_{date_str}.{args.output}"
    print(f"Writing report as {filename!r}")
    with open(filename, mode='w') as fp:
        fp.write(report_str)


if __name__ == '__main__':
    main()

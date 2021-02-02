from requests import Session
import jinja2

import json
from datetime import datetime
from collections import Counter, defaultdict
import argparse
import os

import ftpmd2catcher

from typing import List


def request_collection(manifest_url: str, rendering_label: str, session: Session) -> ftpmd2catcher.FTPCollection:
    print(f"Requesting {manifest_url}...")
    ftp_collection = ftpmd2catcher.get_ftp_collection(
        manifest_url=manifest_url,
        session=session
    )
    for n, ftp_work in enumerate(ftp_collection.works):
        print(f"Requesting manifests and {rendering_label!r} renderings {n}/{len(ftp_collection.works)}...", end='\r')
        ftpmd2catcher.load_ftp_manifest_data(
            ftp_work=ftp_work,
            rendering_label=rendering_label,
            session=session,
            verbose=False
        )
    print(end='\n')
    return ftp_collection


def collection_as_filled_pages(ftp_collection: ftpmd2catcher.FTPCollection) -> List[dict]:
    filled_pages = []
    for ftp_work in ftp_collection.works:
        for page in ftp_work.pages:
            if not page:
                continue
            filled_pages.append({
                'fields': frozenset(page.keys()),
                'ftp_work': ftp_work,
            })
    return filled_pages


def compile_field_frequencies(filled_pages: List[dict]) -> Counter:
    all_field_labels = []
    for page in filled_pages:
        all_field_labels.extend(page['fields'])
    return Counter(all_field_labels)


def compile_field_sets(filled_pages: List[dict]) -> List[dict]:
    field_sets = defaultdict(dict)
    for page in filled_pages:
        field_set = field_sets[page['fields']]
        ftp_work = page['ftp_work']
        if ftp_work.ftp_manifest_url not in field_set:
            field_set[ftp_work.ftp_manifest_url] = {
                'ftp_work_label': ftp_work.ftp_work_label,
                'ftp_work_url': ftp_work.ftp_work_url,
            }
    return [
        {
            'field_set': sorted(list(field_set)),
            'number_of_works': len(works),
            'works': sorted(
                [{'ftp_manifest': manifest_url, **work_data}
                 for manifest_url, work_data in works.items()],
                key=lambda work: work['ftp_manifest']
            )
        } for field_set, works in field_sets.items()
    ]


def compile_report(ftp_collection: ftpmd2catcher.FTPCollection):
    filled_pages = collection_as_filled_pages(ftp_collection)
    report = {
        'collection_number': ftp_collection.number,
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
    parser.add_argument('ftp_collection_number',
                        type=int)
    parser.add_argument('--output',
                        choices=['html', 'json'],
                        default='html',
                        type=str)
    parser.add_argument('--label',
                        choices=list(ftpmd2catcher.rendering_extractors.keys()),
                        default='XHTML Export',
                        type=str)
    args = parser.parse_args()

    with Session() as session:
        ftp_collection = request_collection(
            manifest_url=f'https://fromthepage.com/iiif/collection/{args.ftp_collection_number}',
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
    filename = f"field-label-report_{args.ftp_collection_number}_{date_str}.{args.output}"
    print(f"Writing report as {filename!r}")
    with open(filename, mode='w') as fp:
        fp.write(report_str)


if __name__ == '__main__':
    main()

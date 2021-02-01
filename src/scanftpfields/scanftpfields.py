from requests import Session
import jinja2

import json
from datetime import datetime
from collections import Counter, defaultdict
import argparse
import os

import ftpmd2catcher

from typing import List


def request_collection(collection_url: str, label: str, session: Session) -> List[ftpmd2catcher.CdmObject]:
    print(f"Requesting {collection_url}...")
    ftp_collection = ftpmd2catcher.get_ftp_collection(
        url=collection_url,
        session=session
    )
    for n, cdm_object in enumerate(ftp_collection):
        print(f"Requesting manifests and {label!r} renderings {n}/{len(ftp_collection)}...", end='\r')
        ftpmd2catcher.load_ftp_manifest_data(
            cdm_object=cdm_object,
            rendering_label=label,
            session=session,
            verbose=False
        )
    print(end='\n')
    return ftp_collection


def collection_as_filled_pages(ftp_collection: List[ftpmd2catcher.CdmObject]) -> List[dict]:
    filled_pages = []
    for cdm_object in ftp_collection:
        for page in cdm_object.pages:
            if not page:
                continue
            filled_pages.append({
                'fields': frozenset(page.keys()),
                'cdm_object': cdm_object,
            })
    return filled_pages


def compile_field_frequencies(filled_pages: List[dict]) -> Counter:
    all_field_labels = []
    for page in filled_pages:
        all_field_labels.extend(page['fields'])
    return Counter(all_field_labels)


def compile_field_sets(filled_pages: List[dict]) -> List[dict]:
    works_with_field_sets = defaultdict(dict)
    for page in filled_pages:
        works_with_field_set = works_with_field_sets[page['fields']]
        cdm_object = page['cdm_object']
        if cdm_object.ftp_manifest_url not in works_with_field_set:
            works_with_field_set[cdm_object.ftp_manifest_url] = {
                'ftp_work_label': cdm_object.ftp_work_label,
                'ftp_work_url': cdm_object.ftp_work_url,
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
        } for field_set, works in works_with_field_sets.items()
    ]


def report_to_html(report: dict) -> str:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__))))
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

    collection_url = f'https://fromthepage.com/iiif/collection/{args.ftp_collection_number}'

    with Session() as session:
        ftp_collection = request_collection(
            collection_url=collection_url,
            label=args.label,
            session=session
        )

    print("Compiling report...")
    report_date = datetime.now()
    filled_pages = collection_as_filled_pages(ftp_collection)
    field_label_frequencies = compile_field_frequencies(filled_pages)
    works_with_field_sets = compile_field_sets(filled_pages)

    report = {
        'collection_number': args.ftp_collection_number,
        'collection_manifest': collection_url,
        'report_date': report_date.isoformat(),
        'export_label_used': args.label,
        'works_count': len(ftp_collection),
        'filled_pages_count': len(filled_pages),
        'field_label_frequencies': dict(field_label_frequencies),
        'works_with_field_sets': works_with_field_sets,
    }

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

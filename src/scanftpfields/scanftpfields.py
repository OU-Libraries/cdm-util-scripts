from requests import Session

import json
from datetime import datetime
from collections import Counter, defaultdict
import argparse

import ftpmd2catcher
from ftp2catcher import get_ftp_manifest


def main():
    parser = argparse.ArgumentParser(description="Scan and report on a FromThePage collection's field-based transcription labels")
    parser.add_argument('ftp_collection_number',
                        type=str)
    parser.add_argument('export_label',
                        choices=list(ftpmd2catcher.rendering_extractors.keys()),
                        type=str)
    args = parser.parse_args()

    collection_url = f'https://fromthepage.com/iiif/collection/{args.ftp_collection_number}'
    fields_data = []

    with Session() as session:
        print(f"Requesting {collection_url}...")
        ftp_collection = ftpmd2catcher.get_ftp_collection(
            url=collection_url,
            session=session
        )
        for n, cdm_object in enumerate(ftp_collection):
            print(f"Requesting manifest and {args.export_label!r} renderings {n}/{len(ftp_collection)}...", end='\r')
            ftp_manifest = get_ftp_manifest(
                cdm_object.ftp_manifest_url,
                session
            )
            rendering_text = ftpmd2catcher.get_rendering(
                ftp_manifest=ftp_manifest,
                label=args.export_label,
                session=session,
                verbose=False
            )
            pages = ftpmd2catcher.rendering_extractors[args.export_label](rendering_text)
            fields_data.append({
                'work_url': ftp_manifest['related'][0]['@id'],
                'manifest_url': cdm_object.ftp_manifest_url,
                'filled_pages': [{
                    'field_count': len(page.keys()),
                    'field_labels': sorted(list(page.keys())),
                } for page in pages if page]
            })

    print("\nCompiling report...")

    all_field_labels = []
    for field_data in fields_data:
        for page in field_data['filled_pages']:
            all_field_labels.extend(page['field_labels'])

    field_label_frequencies = Counter(all_field_labels)
    # unique_field_labels = set(field_label_frequencies.keys())

    # for field_data in fields_data:
    #     for page in field_data['filled_pages']:
    #         page['missing_labels'] = sorted(list(unique_field_labels - set(page['field_labels'])))

    works_with_field_set = defaultdict(set)
    for field_data in fields_data:
        for page in field_data['filled_pages']:
            works_with_field_set[frozenset(page['field_labels'])].add(field_data['manifest_url'])

    report = {
        'collection_manifest': collection_url,
        'export_label_used': args.export_label,
        'field_label_frequencies': dict(field_label_frequencies),
        'works_with_field_set': [
            {'field_set': sorted(list(key)),
             'number_of_works': len(value),
             'works': sorted(list(value))}
            for key, value in works_with_field_set.items()
        ],
        # 'fields_data': fields_data
    }

    filename = f"field-label-report_{args.ftp_collection_number}_{args.export_label.replace(' ', '-')}_{datetime.now().strftime('%Y-%m-%d_%I-%M-%S%p')}.json"
    print(f"Writing report as {filename!r}")
    with open(filename, mode='w') as fp:
        json.dump(report, fp, indent=2)


if __name__ == '__main__':
    main()

import requests

import json
import argparse
from itertools import count

from cdm_util_scripts import cdm_api
from cdm_util_scripts.ftp_api import get_ftp_manifest, get_ftp_manifest_transcript_urls, get_ftp_transcript

from typing import List


def find_cdm_objects(repo_url: str, alias: str, field_nick: str, value: str, session: requests.Session) -> List[str]:
    repo_url = repo_url.rstrip('/')
    url = f"{repo_url}/digital/bl/dmwebservices/index.php?q=dmQuery/{alias}/{field_nick}^{value}^exact^and/dmrecord/dmrecord/1024/0/1/0/0/0/0/1/json"
    result = cdm_api.get_dm(url, session)
    return [record['pointer'] for record in result['records']]


def main():
    parser = argparse.ArgumentParser(description="Get FromThePage transcripts and output them in cdm-catcher JSON",
                                     fromfile_prefix_chars='@')
    parser.add_argument('repository_url',
                        type=str,
                        help="CONTENTdm repository URL")
    parser.add_argument('collection_alias',
                        type=str,
                        help="CONTENTdm collection alias")
    parser.add_argument('source_nick',
                        type=str,
                        help="CONTENTdm field nickname for FromThePage's IIIF dc:source metadata field")
    parser.add_argument('transcript_nick',
                        type=str,
                        help="CONTENTdm field nickname for the target transcript field")
    parser.add_argument('manifests_file',
                        type=str,
                        help="Path to file specifying FromThePage manifest links")
    parser.add_argument('output_file',
                        type=str,
                        help="Path to write the cdm-catcher JSON file")
    parser.add_argument('--transcript_type',
                        type=str,
                        action='store',
                        help="The FromThePage transcript type enclosed in quotes, default 'Verbatim Plaintext'")
    args = parser.parse_args()

    transcript_type_label = args.transcript_type or 'Verbatim Plaintext'

    with open(args.manifests_file, mode='r') as fp:
        manifest_urls = [line.strip() for line in fp.readlines()]

    catcher_fields = []
    with requests.Session() as session:
        for manifest_url in manifest_urls:
            print(f"Requesting {manifest_url!r}...")
            manifest = get_ftp_manifest(manifest_url, session)
            source = [field['value']
                      for field in manifest['metadata']
                      if field['label'] == 'dc:source'][0]
            print(f"Searching {args.collection_alias!r} field {args.source_nick!r} for {source!r}...")
            cdm_object_pointers = find_cdm_objects(
                repo_url=args.repository_url,
                alias=args.collection_alias,
                field_nick=args.source_nick,
                value=source,
                session=session
            )
            if len(cdm_object_pointers) != 1:
                raise ValueError(f"No unique object found for {source!r} in {args.source_nick!r}")
            page_pointers = cdm_api.get_cdm_page_pointers(
                repo_url=args.repository_url,
                alias=args.collection_alias,
                dmrecord=cdm_object_pointers[0],
                session=session
            )
            transcript_urls = get_ftp_manifest_transcript_urls(manifest=manifest,
                                                               label=transcript_type_label)
            if len(page_pointers) != len(transcript_urls):
                raise ValueError(f"CONTENTdm/FromThePage object length mismatch")
            print(f"Requesting {len(transcript_urls)} {transcript_type_label!r} page transcripts: ", end='')
            n = count(1)
            for dmrecord, transcript_url in zip(page_pointers, transcript_urls):
                print(f"{next(n)} ", end='', flush=True)
                transcript_text = get_ftp_transcript(transcript_url, session)
                catcher_fields.append({
                    'dmrecord': dmrecord,
                    # CONTENTdm strips whitespace, so preempt it here for cleaner catcherdiffs
                    args.transcript_nick: transcript_text.strip()
                })
            print(end='\n')
    print("Writing JSON file...")
    with open(args.output_file, mode='w') as fp:
        json.dump(catcher_fields, fp, indent=2)
    print("Done")


if __name__ == '__main__':
    main()

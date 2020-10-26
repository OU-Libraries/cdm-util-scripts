import requests

import json
import argparse

from typing import List


def get_compound_object_info(alias: str, dmrecord: str, session: requests.Session) -> dict:
    response = session.get(f"https://media.library.ohio.edu/digital/bl/dmwebservices/index.php?q=dmGetCompoundObjectInfo/{alias}/{dmrecord}/json")
    response.raise_for_status()
    return response.json()


def get_documentpdf_page_pointers(alias: str, dmrecord: str, session: requests.Session) -> List[str]:
    dmGetCompoundObjectInfo = get_compound_object_info(alias, dmrecord, session)
    if 'code' in dmGetCompoundObjectInfo:
        raise ValueError(dmGetCompoundObjectInfo['message'])
    if dmGetCompoundObjectInfo['type'] != 'Document-PDF':
        raise ValueError(f"{dmrecord} is not a Document-PDF")
    return [page['pageptr'] for page in dmGetCompoundObjectInfo['page']]


def get_ftp_manifest(url: str, session: requests.Session) -> dict:
    response = session.get(url)
    response.raise_for_status()
    return response.json()


def get_ftp_manifest_transcript_urls(manifest: dict, label: str) -> List[str]:
    canvases = manifest['sequences'][0]['canvases']
    return [seeAlso['@id'] for canvas in canvases for seeAlso in canvas['seeAlso'] if seeAlso['label'] == label]


def get_ftp_transcript(url: str, session: requests.Session) -> str:
    response = session.get(url)
    response.raise_for_status()
    return response.text


def find_objects(alias: str, field_nick: str, value: str, session: requests.Session) -> List[str]:
    response = session.get(f"https://media.library.ohio.edu/digital/bl/dmwebservices/index.php?q=dmQuery/{alias}/{field_nick}^{value}^exact^and/dmrecord/dmrecord/1024/0/1/0/0/0/0/1/json")
    response.raise_for_status()
    dmQuery = response.json()
    return [record['pointer'] for record in dmQuery['records']]


def main():
    parser = argparse.ArgumentParser(description="Get FromThePage transcripts and output them in cdm-catcher JSON")
    parser.add_argument('collection_alias',
                        metavar='collection_alias',
                        type=str,
                        help="CONTENTdm collection alias")
    parser.add_argument('source_nick',
                        metavar='source_nick',
                        type=str,
                        help="CONTENTdm field nickname for FromThePage's dc:source")
    parser.add_argument('transcript_nick',
                        metavar='transcript_nick',
                        type=str,
                        help="CONTENTdm field nickname for the transcript field")
    parser.add_argument('manifests_file',
                        metavar='manifests_file',
                        type=str,
                        help="Path to file specifying FromThePage manifest links")
    parser.add_argument('output_file',
                        metavar='output_file',
                        type=str,
                        help="Path to cdm-catcher JSON file")
    args = parser.parse_args()

    with open(args.manifests_file, mode='r') as fp:
        manifest_urls = [line.strip() for line in fp.readlines()]

    alias = args.collection_alias
    source_nick = args.source_nick
    transcript_nick = args.transcript_nick

    catcher_fields = []
    with requests.Session() as session:
        for manifest_url in manifest_urls:
            manifest = get_ftp_manifest(manifest_url, session)
            source = [field['value'] for field in manifest['metadata'] if field['label'] == 'dc:source'][0]
            object_pointers = find_objects(alias, source_nick, source, session)
            if len(object_pointers) != 1:
                raise ValueError(f"No unique object found for {source!r} in {source_nick!r}")
            page_pointers = get_documentpdf_page_pointers(alias, object_pointers[0], session)
            transcript_urls = get_ftp_manifest_transcript_urls(manifest,
                                                               label='Verbatim Plaintext')
            if len(page_pointers) != len(transcript_urls):
                raise ValueError(f"CONTENTdm/FromThePage object length mismatch")
            for dmrecord, transcript_url in zip(page_pointers, transcript_urls):
                transcript_text = get_ftp_transcript(transcript_url, session)
                catcher_fields.append({'dmrecord': dmrecord,
                                       transcript_nick: transcript_text})
    with open(args.output_file, mode='w') as fp:
        json.dump(catcher_fields, fp, indent=2)


if __name__ == '__main__':
    main()

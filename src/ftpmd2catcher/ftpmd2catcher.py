from requests import Session

import argparse
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from ftp2catcher import get_ftp_manifest_transcript_urls, get_ftp_manifest

from typing import Optional, List


@dataclass
class CdmObject:
    dmrecord: Optional[str] = None
    collection_alias: Optional[str] = None
    cdm_source_url: Optional[str] = None
    ftp_manifest_url: Optional[str] = None
    pages: Optional[list] = None


def get_collection_manifest_url(slug: str, collection_name: str, session: Session) -> str:
    response = session.get(f"https://fromthepage.com/iiif/collections/{slug}")
    response.raise_for_status()
    collections = response.json()['collections']
    for collection in collections:
        if collection['label'] == collection_name:
            return collection['@id']
    raise KeyError(f"no collection named {collection_name!r}")


def get_ftp_collection(url: str, session: Session) -> List[CdmObject]:
    response = session.get(url)
    response.raise_for_status()
    manifests = response.json()['manifests']
    ftp_collection = []
    for manifest in manifests:
        cdm_source_url = manifest['metadata'][0]['value']
        result = re.search(r"/(\w+)/(\d+)/manifest\.json$", cdm_source_url)
        collection_alias = result.group(1) if result else None
        dmrecord = result.group(2) if result else None
        ftp_collection.append(
            CdmObject(
                dmrecord=dmrecord,
                collection_alias=collection_alias,
                cdm_source_url=cdm_source_url,
                ftp_manifest_url=manifest['@id']
            )
        )
    return ftp_collection


def get_rendering(manifest: dict, label: str) -> dict:
    renderings = manifest['sequences'][0]['rendering']
    for rendering in renderings:
        if rendering['label'] == label:
            return rendering
    raise KeyError("label not found in manifest")


def get_object_pages(cdm_object: CdmObject, session: Session) -> None:
    manifest = get_ftp_manifest(url=cdm_object.ftp_manifest_url, session=session)
    tei_rendering = get_rendering(manifest=manifest, label='TEI Export')
    response = session.get(tei_rendering['@id'])
    response.raise_for_status()
    tei = response.text
    cdm_object.pages = extract_fields_from_TEI(tei=tei)


def get_objects_pages(cdm_objects: Sequence[CdmObject], session: Session) -> None:
    for cdm_object in cdm_objects:
        get_object_pages(cdm_object=cdm_object, session=session)


def extract_fields_from_TEI(tei: str) -> List[dict]:
    NS = {'': 'http://www.tei-c.org/ns/1.0'}
    tei_root = ET.fromstring(tei)
    tei_pages = tei_root.findall('./text/body/div', namespaces=NS)
    pages = []
    for tei_page in tei_pages:
        fields = dict()
        last_label = None
        tei_fields = tei_page.findall('p', namespaces=NS)
        for tei_field in tei_fields:
            label = tei_field.find('span', namespaces=NS)
            # Element truthiness is on existence of child Elements, so test for None
            if label is not None:
                label_text = last_label = label.text.partition(': ')[0]
                fields[label_text] = ''.join(list(tei_field.itertext())[1:]).strip()
            else:
                fields[last_label] = '\n\n'.join([
                    fields[last_label],
                    ''.join(tei_field.itertext())
                ]).strip()
        pages.append(fields)
    return pages


def main():
    parser = argparse.ArgumentParser(
        description="Get FromThePage metadata and map it into cdm-catcher JSON",
        fromfile_prefix_chars='@'
    )
    parser.add_argument(
        'slug',
        type=str,
        help="FromThePage user slug"
    )
    parser.add_argument(
        'collection_name',
        type=str,
        help="CONTENTdm collection name used by FromThePage"
    )
    args = parser.parse_args()

    session = Session()
    collection_manifest_url = get_collection_manifest_url(
        slug=args.slug,
        collection_name=args.collection_name,
        session=session
    )
    ftp_collection = get_ftp_collection(
        url=collection_manifest_url,
        session=session
    )
    get_objects_pages(ftp_collection)



if __name__ == '__main__':
    main()

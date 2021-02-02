from requests import Session

import argparse
import re
import sys
import csv
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass

from ftp2catcher import get_ftp_manifest, get_cdm_page_pointers

from typing import Optional, List, Iterable, Dict, Sequence, Callable


@dataclass
class FTPWork:
    dmrecord: Optional[str] = None
    cdm_repo_url: Optional[str] = None
    cdm_collection_alias: Optional[str] = None
    cdm_source_url: Optional[str] = None
    ftp_manifest_url: Optional[str] = None
    ftp_work_url: Optional[str] = None
    ftp_work_label: Optional[str] = None
    pages: Optional[List[Optional[Dict[str, str]]]] = None


@dataclass
class FTPCollection:
    manifest_url: str
    number: str
    label: str
    works: List[FTPWork]


def get_collection_manifest_url(slug: str, collection_name: str, session: Session) -> str:
    response = session.get(f"https://fromthepage.com/iiif/collections/{slug}")
    response.raise_for_status()
    collections = response.json()['collections']
    for collection in collections:
        if collection['label'] == collection_name:
            return collection['@id']
    raise KeyError(f"no collection named {collection_name!r}")


def get_ftp_collection(manifest_url: str, session: Session) -> FTPCollection:
    response = session.get(manifest_url)
    response.raise_for_status()
    collection_manifest = response.json()
    ftp_collection = FTPCollection(
        manifest_url=collection_manifest['@id'],  # Same as manifest_url
        number=collection_manifest['@id'].partition('collection/')[2],
        label=collection_manifest['label'],
        works=[]
    )
    for work in collection_manifest['manifests']:
        ftp_work = FTPWork(
            ftp_manifest_url=work['@id'],
            ftp_work_label=work['label']
        )
        if 'metadata' in work:
            source_urls = [field['value']
                           for field in work['metadata']
                           if field['label'] == 'dc:source']
            source_url = source_urls[0]
            ftp_work.cdm_source_url = source_url
            result = re.search(r"/(\w+)/(\d+)/manifest\.json$", source_url)
            ftp_work.cdm_collection_alias = result.group(1) if result else None
            ftp_work.dmrecord = result.group(2) if result else None
            ftp_work.cdm_repo_url = source_url.partition('/iiif/info')[0]
        ftp_collection.works.append(ftp_work)
    return ftp_collection


def get_rendering(ftp_manifest: dict, label: str, session: Session, verbose: bool = True) -> str:
    renderings = ftp_manifest['sequences'][0]['rendering']
    for rendering in renderings:
        if rendering['label'] == label:
            rendering_url = rendering['@id']
            break
    else:
        raise KeyError("label not found in manifest")
    if verbose:
        print(f"Requesting {label!r} rendering for {rendering_url!r}...")
    response = session.get(rendering_url)
    response.raise_for_status()
    return response.text


def rchomp(s: str, suffix: str) -> str:
    if s.endswith(suffix):
        return s[:-len(suffix)]
    return s


def extract_fields_from_p_span_xml(
        xml_ps: List[ET.Element],
        namespaces: Dict[str, str]
) -> List[Dict[str, str]]:
    fields = dict()
    last_label = None
    for xml_p in xml_ps:
        label = xml_p.find('span', namespaces=namespaces)
        # Element truthiness is on existence of child Elements, so test for None
        if label is not None:
            label_text = last_label = rchomp(label.text, ': ')
            fields[label_text] = ''.join(
                list(xml_p.itertext())[1:]
            ).strip()
        else:
            fields[last_label] = '\n\n'.join([
                fields[last_label],
                ''.join(xml_p.itertext())
            ]).strip()
    return fields or None


def extract_fields_from_tei(tei: str) -> List[Optional[Dict[str, str]]]:
    NS = {'': 'http://www.tei-c.org/ns/1.0'}
    tei_root = ET.fromstring(tei)
    tei_pages = tei_root.findall('./text/body/div', namespaces=NS)
    pages = []
    for tei_page in tei_pages:
        tei_fields = tei_page.findall('p', namespaces=NS)
        fields = extract_fields_from_p_span_xml(tei_fields, namespaces=NS)
        pages.append(fields)
    return pages


def extract_fields_from_html(html: str) -> List[Optional[Dict[str, str]]]:
    NS = {'': 'http://www.w3.org/1999/xhtml'}
    # The FromThePage XHTML Export isn't valid XHTML because of the JS blob on line 6
    html_no_scripts = re.sub(r"<script>.*</script>", '', html)
    html_root = ET.fromstring(html_no_scripts)
    html_pages = html_root.findall("body/div[@class='pages']/div", namespaces=NS)
    pages = []
    for html_page in html_pages:
        html_fields = html_page.findall("div[@class='page-content']/p", namespaces=NS)
        fields = extract_fields_from_p_span_xml(html_fields, namespaces=NS)
        pages.append(fields)
    return pages


rendering_extractors = {
    'XHTML Export': extract_fields_from_html,
    'TEI Export': extract_fields_from_tei
}


def load_ftp_manifest_data(
        ftp_work: FTPWork,
        rendering_label: str,
        session: Session,
        verbose: bool = True
) -> None:
    if verbose:
        print(f"Requesting FromThePage manifest {ftp_work.ftp_manifest_url!r}...")
    ftp_manifest = get_ftp_manifest(
        url=ftp_work.ftp_manifest_url,
        session=session
    )
    rendering_text = get_rendering(
        ftp_manifest=ftp_manifest,
        label=rendering_label,
        session=session,
        verbose=verbose
    )
    ftp_work.pages = rendering_extractors[rendering_label](rendering_text)
    ftp_work.ftp_work_url = ftp_manifest['related'][0]['@id']


def apply_field_mapping(ftp_fields: Dict[str, str], field_mapping: Dict[str, Sequence[str]]) -> Dict[str, str]:
    accumulator = dict()
    for label, nicks in field_mapping.items():
        ftp_field = ftp_fields[label]
        for nick in nicks:
            if nick in accumulator:
                if ftp_field:
                    if accumulator[nick]:
                        accumulator[nick] = '; '.join([accumulator[nick], ftp_field])
                    else:
                        accumulator[nick] = ftp_field
            else:
                accumulator[nick] = ftp_field
    return accumulator


def map_ftp_work_as_cdm_object(
        ftp_work: FTPWork,
        field_mapping: Dict[str, Sequence[str]],
        page_picker: Callable[[List[Dict[str, str]]], Dict[str, str]]
) -> Dict[str, str]:
    object_page = page_picker(ftp_work.pages)
    return {
        'dmrecord': ftp_work.dmrecord,
        **apply_field_mapping(object_page,
                              field_mapping)
    }


def print_about_drop(ftp_work: FTPWork) -> None:
    print("Dropping FromThePage work without any filled pages:",
          f"   {ftp_work.ftp_work_label!r}",
          f"   {ftp_work.ftp_work_url!r}",
          sep='\n')


def map_ftp_works_as_cdm_objects(
        ftp_works: Iterable[FTPWork],
        field_mapping: Dict[str, Sequence[str]],
        page_picker: Callable[[List[Dict[str, str]]], Dict[str, str]],
        verbose: bool = True
) -> Iterable[Dict[str, str]]:
    for ftp_work in ftp_works:
        try:
            yield map_ftp_work_as_cdm_object(
                ftp_work=ftp_work,
                field_mapping=field_mapping,
                page_picker=page_picker
            )
        except LookupError:
            if verbose:
                print_about_drop(ftp_work)
            continue


# Should the PagePickers raise exceptions or return None?
class PagePickers:
    def first_page(pages: List[Optional[Dict[str, str]]]) -> Optional[Dict[str, str]]:
        if pages:
            return pages[0]
        raise LookupError("no first page")

    def first_filled_page(pages: List[Optional[Dict[str, str]]]) -> Optional[Dict[str, str]]:
        for page in pages:
            if page and any(page.values()):
                return page
        raise LookupError("no filled page")


def get_cdm_item_info(ftp_work: FTPWork, session: Session) -> Dict[str, str]:
    response = session.get(f"{ftp_work.cdm_repo_url.rstrip('/')}/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/{ftp_work.cdm_collection_alias}/{ftp_work.dmrecord}/json")
    response.raise_for_status()
    item_info = response.json()
    return item_info


def map_ftp_work_as_cdm_pages(
        ftp_work: FTPWork,
        field_mapping: Dict[str, Sequence[str]],
        session: Session,
        verbose: bool = True
) -> List[Dict[str, str]]:
    if not any(ftp_work.pages):
        if verbose:
            print_about_drop(ftp_work)
        return []
    if verbose:
        print(f"Requesting CONTENTdm item info for {ftp_work.dmrecord!r}...")
    item_info = get_cdm_item_info(ftp_work, session)
    if item_info['find'].endswith('.cpd'):
        if verbose:
            print(f"Requesting page pointers for {ftp_work.dmrecord!r} in {ftp_work.cdm_collection_alias!r} @ {ftp_work.cdm_repo_url!r}...")
        page_pointers = get_cdm_page_pointers(
            repo_url=ftp_work.cdm_repo_url,
            alias=ftp_work.cdm_collection_alias,
            dmrecord=ftp_work.dmrecord,
            session=session
        )
    else:
        page_pointers = [ftp_work.dmrecord]
    page_data = []
    for page_pointer, ftp_fields in zip(page_pointers, ftp_work.pages):
        if ftp_fields:
            page_data.append({
                'dmrecord': page_pointer,
                **apply_field_mapping(ftp_fields=ftp_fields,
                                      field_mapping=field_mapping)
            })
    return page_data


def map_ftp_works_as_cdm_pages(
        ftp_works: Iterable[FTPWork],
        field_mapping: Dict[str, Sequence[str]],
        session: Session,
        verbose: bool = True
) -> Iterable[Dict[str, str]]:
    for ftp_work in ftp_works:
        pages = map_ftp_work_as_cdm_pages(
            ftp_work=ftp_work,
            field_mapping=field_mapping,
            session=session,
            verbose=verbose
        )
        yield from pages


class MatchModes:
    by_object = 'object'
    by_page = 'page'


def main():
    parser = argparse.ArgumentParser(
        description="Get FromThePage metadata and map it into cdm-catcher JSON",
        fromfile_prefix_chars='@'
    )
    parser.add_argument(
        'match_mode',
        type=str,
        choices=[MatchModes.by_object, MatchModes.by_page],
        help="Mode for matching FromThePage metadata to CONTENTdm objects"
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
    parser.add_argument(
        'field_mapping_csv',
        type=str,
        help="CSV file of FromThePage field labels mapped to CONTENTdm nicknames"
    )
    parser.add_argument(
        'output_file',
        type=str,
        help="File name for cdm-catcher JSON output"
    )
    args = parser.parse_args()

    with open(args.field_mapping_csv, mode='r') as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames != ['name', 'nick']:
            print(f"{args.column_mapping_csv!r}: column mapping CSV must have 'name' and 'nick' column titles in that order")
            sys.exit(1)
        field_mapping = defaultdict(list)
        for row in reader:
            field_mapping[row['name']].append(row['nick'])
        field_mapping = dict(field_mapping)

    with Session() as session:
        collection_manifest_url = get_collection_manifest_url(
            slug=args.slug,
            collection_name=args.collection_name,
            session=session
        )
        ftp_collection = get_ftp_collection(
            manifest_url=collection_manifest_url,
            session=session
        )
        for ftp_work in ftp_collection.works:
            load_ftp_manifest_data(
                ftp_work=ftp_work,
                rendering_label='XHTML Export',
                session=session
            )

        # Non-compound objects metadata is mapped both as
        # page-level and object-level. The match mode
        # only matters for compound objects.
        if args.match_mode == MatchModes.by_object:
            catcher_data = list(
                map_ftp_works_as_cdm_objects(
                    ftp_works=ftp_collection.works,
                    field_mapping=field_mapping,
                    page_picker=PagePickers.first_filled_page
                )
            )
        elif args.match_mode == MatchModes.by_page:
            catcher_data = list(
                map_ftp_works_as_cdm_pages(
                    ftp_works=ftp_collection.works,
                    field_mapping=field_mapping,
                    session=session
                )
            )
        else:
            raise KeyError(f"invalid match mode {args.match_mode!r}")

    with open(args.output_file, mode='w') as fp:
        json.dump(catcher_data, fp, indent=2)


if __name__ == '__main__':
    main()

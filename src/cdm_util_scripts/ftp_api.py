import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from requests import Session


@dataclass
class FTPPage:
    label: Optional[str] = None
    display_url: Optional[str] = None
    transcription_url: Optional[str] = None
    dmrecord: Optional[str] = None
    fields: Optional[Dict[str, str]] = None


@dataclass
class FTPWork:
    dmrecord: Optional[str] = None
    cdm_repo_url: Optional[str] = None
    cdm_collection_alias: Optional[str] = None
    cdm_source_url: Optional[str] = None
    ftp_manifest_url: Optional[str] = None
    ftp_work_url: Optional[str] = None
    ftp_work_label: Optional[str] = None
    pages: Optional[FTPPage] = None


@dataclass
class FTPCollection:
    manifest_url: Optional[str] = None
    alias: Optional[str] = None
    label: Optional[str] = None
    slug: Optional[str] = None
    works: List[FTPWork] = field(default_factory=list)


def get_ftp_manifest(url: str, session: Session) -> dict:
    response = session.get(url)
    response.raise_for_status()
    return response.json()


def get_ftp_transcript(url: str, session: Session) -> str:
    response = session.get(url)
    response.raise_for_status()
    return response.text


def get_slug_collections(slug: str, session: Session) -> dict:
    response = session.get(f"https://fromthepage.com/iiif/collections/{slug}")
    response.raise_for_status()
    return response.json()


def get_ftp_manifest_transcript_urls(manifest: dict, label: str) -> List[str]:
    canvases = manifest['sequences'][0]['canvases']
    return [seeAlso['@id']
            for canvas in canvases
            for seeAlso in canvas['seeAlso']
            if seeAlso['label'] == label]


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
        alias=collection_manifest['@id'].partition('collection/')[2],
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


def get_rendering(ftp_manifest: dict, label: str, session: Session) -> str:
    renderings = ftp_manifest['sequences'][0]['rendering']
    for rendering in renderings:
        if rendering['label'] == label:
            rendering_url = rendering['@id']
            break
    else:
        raise KeyError(f"label {label!r} not found in manifest renderings")
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
        label = xml_p.find('ns:span', namespaces=namespaces)
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
    NS = {'ns': 'http://www.tei-c.org/ns/1.0'}
    tei_root = ET.fromstring(tei)
    tei_pages = tei_root.findall('./ns:text/ns:body/ns:div', namespaces=NS)
    pages = []
    for tei_page in tei_pages:
        tei_fields = tei_page.findall('ns:p', namespaces=NS)
        fields = extract_fields_from_p_span_xml(tei_fields, namespaces=NS)
        pages.append(fields)
    return pages


def extract_fields_from_html(html: str) -> List[Optional[Dict[str, str]]]:
    NS = {'ns': 'http://www.w3.org/1999/xhtml'}
    # The FromThePage XHTML Export isn't valid XHTML because of the JS blob on line 6
    html_no_scripts = re.sub(r"<script>.*</script>", '', html)
    html_root = ET.fromstring(html_no_scripts)
    html_pages = html_root.findall("ns:body/ns:div[@class='pages']/ns:div", namespaces=NS)
    pages = []
    for html_page in html_pages:
        html_fields = html_page.findall("ns:div[@class='page-content']/ns:p", namespaces=NS)
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
        session: Session
) -> None:
    ftp_manifest = get_ftp_manifest(
        url=ftp_work.ftp_manifest_url,
        session=session
    )
    rendering_text = get_rendering(
        ftp_manifest=ftp_manifest,
        label=rendering_label,
        session=session
    )
    ftp_work.ftp_work_url = ftp_manifest['related'][0]['@id']
    pages = rendering_extractors[rendering_label](rendering_text)
    canvases = ftp_manifest['sequences'][0]['canvases']
    if len(pages) != len(canvases):
        raise ValueError('canvas and transcript rendering page count mismatch')
    ftp_work.pages = []
    for page, canvas in zip(pages, canvases):
        ftp_work.pages.append(
            FTPPage(
                label=canvas['label'],
                fields=page if page and any(page.values()) else None,
                display_url=canvas['related'][0]['@id'],
                transcription_url=canvas['related'][1]['@id']
            )
        )


def get_and_load_ftp_collection(
        slug: str,
        collection_name: str,
        rendering_label: str,
        session: Session,
        verbose: bool = True
) -> FTPCollection:
    if verbose:
        print(f"Looking up {collection_name!r} @ {slug}...")
    manifest_url = get_collection_manifest_url(
        slug=slug,
        collection_name=collection_name,
        session=session
    )
    if verbose:
        print(f"Requesting project manifest...")
    ftp_collection = get_ftp_collection(
        manifest_url=manifest_url,
        session=session
    )
    ftp_collection.slug = slug
    for n, ftp_work in enumerate(ftp_collection.works, start=1):
        if verbose:
            print(f"Requesting work manifests and {rendering_label!r} renderings {n}/{len(ftp_collection.works)}...", end='\r')
        load_ftp_manifest_data(
            ftp_work=ftp_work,
            rendering_label=rendering_label,
            session=session
        )
    if verbose:
        print(end='\n')
    return ftp_collection

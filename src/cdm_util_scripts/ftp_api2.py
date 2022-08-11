import requests
import tqdm

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from typing import List, Dict, Any, Tuple, Optional, NamedTuple, Union


@dataclass
class FTPInstance:
    base_url: str

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def request_collections(
        self, slug: str, session: requests.Session
    ) -> "FTPCollectionOfCollections":
        response = session.get(f"{self.base_url}/iiif/collections/{slug}")
        response.raise_for_status()
        collections = FTPCollectionOfCollections.from_json(response.json())
        return collections


@dataclass
class FTPCollectionOfCollections:
    url: str
    collections: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FTPCollectionOfCollections":
        return cls(
            url=json["@id"],
            collections={
                collection["label"]: collection["@id"]
                for collection in json["collections"]
            },
        )

    def request_collection(
        self, label: str, session: requests.Session
    ) -> "FTPCollection":
        response = session.get(self.collections[label])
        response.raise_for_status()
        return FTPCollection.from_json(response.json())


@dataclass
class FTPCollection:
    url: str
    label: str
    manifests: List["FTPManifest"] = field(default_factory=list)
    collection_id: str = field(init=False)

    def __post_init__(self):
        self.collection_id = self.url.rpartition("/")[2]

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FTPCollection":
        return cls(
            url=json["@id"],
            label=json["label"],
            manifests=[
                FTPManifest.from_json(manifest) for manifest in json["manifests"]
            ],
        )

    def request_manifests(
        self, session: requests.Session, show_progress: bool = True
    ) -> None:
        manifests = tqdm.tqdm(self.manifests) if show_progress else self.manifests
        for manifest in manifests:
            manifest.request(session=session)


@dataclass
class FTPManifest:
    url: str
    label: str
    metadata: Dict[str, str] = field(default_factory=dict)
    renderings: List["FTPRendering"] = field(default_factory=list)
    pages: List["FTPPage"] = field(default_factory=list)
    cdm_collection_alias: Optional[str] = None
    cdm_object_dmrecord: Optional[str] = None

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FTPManifest":
        manifest = cls(url=json["@id"], label=json["label"])
        manifest._load(json)
        return manifest

    def request(self, session: requests.Session) -> None:
        response = session.get(self.url)
        response.raise_for_status()
        json = response.json()
        self._load(json)

    def _load(self, json: Dict[str, Any]) -> None:
        # Update everything based on the new data
        self.url = json["@id"]
        self.label = json["label"]
        self.metadata = {}
        self.renderings = []
        self.pages = []
        self.cdm_collection_alias = None
        self.cdm_object_dmrecord = None

        metadata = json.get("metadata")
        if metadata is not None:
            self.metadata = {pair["label"]: pair["value"] for pair in metadata}

        # TODO: conflating seeAlso and renderings duplicates Verbatim Plaintext: problem or not?
        seeAlsos = json.get("seeAlso")
        if seeAlsos is not None:
            for seeAlso in seeAlsos:
                self.renderings.append(FTPRendering.from_json(seeAlso))

        sequences = json.get("sequences")
        if sequences is not None:
            sequence = sequences[0]
            for rendering in sequence["rendering"]:
                self.renderings.append(FTPRendering.from_json(rendering))
            self.pages = [
                FTPPage.from_json(canvas) for canvas in sequence["canvases"]
            ]

        if "dc:source" in self.metadata:
            cdm_iiif_manifest_url = self.metadata["dc:source"]
            (
                self.cdm_collection_alias,
                self.cdm_object_dmrecord,
            ) = parse_cdm_iiif_manifest_url(cdm_iiif_manifest_url)

    def _get_rendering(self, attr: str, value: str) -> "FTPRendering":
        for rendering in self.renderings:
            if getattr(rendering, attr) == value:
                return rendering
        raise KeyError(repr(value))

    def request_rendering(self, label: str, session: requests.Session) -> str:
        response = session.get(self._get_rendering(attr="label", value=label).url)
        response.raise_for_status()
        return response.text

    def request_xhtml_transcript_fields(
        self, session: requests.Session
    ) -> List[Optional[Dict[str, str]]]:
        xhtml = self.request_rendering(label="XHTML Export", session=session)
        return extract_fields_from_xhtml(xhtml)

    def request_tei_transcript_fields(
        self, session: requests.Session
    ) -> List[Optional[Dict[str, str]]]:
        tei = self.request_rendering(label="TEI Export", session=session)
        return extract_fields_from_tei(tei)

    def request_structured_data(self, session: requests.Session) -> "FTPStructuredData":
        for rendering in self.renderings:
            if rendering.context and rendering.context.endswith(
                "/jsonld/structured/1/context.json"
            ):
                break
        else:
            raise KeyError("couldn't find structured data rendering")
        response = session.get(rendering.url)
        response.raise_for_status()
        return FTPStructuredData.from_json(response.json())


class FTPRendering(NamedTuple):
    url: str
    label: str
    profile: str
    format_: Optional[str] = None
    context: Optional[str] = None

    @classmethod
    def from_json(cls, json: Dict[str, str]) -> "FTPRendering":
        return cls(
            url=json["@id"],
            label=json["label"],
            format_=json.get("format"),
            profile=json["profile"],
            context=json.get("@context"),
        )


@dataclass
class FTPPage:
    id_: str
    label: str
    renderings: List[FTPRendering] = field(default_factory=list)
    cdm_collection_alias: Optional[str] = None
    cdm_page_dmrecord: Optional[str] = None

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FTPPage":
        id_ = json["@id"]
        cdm_collection_alias, cdm_page_dmrecord = parse_ftp_canvas_id(id_)
        return cls(
            id_=id_,
            label=json["label"],
            renderings=[FTPRendering.from_json(seeAlso) for seeAlso in json["seeAlso"]],
            cdm_collection_alias=cdm_collection_alias,
            cdm_page_dmrecord=cdm_page_dmrecord,
        )

    def request_transcript(self, label: str, session: requests.Session) -> str:
        response = session.get(self._get_rendering(attr="label", value=label).url)
        response.raise_for_status()
        return response.text

    def _get_rendering(self, attr: str, value: str) -> FTPRendering:
        for rendering in self.renderings:
            if getattr(rendering, attr) == value:
                return rendering
        raise KeyError(repr(value))

    def request_structured_data(self, session: requests.Session) -> "FTPStructuredData":
        for rendering in self.renderings:
            if rendering.context and rendering.context.endswith(
                "/jsonld/structured/1/context.json"
            ):
                break
        else:
            raise KeyError("couldn't find structured data rendering")
        response = session.get(rendering.url)
        response.raise_for_status()
        return FTPStructuredData.from_json(response.json())


@dataclass
class FTPStructuredData:
    contributors: List[Dict[str, str]]
    data: List["FTPStructuredDataField"] = field(default_factory=list)

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> "FTPStructuredData":
        return cls(
            contributors=json["contributors"],
            data=[FTPStructuredDataField(**field_data) for field_data in json["data"]],
        )


class FTPStructuredDataField(NamedTuple):
    label: str
    value: Union[str, List[str]]
    config: str


def parse_cdm_iiif_manifest_url(url: str) -> Tuple[str, str]:
    # New route: .../iiif/2/p15808coll19:872/manifest.json
    # Old route: .../iiif/info/p15808coll19/3001/manifest.json
    match = re.search(r"/([^/:]*)[/:](\d*)/manifest.json", url)
    if match is None:
        raise ValueError(repr(url))
    return match.groups()


def parse_ftp_canvas_id(id_: str) -> Tuple[str, str]:
    match = re.search(r"/iiif/([^:]*):(\d*)/canvas/c\d+", id_)
    if match is None:
        raise ValueError(repr(id_))
    return match.groups()


def request_ftp_collection(
    base_url: str, slug: str, collection_label: str, session: requests.Session
) -> FTPCollection:
    instance = FTPInstance(base_url=base_url)
    collections = instance.request_collections(slug=slug, session=session)
    return collections.request_collection(label=collection_label, session=session)


def request_ftp_collection_and_manifests(
    base_url: str,
    slug: str,
    collection_label: str,
    session: requests.Session,
    show_progress: bool = True,
) -> FTPCollection:
    collection = request_ftp_collection(
        base_url=base_url,
        slug=slug,
        collection_label=collection_label,
        session=session,
    )
    collection.request_manifests(session=session, show_progress=show_progress)
    return collection


def extract_fields_from_tei(tei: str) -> List[Optional[Dict[str, str]]]:
    NS = {"ns": "http://www.tei-c.org/ns/1.0"}
    tei_root = ET.fromstring(tei)
    tei_pages = tei_root.findall("./ns:text/ns:body/ns:div", namespaces=NS)
    pages = []
    for tei_page in tei_pages:
        tei_fields = tei_page.findall("ns:p", namespaces=NS)
        fields = extract_fields_from_p_span_xml(tei_fields, namespaces=NS)
        pages.append(fields)
    return pages


def extract_fields_from_xhtml(xhtml: str) -> List[Optional[Dict[str, str]]]:
    NS = {"ns": "http://www.w3.org/1999/xhtml"}
    # The FromThePage XHTML Export isn't valid XHTML because of the JS blob on line 6
    html_no_scripts = re.sub(r"<script>?.*</script>", "", xhtml).strip()
    html_root = ET.fromstring(html_no_scripts)
    html_pages = html_root.findall(
        "ns:body/ns:div[@class='pages']/ns:div", namespaces=NS
    )
    pages = []
    for html_page in html_pages:
        html_fields = html_page.findall(
            "ns:div[@class='page-content']/ns:p", namespaces=NS
        )
        fields = extract_fields_from_p_span_xml(html_fields, namespaces=NS)
        pages.append(fields)
    return pages


def extract_fields_from_p_span_xml(
    xml_ps: List[ET.Element], namespaces: Dict[str, str]
) -> Optional[Dict[str, str]]:
    fields = dict()
    last_label: Optional[str] = None
    for xml_p in xml_ps:
        label = xml_p.find("ns:span", namespaces=namespaces)
        # Element truthiness is on existence of child Elements, so test for None
        if label is not None:
            label_text = last_label = removesuffix(label.text, ": ")
            fields[label_text] = "".join(list(xml_p.itertext())[1:]).strip()
        else:
            fields[last_label] = "\n\n".join(
                [fields[last_label], "".join(xml_p.itertext())]
            ).strip()
    return fields or None


RENDERING_EXTRACTORS = {
    "XHTML Export": extract_fields_from_xhtml,
    "TEI Export": extract_fields_from_tei,
}


def removesuffix(s: str, suffix: str) -> str:
    if s.endswith(suffix):
        return s[: -len(suffix)]
    return s
